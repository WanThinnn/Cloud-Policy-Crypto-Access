# Crypto Access - Django Application

Production-ready Django application with crypto access control system.

## 📋 Features

- ✅ **Production-ready settings** (base, development, production)
- ✅ **Environment variables** management with .env
- ✅ **Security configurations** (HTTPS, CORS, security headers)
- ✅ **Static files** handling with WhiteNoise
- ✅ **REST API** support with Django REST Framework
- ✅ **PostgreSQL** support for production
- ✅ **Redis caching** configuration
- ✅ **Logging** system
- ✅ **Testing** setup with pytest
- ✅ **Code quality** tools (flake8, black, isort)

## 🚀 Quick Start

### 1. Create Virtual Environment

```bash
cd src
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
# Development
pip install -r requirements-dev.txt

# Production
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# .env file is located in project root (not in src/)
# Copy example env file if needed
cp .env.example .env

# Edit .env file with your configurations
# Location: d:\Documents\UIT\Nam_4\Cloud-Firestore-Crypto-Access\.env
```

### 4. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 7. Run Development Server

```bash
# Make sure DJANGO_ENV=development in .env
python manage.py runserver
```

Visit: http://localhost:8000

## 📁 Project Structure

```
Cloud-Firestore-Crypto-Access/    # Project root
├── .env                           # Environment variables (HERE!)
├── .env.example                  # Example environment file
└── src/                          # Django source code
    ├── config/                   # Project configuration
    │   ├── settings/            # Settings package
    │   │   ├── __init__.py
    │   │   ├── base.py          # Base settings (loads .env from root)
    │   │   ├── development.py   # Development settings
    │   │   └── production.py    # Production settings
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    ├── crypto_access/           # Main application
    │   ├── models.py
    │   ├── views.py
    │   ├── urls.py
    │   ├── admin.py
    │   ├── serializers.py
    │   ├── signals.py
    │   └── tests.py
    ├── static/                  # Static files
    │   ├── css/
    │   └── js/
    ├── templates/               # Templates
    │   └── crypto_access/
    ├── media/                   # User uploads
    ├── logs/                    # Application logs
    ├── manage.py
    ├── requirements.txt
    └── requirements-dev.txt
```

## 🔧 Configuration

### Environment Variables
 (located in project root)
Key environment variables in `.env`:

```env
DJANGO_ENV=development|production
DJANGO_SECRET_KEY=your-secret-key
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=crypto_access_db
DB_USER=crypto_user
DB_PASSWORD=your-password
```

### Settings Modules

- **base.py**: Common settings for all environments
- **development.py**: Development-specific settings (DEBUG=True, SQLite)
- **production.py**: Production settings (DEBUG=False, PostgreSQL, security)

Switch between environments:
```bash
# Development (default)
export DJANGO_ENV=development

# Production
export DJANGO_ENV=production
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest crypto_access/tests.py
```

## 🎨 Code Quality

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Lint with flake8
flake8 .
```

## 🚀 Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run application
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Environment Setup

1. Set `DJANGO_ENV=production`
2. Configure PostgreSQL database
3. Set strong `DJANGO_SECRET_KEY`
4. Configure `DJANGO_ALLOWED_HOSTS`
5. Set up Redis for caching
6. Configure HTTPS/SSL
7. Collect static files

### Security Checklist

- [ ] `DEBUG = False`
- [ ] Strong `SECRET_KEY` from environment
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] HTTPS enabled (`SECURE_SSL_REDIRECT = True`)
- [ ] Security headers configured
- [ ] Database credentials in environment variables
- [ ] Static files served via WhiteNoise or CDN
- [ ] Logging configured
- [ ] Error monitoring (Sentry)

## 📚 API Endpoints

- `GET /` - Home page
- `GET /health/` - Health check endpoint
- `GET /admin/` - Django admin panel
- `GET /api/` - API endpoints

## 🛠️ Development

### Create New App

```bash
python manage.py startapp app_name
```

### Make Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

## 📝 License

MIT License

## 👥 Authors

Your Team Name

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
