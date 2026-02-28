# Hashmark Authentication System

Secure Microsoft-based authentication system for the **Hashmark Capstone
Project**.

This system provides:

-   Microsoft (Azure AD) login
-   Invite-only access control
-   Role-based authorization
-   CSRF protection
-   Rate limiting
-   Secure session handling

------------------------------------------------------------------------

## 🛠 Tech Stack

### Frontend

-   Vue 3
-   Vite
-   Axios

### Backend

-   Python
-   Flask
-   MSAL (Microsoft Authentication Library)

### Database

-   SQLite

------------------------------------------------------------------------

## 🔐 Features

### Microsoft OAuth Login

Users authenticate using their Microsoft account.

### Invite-Only Access

Only users who: - Already exist in the system\
- OR have a valid invite

can access the platform.

### Role-Based Permissions

Available roles:

-   `SUPER_ADMIN`
-   `ADMIN`
-   `COACH`
-   `SCOUT`

Protected endpoints require appropriate roles.

------------------------------------------------------------------------

## 🚀 Local Development Setup

### Backend Setup

Navigate to the backend folder:

`cd backend`

Create a virtual environment:

`python -m venv .venv`

Activate it (Windows):

`.venv`\Scripts`{=tex}`\activate`{=tex}`

Install dependencies:

`pip install -r requirements.txt`

Create a `.env` file using `.env.example` as a template.

Start the backend server:

`python app.py`

Backend runs at:

http://localhost:5000

------------------------------------------------------------------------

### Frontend Setup

Navigate to frontend:

`cd frontend`

Install dependencies:

`npm install`

Run development server:

`npm run dev`

Frontend runs at:

http://localhost:5173

------------------------------------------------------------------------

## 🔄 Authentication Flow

1.  User clicks **Sign in with Microsoft**
2.  Flask redirects to Microsoft login
3.  Microsoft returns an authorization code
4.  Flask exchanges the code for an access token
5.  System:
    -   Validates user
    -   Checks invite status
    -   Assigns role
6.  Session cookie is created
7.  Frontend fetches `/api/me` to confirm login

------------------------------------------------------------------------

## 🛡 Security Measures

-   Signed session cookies
-   HttpOnly cookies
-   SameSite protection
-   CSRF token validation
-   Rate limiting on authentication routes
-   Content Security Policy (CSP)
-   Optional domain allowlist
-   `.env`, `.venv`, `node_modules`, and database files ignored by Git

------------------------------------------------------------------------

## 📌 Future Improvements

-   Production HTTPS enforcement
-   Redis-based rate limiting storage
-   Email-based invite delivery
-   Refresh token handling
-   Deployment configuration


