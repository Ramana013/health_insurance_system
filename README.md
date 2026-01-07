# Health Insurance Management System

A Django-based full-stack web application designed to manage health insurance policies, users, and claims with role-based access control.

---

## 📌 Project Overview

The Health Insurance Management System is a web application that streamlines insurance operations such as policy management, claim processing, and user administration.  
It supports multiple user roles and provides secure, structured workflows for real-world insurance use cases.

---

## 🛠️ Technologies Used

### Backend
- Python 3.x
- Django 5.0.6
- Django ORM
- SQLite (development database)

### Frontend
- HTML
- CSS
- JavaScript
- Bootstrap

---

## 👥 User Roles

- **Policy Holder**
  - Browse and apply for insurance policies
  - Track policy status
  - Submit insurance claims

- **Network Provider**
  - Review and process claims

- **Admin**
  - Manage users
  - Create and manage policies
  - Review and approve/reject claims

---

## 🔐 Authentication & Security

- Custom user model extending Django’s `AbstractUser`
- Role-based access control
- Session-based authentication
- Password reset via email (SMTP)
- CSRF protection
- Secure password hashing
- Secure file upload handling

---

## 🗄️ Core Models

- **CustomUser**
  - Fields include role, phone number, address, and date of birth

- **Policy**
  - Insurance plans with premium, coverage limit, and validity

- **UserPolicy**
  - Links users to policies
  - Tracks policy status (Applied, Active, Withdrawn, Expired)

- **Claim**
  - Manages claim submission, document uploads, and approval workflow
  - Statuses: Submitted, Under Review, Approved, Rejected

---

## ✨ Key Features

- Policy browsing and application
- Policy lifecycle tracking
- Claim submission with document upload
- Claim review and processing
- User profile management
- Admin panel for complete system control

---

## 📁 Project Structure

health_insurance/
├── admin_panel/ # Admin functionalities
├── claims/ # Claim management
├── feedback_support/ # User feedback and support
├── health_insurance/ # Project settings
├── network_provider/ # Network provider features
├── policy/ # Policy management
├── users/ # Authentication and user profiles
├── media/ # Uploaded files
├── db.sqlite3 # SQLite database (ignored in Git)
└── manage.py

---

## ⚙️ Installation & Setup

1. Clone the repository
```bash
git clone <repository-url>
cd health_insurance

2.Create and activate virtual environment

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

3. Apply migrations

4. Run the development server

5.Open in browser

http://127.0.0.1:8000/
