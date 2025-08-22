# Docker Setup - Cloud Firestore Crypto Access Backend

## Prerequisites

### Environment Setup
1. Copy the environment template:
```bash
cp env/.env.template env/.env
```

2. Edit `env/.env` and provide required values:
```bash
# Required: Generate strong secrets
JWT_SECRET_KEY=your-jwt-secret-key-here
SYSTEM_SERVICE_TOKEN=your-system-service-token-here

# Generate secrets using:
# openssl rand -hex 32
```

3. Ensure Firebase service account key is in `env/` directory

## Quick Start

### 1. Build and Run
```bash
# Make script executable
chmod +x docker.sh

# Build and run the container
./docker.sh run
```

### 2. Using Docker Compose
```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Manual Docker Commands

### Build Image
```bash
docker build -t crypto-access-backend .
```

### Run Container
```bash
docker run -d \
  --name crypto-access-backend \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/log:/app/log \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/tmp:/app/tmp \
  -v $(pwd)/env:/app/env:ro \
  -v $(pwd)/abe_keys:/app/abe_keys \
  -e FLASK_ENV=production \
  -e LOG_LEVEL=INFO \
  -e HOST=0.0.0.0 \
  -e PORT=5000 \
  crypto-access-backend
```

## Management Script

The `docker.sh` script provides easy management:

```bash
./docker.sh build      # Build the Docker image
./docker.sh run        # Run the container
./docker.sh stop       # Stop the container
./docker.sh restart    # Restart the container
./docker.sh logs       # Show logs
./docker.sh logs -f    # Follow logs
./docker.sh shell      # Get shell access
./docker.sh status     # Show container status
./docker.sh health     # Check application health
./docker.sh clean      # Remove container and image
./docker.sh help       # Show help
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment |
| `LOG_LEVEL` | `INFO` | Logging level |
| `HOST` | `0.0.0.0` | Listen host |
| `PORT` | `5000` | Listen port |
| `JWT_SECRET_KEY` | `corporate-cp-abe-jwt-secret-2025-docker` | JWT signing key |

## Volume Mounts

| Host Path | Container Path | Description |
|-----------|---------------|-------------|
| `./log` | `/app/log` | Application logs |
| `./uploads` | `/app/uploads` | Uploaded files |
| `./tmp` | `/app/tmp` | Temporary files |
| `./env` | `/app/env` | Environment configs (read-only) |
| `./abe_keys` | `/app/abe_keys` | ABE encryption keys |

## Health Check

The container includes a health check that verifies:
- Application is responding on port 5000
- CA health endpoint returns successful response

```bash
# Check health manually
curl http://localhost:5000/api/ca/health
```

## Logging

All application logs are stored in the mounted `./log` directory:

```bash
# View recent logs
tail -f log/api.log

# View JSON structured logs
tail -f log/api_json.log | jq '.'

# View all log files
ls -la log/
```

## Troubleshooting

### Container won't start
```bash
# Check container logs
docker logs crypto-access-backend

# Check if ports are in use
netstat -tulpn | grep 5000

# Verify image was built correctly
docker images | grep crypto-access-backend
```

### Permission issues
```bash
# Fix log directory permissions
sudo chown -R $USER:$USER log/

# Check container user
docker exec crypto-access-backend whoami
```

### Application errors
```bash
# Access container shell
docker exec -it crypto-access-backend /bin/bash

# Check Python dependencies
docker exec crypto-access-backend python3 -c "import flask; print('Flask OK')"

# View application files
docker exec crypto-access-backend ls -la /app/
```

## Production Deployment

### Security Considerations
- Container runs as non-root user `app`
- Sensitive files mounted read-only
- Health checks enabled
- Resource limits can be added

### Resource Limits (Optional)
```bash
docker run -d \
  --memory="1g" \
  --cpus="0.5" \
  --name crypto-access-backend \
  # ... other options
```

### Behind Reverse Proxy
```nginx
upstream backend {
    server localhost:5000;
}

server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Development

For development with auto-reload:
```bash
docker run -d \
  --name crypto-access-backend-dev \
  -p 5000:5000 \
  -v $(pwd):/app \
  -e FLASK_ENV=development \
  -e FLASK_DEBUG=1 \
  crypto-access-backend \
  python3 -u main.py
```
