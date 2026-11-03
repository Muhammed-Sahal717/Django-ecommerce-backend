# Django REST API Development – E-Commerce Backend Implementation

A complete RESTful e-commerce backend built using **Django** and **Django REST Framework (DRF)** for the Week 16 practical assignment.

The backend supports product catalog management, shopping cart operations, order processing with nested items, token authentication, role-based permissions, searching, filtering, and pagination.

---

## Features

- **Product Management (CRUD):**
  - Public endpoints for listing and viewing product details.
  - Admin-only access for creating, updating, and deleting products.
  - Image upload support for product images.
- **Cart Management:**
  - Authenticated user cart creation and retrieval.
  - Adding items to cart, updating quantities, and removing items.
  - Stock validation to prevent adding more items than available in inventory.
  - Dynamic calculation of subtotal per item and total cart amount.
- **Order Management:**
  - Place orders directly from the current user's shopping cart.
  - Stock deduction on order placement.
  - Automatic clearing of cart items after successful checkout.
  - Nested order items included in order responses.
- **Authentication & Permissions:**
  - Token Authentication (`rest_framework.authtoken`) and Session Authentication.
  - `IsAdminOrReadOnly` permission for products (public read, admin write).
  - `IsAuthenticated` permission for cart and orders.
- **Filtering, Search & Pagination:**
  - Filter products by price range (`min_price`, `max_price`).
  - Search products by name (`search` or `name`).
  - Order products by price and date created (`ordering=price` or `ordering=-created_at`).
  - Page number pagination (`PAGE_SIZE = 10`).

---

## Tech Stack

- **Backend Framework:** Django 6.1
- **API Framework:** Django REST Framework 3.18
- **Filtering Library:** django-filter
- **Image Handling:** Pillow
- **Database:** SQLite (default)

---

## Project Structure

```text
week16-ecommerce/
├── manage.py
├── requirements.txt
├── README.md
├── shop_backend/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── store/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── filters.py
    ├── models.py
    ├── pagination.py
    ├── permissions.py
    ├── serializers.py
    ├── tests.py
    ├── urls.py
    ├── views.py
    └── migrations/
        └── 0001_initial.py
```

---

## Installation & Setup

### 1. Clone the repository and navigate to the project root

```bash
git clone <repository-url>
cd Django-ecommerce-backend
```

### 2. Set up and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run database migrations

```bash
python manage.py migrate
```

### 5. Create a superuser (for admin access)

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`.

---

## API Endpoints

### 1. Authentication

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `POST` | `/api/auth/token/` | Obtain auth token by sending `username` and `password` | Public |

To authenticate requests, include the token in the `Authorization` header:
```text
Authorization: Token <your_token_key>
```

---

### 2. Products (`/api/products/`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/api/products/` | List all products (paginated) | Public |
| `GET` | `/api/products/{id}/` | Retrieve a single product by ID | Public |
| `POST` | `/api/products/` | Create a new product | Admin Only |
| `PUT` | `/api/products/{id}/` | Update a product | Admin Only |
| `PATCH` | `/api/products/{id}/` | Partially update a product | Admin Only |
| `DELETE` | `/api/products/{id}/` | Delete a product | Admin Only |

#### Query Parameters:
- **Price Range Filter:** `/api/products/?min_price=50&max_price=200`
- **Name Search:** `/api/products/?search=keyboard` or `/api/products/?name=keyboard`
- **Ordering:** `/api/products/?ordering=price` (ascending) or `/api/products/?ordering=-price` (descending)
- **Pagination:** `/api/products/?page=2`

---

### 3. Shopping Cart (`/api/cart/` & `/api/cart-items/`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/api/cart/` | Get current user's cart with items and total price | Authenticated |
| `POST` | `/api/cart/` | Create cart or add product to cart | Authenticated |
| `GET` | `/api/cart-items/` | List items in current user's cart | Authenticated |
| `POST` | `/api/cart-items/` | Add item to cart (`product`, `quantity`) | Authenticated |
| `GET` | `/api/cart-items/{id}/` | Retrieve a specific cart item | Authenticated |
| `PUT` / `PATCH` | `/api/cart-items/{id}/` | Update item quantity | Authenticated |
| `DELETE` | `/api/cart-items/{id}/` | Remove item from cart | Authenticated |

#### Sample Request Body (Add to cart):
```json
{
  "product": 1,
  "quantity": 2
}
```

---

### 4. Orders (`/api/orders/`)

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/api/orders/` | List user's orders (Admin sees all) | Authenticated |
| `POST` | `/api/orders/` | Place order from current cart | Authenticated |
| `GET` | `/api/orders/{id}/` | Retrieve order details with nested items | Authenticated |
| `PUT` / `PATCH` | `/api/orders/{id}/` | Update order (e.g. status) | Authenticated / Admin |
| `DELETE` | `/api/orders/{id}/` | Delete order | Authenticated |

#### Sample Order Response (Nested Order Items):
```json
{
  "id": 1,
  "user": 2,
  "total_amount": "1999.98",
  "created_at": "2026-10-30T15:00:00Z",
  "status": "Pending",
  "items": [
    {
      "id": 1,
      "order": 1,
      "product": 1,
      "product_name": "Laptop",
      "quantity": 2,
      "price": "999.99"
    }
  ]
}
```

---

## Frontend Integration Workflow (React)

The backend provides a straightforward flow for React frontend integration:

1. **Browse Products:** Call `GET /api/products/` with optional search and pagination parameters.
2. **Product Details:** Call `GET /api/products/:id/` to display single product information.
3. **Cart Operations:**
   - Call `POST /api/cart-items/` with `{"product": id, "quantity": 1}` to add items.
   - Call `GET /api/cart/` to get current items and calculated `total_price`.
   - Call `DELETE /api/cart-items/:id/` to remove an item.
4. **Checkout:**
   - Call `POST /api/orders/` without body to checkout current cart items.
   - On success (`HTTP 201`), redirect the user to the order confirmation page using the returned `order.id`.

---

## Running Automated Tests

Run the test suite using Django's test runner:

```bash
python manage.py test
```

All 15 test cases covering permissions, CRUD endpoints, filtering, ordering, pagination, stock limits, and order placement will execute.
