#!/bin/bash

# Production deployment script for Crypto Access

echo "Starting production deployment..."

# Set environment to production
export DJANGO_ENV=production

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run tests
echo "Running tests..."
pytest

# Restart Gunicorn
echo "Restarting Gunicorn..."
sudo systemctl restart gunicorn

# Restart Nginx
echo "Restarting Nginx..."
sudo systemctl restart nginx

echo "Deployment completed successfully!"