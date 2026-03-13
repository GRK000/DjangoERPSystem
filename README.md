# ERP System

Delivery notes and inventory management system built with Django to cover the full order preparation workflow: customers, delivery notes, line items, product availability, and warehouse movements.

It is designed as a server-rendered web application, simple to run locally and easy to follow from a code perspective.

---

# Overview

This project addresses a very practical problem: managing delivery notes operationally by connecting the commercial side (customers and documents) with warehouse operations (stock, replenishment, and order preparation).

The main workflow starts with creating a delivery note, adding product lines, and advancing it through controlled states until preparation or delivery, registering inventory movements when required.

From a technical perspective, the project focuses on implementing real business logic inside the Django models and views: state transitions, total calculations, stock validation, and atomic operations to prevent inconsistencies during order preparation.

---

# Features

- User authentication with login, logout, and registration.
- Customer management (list, detail, creation, and editing).
- Product catalog with category filters.
- Delivery note management:
  - create delivery notes
  - detailed view with line items and low-stock alerts
  - add product lines
  - validated state transitions
- Delivery note lookup by number..
- Order preparation module with employee and warehouse assignment.
- Stock deduction during preparation using `transaction.atomic()` and `select_for_update()` to prevent race conditions.
- Inventory movement tracking (stock in / stock out).
- Stock replenishment through forms.
- Sales statistics (total sales, best-selling products, sales by category and customer ranking).

---

# Architecture

The application follows a classic server-rendered Django architecture:

Routes → Views → Models / Forms → HTML Templates

Simplified flow:

Browser -> Django URLConf -> Views -> ORM/Models -> Templates (HTML)

Main components:

- `DjangoProject/`  
  Global configuration (settings, main URLs, ASGI/WSGI entry points).
- `albaranes/`  
  Core business application containing domain logic, forms, views, and routes.
- `templates/`  
  Server-rendered interface for each functional module.

Example data flow (order preparation):

Usuari autenticat -> `preparacio` -> seleccio d'albara pendent -> validacio de stock per linia -> actualitzacio atomica de `StockMagatzem` -> alta de `MovimentStock` -> canvi d'estat de l'albara.

---

# Technologies

- Python
- Django
- SQLite (current default configuration)
- Django ORM
- Django Templates
- Bootstrap (used through template classes where applicable)

---

# Running the Project

Prerequisites:

- Python 3.10+ (recommended)
- `pip`

Installation and setup (Windows PowerShell)

```powershell
cd D:\ERPs\DjangoProject
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install django
python manage.py migrate
python manage.py runserver
```

The application will be available at:
`http://127.0.0.1:8000/`

