#!/bin/bash

# Docker management script for Cloud Firestore Crypto Access Backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="crypto-access-backend"
CONTAINER_NAME="crypto-access-backend"
PORT="5000"

print_help() {
    echo -e "${BLUE}Cloud Firestore Crypto Access Backend - Docker Management${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build      Build the Docker image"
    echo "  run        Run the container (builds if needed)"
    echo "  stop       Stop the running container"
    echo "  restart    Restart the container"
    echo "  logs       Show container logs"
    echo "  shell      Get shell access to running container"
    echo "  clean      Remove container and image"
    echo "  status     Show container status"
    echo "  health     Check application health"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run"
    echo "  $0 logs -f"
}

build_image() {
    echo -e "${BLUE}Building Docker image...${NC}"
    docker build -t $IMAGE_NAME .
    echo -e "${GREEN}✅ Image built successfully!${NC}"
}

run_container() {
    # Check if container exists and is running
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        echo -e "${YELLOW}Container is already running!${NC}"
        return 0
    fi

    # Check if container exists but is stopped
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        echo -e "${BLUE}Starting existing container...${NC}"
        docker start $CONTAINER_NAME
        echo -e "${GREEN}✅ Container started!${NC}"
        return 0
    fi

    # Check if image exists
    if ! docker images -q $IMAGE_NAME | grep -q .; then
        echo -e "${YELLOW}Image not found, building first...${NC}"
        build_image
    fi

    echo -e "${BLUE}Running new container...${NC}"
    
    # Create directories if they don't exist
    mkdir -p log uploads tmp abe_keys
    
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:5000 \
        -v "$(pwd)/log:/app/log" \
        -v "$(pwd)/uploads:/app/uploads" \
        -v "$(pwd)/tmp:/app/tmp" \
        -v "$(pwd)/env:/app/env:ro" \
        -v "$(pwd)/abe_keys:/app/abe_keys" \
        -e FLASK_ENV=production \
        -e LOG_LEVEL=INFO \
        -e HOST=0.0.0.0 \
        -e PORT=5000 \
        $IMAGE_NAME

    echo -e "${GREEN}✅ Container started successfully!${NC}"
    echo -e "${BLUE}Application will be available at: http://localhost:$PORT${NC}"
    
    # Wait a moment and show status
    sleep 3
    show_status
}

stop_container() {
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        echo -e "${BLUE}Stopping container...${NC}"
        docker stop $CONTAINER_NAME
        echo -e "${GREEN}✅ Container stopped!${NC}"
    else
        echo -e "${YELLOW}Container is not running!${NC}"
    fi
}

restart_container() {
    echo -e "${BLUE}Restarting container...${NC}"
    stop_container
    sleep 2
    run_container
}

show_logs() {
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        echo -e "${BLUE}Showing container logs...${NC}"
        docker logs $@ $CONTAINER_NAME
    else
        echo -e "${RED}Container is not running!${NC}"
        exit 1
    fi
}

shell_access() {
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        echo -e "${BLUE}Accessing container shell...${NC}"
        docker exec -it $CONTAINER_NAME /bin/bash
    else
        echo -e "${RED}Container is not running!${NC}"
        exit 1
    fi
}

clean_up() {
    echo -e "${YELLOW}Cleaning up Docker resources...${NC}"
    
    # Stop and remove container
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        echo -e "${GREEN}✅ Container removed!${NC}"
    fi
    
    # Remove image
    if docker images -q $IMAGE_NAME | grep -q .; then
        docker rmi $IMAGE_NAME 2>/dev/null || true
        echo -e "${GREEN}✅ Image removed!${NC}"
    fi
    
    echo -e "${GREEN}✅ Cleanup completed!${NC}"
}

show_status() {
    echo -e "${BLUE}Container Status:${NC}"
    if docker ps -f name=$CONTAINER_NAME --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q $CONTAINER_NAME; then
        docker ps -f name=$CONTAINER_NAME --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        check_health
    else
        echo -e "${RED}❌ Container is not running${NC}"
    fi
}

check_health() {
    echo -e "${BLUE}Health Check:${NC}"
    if curl -s -f http://localhost:$PORT/api/ca/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Application is healthy${NC}"
        curl -s http://localhost:$PORT/api/ca/health | python3 -m json.tool
    else
        echo -e "${RED}❌ Application health check failed${NC}"
    fi
}

# Main script logic
case "$1" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    logs)
        shift
        show_logs $@
        ;;
    shell)
        shell_access
        ;;
    clean)
        clean_up
        ;;
    status)
        show_status
        ;;
    health)
        check_health
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac
