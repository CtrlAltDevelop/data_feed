# Data Feed Project with Django Ninja

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.13-yellow.svg)

## Overview
This project provides a RESTful API for managing and serving data feeds using Django Ninja. It includes features for creating, reading, updating, and deleting feed items, with authentication and rate limiting support.

---

## Features
- **REST API** endpoints for data feed management.
- **API** documentation (*Swagger/OpenAPI*)
- **Environment variables** for secure configurations.
- **Uvicorn** as the ASGI server.

---

## Prerequisites
- Python 3.13+
- Django 5.2+
- Django Ninja 1.4+
- SQLite

---

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/CtrlAltDevelop/data_feed.git
    cd data_feed
    ```

2. Create and activate a virtual environment (optional):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3. Install dependencies:
    ```bash
   python.exe -m pip install --upgrade pip
   pip install -r requirements 
   ```

4. Configure environment variables:

    Modify a `.env` file in the project root with the following variables:

    ``` ini
    SECRET_KEY=your-django-secret-key
    DEBUG=True
    ALLOWED_HOSTS=localhost
    LOG_LEVEL=DEBUG
    ```

5. Run migrations:
   ``` bash
   python manage.py migrate 
   ```

6. Create a superuser (only once when database is fresh):
   ``` bash
   python manage.py createsuperuser
   ```

7. Run the development server:
   ``` bash
   uvicorn configs.asgi:application --host localhost --port 8000 --reload --workers 8 --env-file .env
   ```

---

## Project Structure

The project structure is documented in the `structure` file. You can view it by running [📂 View Project Structure](structure)

``` text
├── apps/               # Your Django Ninja API application (contains app-specific logic)
├── common/             # Common utilities, shared functions, and reusable components
├── config/             # Django project configuration and settings
│   ├── __init__.py     # Marks the directory as a Python module
│   ├── admin.py        # Admin panel configuration
│   ├── api.py          # API router configuration for Django Ninja
│   ├── asgi.py         # ASGI application entry point (for async support)
│   ├── database.py     # Database configuration and connections
│   ├── jazzmin.py      # Configuration for Jazzmin (customized Django admin theme)
│   ├── logging.py      # Logging configuration for debugging and error tracking
│   ├── middlewares.py  # Custom middlewares for request/response processing
│   ├── settings.py     # Main settings file for Django (environment-based configurations)
│   ├── urls.py         # URL routing configuration for the project
│   └── wsgi.py         # WSGI entry point for production servers
├── images/             # Static image files used within the project
│   ├── some_file       # Example image or placeholder file
│   └── ...
├── .env                # Environment variables (e.g., secrets, database credentials)
├── .gitignore          # Files and directories to ignore in Git version control
├── manage.py           # Django’s command-line utility for project management
├── README.md           # Documentation and project instructions
├── requirements.txt    # List of Python dependencies
├── shell.py            # Django shell script for running interactive commands
└── structure           # (Optional) Project structure documentation
```

---

## API Documentation

After starting the server, access the interactive API documentation at:
- **API Endpoint:** [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)
- **Swagger UI:** [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/docs)
- **ReDoc:** [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/redoc)
- **Admin Panel:** [http://localhost:8000/admin/](http://localhost:8000/admin/)
- **Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## Contributors

- **Mohammad Zarif** – [CtrlAltDevelop](https://github.com/CtrlAltDevelop)
- **Alireza Mahmodi** – [Yaroofie](https://github.com/Yaroofie)

---
## License

This project is licensed under the [MIT License](LICENSE).

---

## Support

If you encounter any issues or have questions, feel free to open an issue on the [GitHub Issues](https://github.com/CtrlAltDevelop/data_feed/issues) page or contact the maintainer directly.