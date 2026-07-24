#!/bin/bash
# ============================================================================
# StudyBuddy Deployment Script
# ============================================================================
# Usage:
#   ./deploy.sh build     - Build Docker image
#   ./deploy.sh run       - Run container locally
#   ./deploy.sh stop      - Stop running container
#   ./deploy.sh logs      - View container logs
#   ./deploy.sh push      - Push image to Docker Hub (set DOCKER_USER first)
# ============================================================================

APP_NAME="studybuddy"
IMAGE_NAME="${APP_NAME}:latest"
CONTAINER_NAME="${APP_NAME}"
PORT=8501

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

case "$1" in
  build)
    info "Building Docker image: ${IMAGE_NAME}"
    docker build -t "${IMAGE_NAME}" .
    if [ $? -eq 0 ]; then
      info "Build successful! Image: ${IMAGE_NAME}"
    else
      error "Build failed!"
      exit 1
    fi
    ;;

  run)
    info "Starting ${CONTAINER_NAME} on port ${PORT}..."

    # Stop existing container if running
    docker rm -f "${CONTAINER_NAME}" 2>/dev/null

    # Run with AWS credentials from environment or .env file
    if [ -f .env ]; then
      docker run -d \
        --name "${CONTAINER_NAME}" \
        -p "${PORT}:8501" \
        --env-file .env \
        --restart unless-stopped \
        "${IMAGE_NAME}"
    else
      docker run -d \
        --name "${CONTAINER_NAME}" \
        -p "${PORT}:8501" \
        -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
        -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
        -e AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN}" \
        -e AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}" \
        --restart unless-stopped \
        "${IMAGE_NAME}"
    fi

    if [ $? -eq 0 ]; then
      info "Container started!"
      info "Access the app at: http://localhost:${PORT}"
      info "Share with others on your network: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your-ip'):${PORT}"
    else
      error "Failed to start container!"
      exit 1
    fi
    ;;

  stop)
    info "Stopping ${CONTAINER_NAME}..."
    docker stop "${CONTAINER_NAME}" && docker rm "${CONTAINER_NAME}"
    info "Container stopped and removed."
    ;;

  logs)
    docker logs -f "${CONTAINER_NAME}"
    ;;

  push)
    DOCKER_USER="${DOCKER_USER:-}"
    if [ -z "${DOCKER_USER}" ]; then
      error "Set DOCKER_USER environment variable first:"
      echo "  export DOCKER_USER=yourdockerhubusername"
      exit 1
    fi

    REMOTE_IMAGE="${DOCKER_USER}/${APP_NAME}:latest"
    info "Tagging image as ${REMOTE_IMAGE}"
    docker tag "${IMAGE_NAME}" "${REMOTE_IMAGE}"

    info "Pushing to Docker Hub..."
    docker push "${REMOTE_IMAGE}"

    if [ $? -eq 0 ]; then
      info "Pushed successfully!"
      info "Others can run: docker run -p 8501:8501 --env-file .env ${REMOTE_IMAGE}"
    else
      error "Push failed! Make sure you're logged in: docker login"
      exit 1
    fi
    ;;

  *)
    echo "StudyBuddy Deployment Script"
    echo ""
    echo "Usage: $0 {build|run|stop|logs|push}"
    echo ""
    echo "Commands:"
    echo "  build  - Build the Docker image"
    echo "  run    - Run the container locally (port ${PORT})"
    echo "  stop   - Stop and remove the container"
    echo "  logs   - Follow container logs"
    echo "  push   - Push image to Docker Hub (set DOCKER_USER first)"
    echo ""
    echo "Quick start:"
    echo "  1. cp .env.example .env  (then fill in your AWS credentials)"
    echo "  2. ./deploy.sh build"
    echo "  3. ./deploy.sh run"
    echo "  4. Open http://localhost:${PORT}"
    ;;
esac
