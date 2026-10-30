from decimal import Decimal
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from .models import Product, Cart, CartItem, Order, OrderItem


class StoreAPITests(APITestCase):
    def setUp(self):
        # Create regular user
        self.user = User.objects.create_user(username="student", password="password123")
        self.user_token = Token.objects.create(user=self.user)

        # Create admin user
        self.admin = User.objects.create_superuser(username="admin", password="adminpassword123", email="admin@test.com")
        self.admin_token = Token.objects.create(user=self.admin)

        # Create sample products
        self.product1 = Product.objects.create(
            name="Laptop",
            description="High performance laptop",
            price=Decimal("999.99"),
            stock=10,
        )
        self.product2 = Product.objects.create(
            name="Wireless Mouse",
            description="Ergonomic wireless mouse",
            price=Decimal("29.99"),
            stock=50,
        )
        self.product3 = Product.objects.create(
            name="Mechanical Keyboard",
            description="RGB mechanical gaming keyboard",
            price=Decimal("89.99"),
            stock=5,
        )

    # 1. Product Listing and Detail (Public)
    def test_public_can_list_products(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check pagination structure
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 3)

    def test_public_can_retrieve_single_product(self):
        response = self.client.get(f"/api/products/{self.product1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Laptop")

    # 2. Product Permissions (Admin-only write)
    def test_unauthenticated_cannot_create_product(self):
        data = {
            "name": "Headphones",
            "description": "Noise cancelling headphones",
            "price": "149.99",
            "stock": 20,
        }
        response = self.client.post("/api/products/", data)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_regular_user_cannot_create_product(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")
        data = {
            "name": "Headphones",
            "description": "Noise cancelling headphones",
            "price": "149.99",
            "stock": 20,
        }
        response = self.client.post("/api/products/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_update_delete_product(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        
        # Create
        create_data = {
            "name": "Headphones",
            "description": "Noise cancelling headphones",
            "price": "149.99",
            "stock": 20,
        }
        create_res = self.client.post("/api/products/", create_data)
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        product_id = create_res.data["id"]

        # Update
        update_data = {
            "name": "Pro Headphones",
            "description": "Updated description",
            "price": "179.99",
            "stock": 15,
        }
        update_res = self.client.put(f"/api/products/{product_id}/", update_data)
        self.assertEqual(update_res.status_code, status.HTTP_200_OK)
        self.assertEqual(update_res.data["name"], "Pro Headphones")

        # Delete
        delete_res = self.client.delete(f"/api/products/{product_id}/")
        self.assertEqual(delete_res.status_code, status.HTTP_204_NO_CONTENT)

    # 3. Filtering and Ordering
    def test_product_price_filtering(self):
        response = self.client.get("/api/products/?min_price=30&max_price=100")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Mechanical Keyboard", names)
        self.assertNotIn("Wireless Mouse", names)
        self.assertNotIn("Laptop", names)

    def test_product_search(self):
        response = self.client.get("/api/products/?search=mouse")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Wireless Mouse")

    def test_product_ordering(self):
        # Order by price ascending
        response = self.client.get("/api/products/?ordering=price")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["name"], "Wireless Mouse")
        self.assertEqual(results[-1]["name"], "Laptop")

    # 4. Cart Operations
    def test_unauthenticated_cannot_access_cart(self):
        response = self.client.get("/api/cart/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_cart_flow(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")

        # Get initial cart (empty)
        get_res = self.client.get("/api/cart/")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_res.data["items"]), 0)
        self.assertEqual(get_res.data["total_price"], 0)

        # Add item via POST /api/cart/
        post_res = self.client.post("/api/cart/", {"product": self.product2.id, "quantity": 2})
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(post_res.data["items"]), 1)
        self.assertEqual(post_res.data["items"][0]["quantity"], 2)
        self.assertEqual(float(post_res.data["total_price"]), 59.98)

        # Add item via CartItemViewSet POST /api/cart-items/
        item_res = self.client.post("/api/cart-items/", {"product": self.product3.id, "quantity": 1})
        self.assertEqual(item_res.status_code, status.HTTP_201_CREATED)

        # Verify cart now has 2 items and updated total
        updated_cart = self.client.get("/api/cart/")
        self.assertEqual(len(updated_cart.data["items"]), 2)
        expected_total = float(Decimal("59.98") + Decimal("89.99"))
        self.assertAlmostEqual(float(updated_cart.data["total_price"]), expected_total, places=2)

        # Remove item from cart
        cart_item_id = item_res.data["id"]
        delete_res = self.client.delete(f"/api/cart-items/{cart_item_id}/")
        self.assertEqual(delete_res.status_code, status.HTTP_204_NO_CONTENT)

        # Verify cart item was removed
        final_cart = self.client.get("/api/cart/")
        self.assertEqual(len(final_cart.data["items"]), 1)

    def test_cart_item_insufficient_stock(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")
        # Product 3 has 5 in stock, try to add 10
        response = self.client.post("/api/cart-items/", {"product": self.product3.id, "quantity": 10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 5. Order Flow and Checkout
    def test_cannot_place_order_with_empty_cart(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")
        response = self.client.post("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_place_order_from_cart_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")

        # Add item to cart
        self.client.post("/api/cart-items/", {"product": self.product1.id, "quantity": 2})

        # Place order via POST /api/orders/
        response = self.client.post("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "Pending")
        self.assertEqual(float(response.data["total_amount"]), 1999.98)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["product_name"], "Laptop")
        self.assertEqual(response.data["items"][0]["quantity"], 2)

        # Check stock deduction
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 8)

        # Check cart is cleared
        cart_res = self.client.get("/api/cart/")
        self.assertEqual(len(cart_res.data["items"]), 0)

    def test_order_stock_insufficient_at_checkout(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")

        # Add 5 mechanical keyboards to cart
        self.client.post("/api/cart-items/", {"product": self.product3.id, "quantity": 5})

        # Another process or admin reduces stock to 3
        self.product3.stock = 3
        self.product3.save()

        # Try to checkout
        response = self.client.post("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient stock", response.data["error"])

    # 6. React Frontend Workflow
    def test_react_frontend_workflow(self):
        # 1. Fetch all products
        products_res = self.client.get("/api/products/")
        self.assertEqual(products_res.status_code, status.HTTP_200_OK)
        first_product_id = products_res.data["results"][0]["id"]

        # 2. Retrieve product details by ID
        detail_res = self.client.get(f"/api/products/{first_product_id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)

        # 3. Authenticate user
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")

        # 4. Add item to cart
        add_res = self.client.post("/api/cart-items/", {"product": first_product_id, "quantity": 1})
        self.assertEqual(add_res.status_code, status.HTTP_201_CREATED)
        cart_item_id = add_res.data["id"]

        # 5. Calculate cart total
        cart_res = self.client.get("/api/cart/")
        self.assertEqual(cart_res.status_code, status.HTTP_200_OK)
        self.assertGreater(float(cart_res.data["total_price"]), 0)

        # 6. Submit checkout / create order
        order_res = self.client.post("/api/orders/")
        self.assertEqual(order_res.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", order_res.data)
        self.assertEqual(order_res.data["status"], "Pending")

        # 7. Verify order details can be retrieved for redirect page
        order_id = order_res.data["id"]
        order_detail_res = self.client.get(f"/api/orders/{order_id}/")
        self.assertEqual(order_detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(order_detail_res.data["id"], order_id)
