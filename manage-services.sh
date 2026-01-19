#!/bin/bash
##############################################################################
# Phone Manager Services Control Script
# Manages both frontend and backend services with start, stop, status, restart
##############################################################################

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Directories
VAR_DIR="$PROJECT_ROOT/var"
LOG_DIR="$VAR_DIR/logs"
RUN_DIR="$VAR_DIR/run"
DATA_DIR="$VAR_DIR/data"

# PID files
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"

# Log files
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

##############################################################################
# Helper Functions
##############################################################################

# Create necessary directories
init_directories() {
    mkdir -p "$LOG_DIR" "$RUN_DIR" "$DATA_DIR"
}

# Log a message with timestamp
log_message() {
    local level=$1
    local message=$2
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $message"
}

# Print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "running")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "stopped")
            echo -e "${RED}✗${NC} $message"
            ;;
        "info")
            echo -e "${YELLOW}ℹ${NC} $message"
            ;;
    esac
}

# Check if process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

##############################################################################
# Backend Functions
##############################################################################

start_backend() {
    print_status "info" "Starting backend service..."
    
    if is_running "$BACKEND_PID_FILE"; then
        print_status "running" "Backend is already running (PID: $(cat $BACKEND_PID_FILE))"
        return 0
    fi
    
    # Check if virtual environment exists
    if [ ! -f "$BACKEND_DIR/.venv/bin/activate" ]; then
        log_message "ERROR" "Virtual environment not found. Creating venv..."
        cd "$BACKEND_DIR"
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
    fi
    
    # Activate venv and start backend
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    
    # Start Django development server
    python manage.py runserver 0.0.0.0:8000 >> "$BACKEND_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$BACKEND_PID_FILE"
    
    sleep 2
    if is_running "$BACKEND_PID_FILE"; then
        print_status "running" "Backend started (PID: $pid)"
        log_message "INFO" "Backend logs: $BACKEND_LOG"
        return 0
    else
        print_status "stopped" "Failed to start backend"
        return 1
    fi
}

stop_backend() {
    if [ ! -f "$BACKEND_PID_FILE" ]; then
        print_status "info" "Backend is not running"
        return 0
    fi
    
    local pid=$(cat "$BACKEND_PID_FILE")
    print_status "info" "Stopping backend (PID: $pid)..."
    
    if kill "$pid" 2>/dev/null; then
        sleep 1
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
        print_status "stopped" "Backend stopped"
        return 0
    else
        rm -f "$BACKEND_PID_FILE"
        print_status "info" "Backend was not running"
        return 0
    fi
}

status_backend() {
    if is_running "$BACKEND_PID_FILE"; then
        local pid=$(cat "$BACKEND_PID_FILE")
        print_status "running" "Backend is running (PID: $pid)"
        return 0
    else
        print_status "stopped" "Backend is not running"
        return 1
    fi
}

##############################################################################
# Frontend Functions
##############################################################################

start_frontend() {
    print_status "info" "Starting frontend service..."
    
    if is_running "$FRONTEND_PID_FILE"; then
        print_status "running" "Frontend is already running (PID: $(cat $FRONTEND_PID_FILE))"
        return 0
    fi
    
    # Check if node_modules exists
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        log_message "INFO" "Installing frontend dependencies..."
        cd "$FRONTEND_DIR"
        npm install
    fi
    
    cd "$FRONTEND_DIR"
    npm run dev >> "$FRONTEND_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"
    
    sleep 2
    if is_running "$FRONTEND_PID_FILE"; then
        print_status "running" "Frontend started (PID: $pid)"
        log_message "INFO" "Frontend logs: $FRONTEND_LOG"
        return 0
    else
        print_status "stopped" "Failed to start frontend"
        return 1
    fi
}

stop_frontend() {
    if [ ! -f "$FRONTEND_PID_FILE" ]; then
        print_status "info" "Frontend is not running"
        return 0
    fi
    
    local pid=$(cat "$FRONTEND_PID_FILE")
    print_status "info" "Stopping frontend (PID: $pid)..."
    
    if kill "$pid" 2>/dev/null; then
        sleep 1
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
        print_status "stopped" "Frontend stopped"
        return 0
    else
        rm -f "$FRONTEND_PID_FILE"
        print_status "info" "Frontend was not running"
        return 0
    fi
}

status_frontend() {
    if is_running "$FRONTEND_PID_FILE"; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        print_status "running" "Frontend is running (PID: $pid)"
        return 0
    else
        print_status "stopped" "Frontend is not running"
        return 1
    fi
}

##############################################################################
# Combined Functions
##############################################################################

start_all() {
    init_directories
    log_message "INFO" "Starting all services..."
    start_backend
    start_frontend
    echo ""
    log_message "INFO" "All services started"
}

stop_all() {
    log_message "INFO" "Stopping all services..."
    stop_backend
    stop_frontend
    echo ""
    log_message "INFO" "All services stopped"
}

status_all() {
    log_message "INFO" "Service Status:"
    echo ""
    status_backend
    local backend_status=$?
    echo ""
    status_frontend
    local frontend_status=$?
    echo ""
    echo "Backend logs: $BACKEND_LOG"
    echo "Frontend logs: $FRONTEND_LOG"
    
    if [ $backend_status -eq 0 ] && [ $frontend_status -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

restart_all() {
    log_message "INFO" "Restarting all services..."
    stop_all
    sleep 1
    start_all
}

##############################################################################
# Main Script
##############################################################################

show_usage() {
    cat << EOF
Phone Manager Services Control

Usage: $0 [COMMAND]

Commands:
  start       Start both frontend and backend services
  stop        Stop both frontend and backend services
  status      Show status of both services
  restart     Restart both services

Examples:
  $0 start
  $0 stop
  $0 status
  $0 restart

Service Logs:
  Backend:  $BACKEND_LOG
  Frontend: $FRONTEND_LOG

PID Files:
  Backend:  $BACKEND_PID_FILE
  Frontend: $FRONTEND_PID_FILE
EOF
}

# Parse command
COMMAND=${1:-status}

case "$COMMAND" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    status)
        status_all
        ;;
    restart)
        restart_all
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo ""
        show_usage
        exit 1
        ;;
esac
