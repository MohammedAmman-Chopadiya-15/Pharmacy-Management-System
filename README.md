# Pharmacy Management System API
**Module:** Web Service Design and Development (Assessment 2)  
**Student ID:** 30264083

## Overview
A containerized RESTful Web Service built with FastAPI and MySQL. This project demonstrates CRUD operations, JWT authentication, and professional API documentation using the Pharmacy database schema.

### Key Features:
* **Asynchronous Design:** Utilizes FastAPI's `async` capabilities for high-performance request handling.
* **Database Management:** Implements SQLAlchemy ORM for secure and structured communication with a MySQL database.
* **Containerization:** Orchestrated with Docker Compose to ensure environment parity between development and production.
* **Security:** Implements OAuth2 with Password Flow and JWT (JSON Web Tokens) for secure endpoint access.
* **Standardization:** Adheres to RESTful principles and provides comprehensive schema validation using Pydantic.

## Tech Stack
* **Language:** Python 3.11
* **Framework:** FastAPI
* **Database:** MySQL 8.0 (Containerized)
* **ORM:** SQLAlchemy
* **Infrastructure:** Docker & Docker Compose

## Prerequisites
- Docker Desktop
- Git

## Installation & Setup
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   ```
2. Start the service using Docker Compose:
   ```bash
   docker-compose up --build
   ```
3. The API will be available at ```http://localhost:8000```

## Documentation
Once the server is running, you can access the interactive documentation:

**Swagger UI:** http://localhost:8000/docs

**ReDoc:** http://localhost:8000/redoc

## Endpoints Summary

