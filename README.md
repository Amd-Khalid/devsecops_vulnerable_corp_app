# Vulnerable Corporate App - DevSecOps Educational Project

A Flask web application designed for educational purposes to demonstrate common security vulnerabilities and teach DevSecOps practices.

## Overview

This project is an corporate portal application for testing purposes. It demonstrates real-world security monitoring that should be avoided in production systems.

## Features

- **User Authentication**: Login system with session management
- **Role-Based Access Control (RBAC)**: Admin and user roles
- **CRUD Operations**: Create, read, and delete posts
- **Dashboard**: User feed for viewing posts
- **Admin Panel**: Admin-only access to view users

## Tech Stack

- **Framework**: Flask 2.2.2
- **Database**: SQLite3
- **Language**: Python 3.13+

## Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

## Installation

1. Clone or extract the project:
   ```bash
   cd devsecops_vulnerable_corp_app
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```bash
   python init_db.py
   ```

## Running the Application

Start the Flask development server:

```bash
python app.py
```

The application will be available at:
- Local: `http://127.0.0.1:5000`
- Network: `http://0.0.0.0:5000`

## Default Credentials

Use these credentials to test the application:

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| john_doe | password123 | User |

## Project Structure

```
devsecops_vulnerable_corp_app/
├── app.py                      # Main Flask application
├── init_db.py                  # Database initialization script
├── requirements.txt            # Python dependencies
├── sonar-project.properties    # SonarQube configuration
├── Dockerfile                  # Docker configuration
└── templates/
    ├── base.html              # Base template
    ├── login.html             # Login page
    ├── dashboard.html         # User dashboard
    └── admin.html             # Admin panel
```

## Available Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Redirect to login or dashboard |
| `/login` | GET, POST | User login page |
| `/dashboard` | GET, POST | User dashboard (create/view posts) |
| `/admin` | GET | Admin panel (admin only) |
| `/delete/<post_id>` | GET | Delete a post |
| `/logout` | GET | Logout user |

## Security Testing Tips

This application is ideal for:
- SAST (Static Application Security Testing) - Code analysis tools
- DAST (Dynamic Application Security Testing) - Web vulnerability scanners
- Manual penetration testing
- Security training and awareness
- CI/CD security pipeline testing

## Stopping the Application

Press `Ctrl + C` in the terminal running the Flask server.

## Dependencies

See `requirements.txt`:
- Flask 2.2.2
- Werkzeug 2.2.2

## License

Educational use only.

## Project Team & Roles

| Name | Role | Primary Responsibilities |
| :--- | :--- | :--- |
| **Ahmed Khalid** | **DevSecOps Engineer** | Lead developer for the CI/CD pipeline integration, SAST/DAST automation, and backend security patching for SQLi and IDOR. |
| **Sarfaraz Baig** | **Security Researcher** | Responsible for vulnerability research, threat modeling, and performing manual penetration testing to identify business logic flaws. |
| **Daniyal Shadab** | **QA & Compliance Lead** | Focused on regression testing suites, SCA dependency management, and generating compliance documentation (Audit & Retest Reports). |
