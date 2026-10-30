from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, Cart, CartItem, Order, OrderItem
from .serializers import (
    ProductSerializer,
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
)
from .permissions import IsAdminOrReadOnly
from .pagination import ProductPagination
from .filters import ProductFilter


class ProductViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for Product CRUD.
    Publicly accessible for listing and detail view.
    Only admin users can create, update, or delete products.
    """
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]


class CartViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for Cart operations.
    Only authenticated users can access their cart.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        cart, created = Cart.objects.get_or_create(user=request.user)

        # If product is passed in request, add it to the cart
        product_id = request.data.get("product")
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

            try:
                quantity = int(request.data.get("quantity", 1))
            except (ValueError, TypeError):
                return Response({"error": "Invalid quantity."}, status=status.HTTP_400_BAD_REQUEST)

            if quantity <= 0:
                return Response({"error": "Quantity must be at least 1."}, status=status.HTTP_400_BAD_REQUEST)

            if product.stock < quantity:
                return Response(
                    {"error": f"Insufficient stock. Available stock is {product.stock}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not item_created:
                if product.stock < (cart_item.quantity + quantity):
                    return Response(
                        {"error": f"Insufficient stock. Available stock is {product.stock}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()

        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CartItemViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for full CRUD operations on Cart Items.
    Only authenticated users can view/modify items in their cart.
    """
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)

        if product.stock < quantity:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"stock": f"Insufficient stock. Available stock is {product.stock}."})

        existing_item = CartItem.objects.filter(cart=cart, product=product).first()
        if existing_item:
            new_quantity = existing_item.quantity + quantity
            if product.stock < new_quantity:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"stock": f"Insufficient stock. Available stock is {product.stock}."})
            existing_item.quantity = new_quantity
            existing_item.save()
            serializer.instance = existing_item
        else:
            serializer.save(cart=cart)

    def perform_update(self, serializer):
        quantity = serializer.validated_data.get("quantity", serializer.instance.quantity)
        product = serializer.instance.product

        if product.stock < quantity:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"stock": f"Insufficient stock. Available stock is {product.stock}."})

        serializer.save()


class OrderViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for Order CRUD.
    Authenticated users can place orders from their cart and view their orders.
    Admin users can view all orders.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all().order_by("-created_at")
        return Order.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        cart = Cart.objects.filter(user=request.user).first()
        cart_items = list(cart.items.all()) if cart else []

        # If cart is empty, check if items were provided in request body
        if not cart_items:
            items_data = request.data.get("items", [])
            if not items_data:
                return Response(
                    {"error": "Your cart is empty. Add products to cart before placing an order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order_items_to_create = []
            total_amount = 0

            for item_data in items_data:
                product_id = item_data.get("product")
                quantity = item_data.get("quantity", 1)
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    return Response({"error": f"Product with ID {product_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

                if quantity <= 0:
                    return Response({"error": "Quantity must be at least 1."}, status=status.HTTP_400_BAD_REQUEST)

                if product.stock < quantity:
                    return Response(
                        {"error": f"Insufficient stock for {product.name}. Available: {product.stock}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                order_items_to_create.append((product, quantity, product.price))
                total_amount += product.price * quantity

            order = Order.objects.create(user=request.user, total_amount=total_amount, status="Pending")
            for product, quantity, price in order_items_to_create:
                OrderItem.objects.create(order=order, product=product, quantity=quantity, price=price)
                product.stock -= quantity
                product.save()

            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # Checkout using cart items
        for item in cart_items:
            if item.product.stock < item.quantity:
                return Response(
                    {"error": f"Insufficient stock for {item.product.name}. Available: {item.product.stock}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        total_amount = sum(item.product.price * item.quantity for item in cart_items)
        order = Order.objects.create(user=request.user, total_amount=total_amount, status="Pending")

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
            item.product.stock -= item.quantity
            item.product.save()

        # Clear cart items after order is placed
        cart.items.all().delete()

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
