# ERP System

Delivery notes and inventory management system built with Django to cover the full order preparation workflow: customers, delivery notes, line items, product availability, and warehouse movements.

The backend keeps the business rules in Django. The UI is now React + TypeScript + Vite + CSS, using the Aurora Ops visual system: dark, operational, bento-style, with semantic status badges, embedded KPIs and a command palette.

---

# Overview

This project addresses a practical problem: managing delivery notes operationally by connecting the commercial side with warehouse operations.

The main workflow starts with creating a delivery note, adding product lines, and advancing it through controlled states until preparation or delivery, registering inventory movements when required.

From a technical perspective, the project focuses on business logic inside Django models and views: state transitions, total calculations, stock validation, and atomic operations to prevent inconsistencies during order preparation.

---

# Features

- User authentication with login, logout, and registration.
- Customer management: list, detail, creation, and editing.
- Product catalog with category filters.
- Delivery note management:
  - create delivery notes
  - detail view with line items and low-stock alerts
  - add product lines
  - validated state transitions
- Delivery note lookup by number.
- Order preparation module with employee and warehouse assignment.
- Stock deduction during preparation using `transaction.atomic()` and `select_for_update()`.
- Inventory movement tracking.
- Stock replenishment through forms.
- Sales statistics.
- Aurora Ops React UI with dashboard, semantic badges, sparklines, empty states and command palette.

---

# Architecture

Routes -> Views -> Models / Forms -> React shell with initial JSON data

Simplified flow:

Browser -> Django URLConf -> Views -> ORM/Models -> `templates/app.html` -> Vite assets

Main components:

- `DjangoProject/`
  Global configuration.
- `albaranes/`
  Core business application containing domain logic, forms, views, and routes.
- `templates/app.html`
  Single Django shell that injects initial data for React.
- `frontend/`
  React, TypeScript, Vite and CSS implementation of the Aurora Ops UI.

Example data flow:

Authenticated user -> `preparacio` -> pending delivery note selection -> stock validation per line -> atomic `StockMagatzem` update -> `MovimentStock` creation -> delivery note state change.

---

# Technologies

- Python
- Django
- SQLite
- Django ORM
- React
- TypeScript
- Vite
- CSS

---

# Running the Project

Prerequisites:

- Python 3.10+ recommended
- `pip`
- Node.js 20+ recommended

Installation and setup on Windows PowerShell:

```powershell
cd D:\ERPs\DjangoProject
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install django
python manage.py migrate
cd frontend
npm install
npm run build
cd ..
python manage.py runserver
```

The application will be available at:

`http://127.0.0.1:8000/`

The Django app serves compiled frontend assets from `frontend/dist`, so run `npm run build` after frontend changes.
