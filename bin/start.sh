#!/bin/bash
# NGX Voice Sales Agent - Universal Startup Script
# Standard entry point for all environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="development"
HOST="127.0.0.1"
PORT="8000"
WORKERS="4"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[NGX]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "NGX Voice Sales Agent - Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --env ENVIRONMENT    Environment (development|staging|production) [default: development]"
    echo "  -h, --host HOST          Host to bind to [default: 127.0.0.1]"
    echo "  -p, --port PORT          Port to bind to [default: 8000]"
    echo "  -w, --workers WORKERS    Number of workers for production [default: 4]"
    echo "  --docker                 Start with Docker Compose"
    echo "  --help                   Show this help message"
    echo ""
    echo "Environment-specific commands:"
    echo "  Development:    $0 --env development"
    echo "  Staging:        $0 --env staging --host 0.0.0.0"
    echo "  Production:     $0 --env production --host 0.0.0.0 --workers 16"
    echo "  Docker:         $0 --docker"
    echo ""
    echo "Standard entry point: uvicorn src.api.main:app"
}

# Function to check environment variables
check_env_vars() {
    print_status "Checking required environment variables..."
    
    local missing=()
    
    # Core environment variables
    [ -z "${OPENAI_API_KEY:-}" ] && missing+=("OPENAI_API_KEY")
    [ -z "${ELEVENLABS_API_KEY:-}" ] && missing+=("ELEVENLABS_API_KEY")
    [ -z "${SUPABASE_URL:-}" ] && missing+=("SUPABASE_URL")
    [ -z "${SUPABASE_ANON_KEY:-}" ] && missing+=("SUPABASE_ANON_KEY")
    
    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing[@]}"; do
            echo "  - $var"
        done
        print_warning "Please create a .env file based on env.example"
        
        if [ "$ENVIRONMENT" = "production" ]; then
            print_error "Cannot start in production without required environment variables"
            exit 1
        else
            print_warning "Continuing in development mode with missing variables"
        fi
    else
        print_success "All required environment variables are set"
    fi
}

# Function to start with uvicorn
start_uvicorn() {
    local cmd=(
        "uvicorn"
        "src.api.main:app"
        "--host" "$HOST"
        "--port" "$PORT"
    )
    
    case "$ENVIRONMENT" in
        "development")
            print_status "Starting in DEVELOPMENT mode..."
            cmd+=("--reload" "--log-level" "debug")
            ;;
        "staging")
            print_status "Starting in STAGING mode..."
            cmd+=("--workers" "$WORKERS" "--log-level" "info")
            ;;
        "production")
            print_status "Starting in PRODUCTION mode..."
            cmd+=(
                "--workers" "$WORKERS"
                "--log-level" "warning"
                "--access-log"
                "--limit-concurrency" "1000"
                "--limit-max-requests" "10000"
                "--loop" "uvloop"
            )
            ;;
        *)
            print_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    print_status "Command: ${cmd[*]}"
    print_status "Server will be available at http://$HOST:$PORT"
    
    if [ "$ENVIRONMENT" = "development" ]; then
        print_status "API Documentation: http://$HOST:$PORT/docs"
    fi
    
    exec "${cmd[@]}"
}

# Function to start with Docker
start_docker() {
    print_status "Starting with Docker Compose..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found"
        exit 1
    fi
    
    docker-compose up --build
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
print_status "NGX Voice Sales Agent - Startup"
print_status "Environment: $ENVIRONMENT"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    print_status "Loading environment variables from .env"
    # Export variables from .env file
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check environment variables
check_env_vars

# Start the application
if [ "${USE_DOCKER:-false}" = "true" ]; then
    start_docker
else
    start_uvicorn
fi