#!/bin/bash

# GEE System Management Script
# Manages both Forge (Python) and Praxis (Go) processes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FORGE_DIR="./Forge"
PRAXIS_DIR="./Praxis"
FORGE_PORT=5000
PRAXIS_PORT=8080
PID_DIR="/tmp/gee"

# Create PID directory if it doesn't exist
mkdir -p "$PID_DIR"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[GEE]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if a process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start Forge
start_forge() {
    print_status "Starting Forge (Python Rules Engine)..."
    
    if is_running "$PID_DIR/forge.pid"; then
        print_warning "Forge is already running"
        return 1
    fi
    
    cd "$FORGE_DIR" || exit 1
    
    # Apply database updates if needed
    if [ -f "db_updates_praxis.sql" ] && [ -f "instance/GEE.db" ]; then
        print_status "Applying database updates..."
        sqlite3 instance/GEE.db < db_updates_praxis.sql 2>/dev/null || true
    fi
    
    # Start Forge in background
    nohup python app.py > ../logs/forge.log 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/forge.pid"
    
    # Wait a moment to check if it started successfully
    sleep 2
    if is_running "$PID_DIR/forge.pid"; then
        print_status "Forge started successfully (PID: $pid) on port $FORGE_PORT"
    else
        print_error "Failed to start Forge"
        rm -f "$PID_DIR/forge.pid"
        return 1
    fi
    
    cd ..
}

# Function to start Praxis
start_praxis() {
    print_status "Starting Praxis (Go Rules Execution Engine)..."
    
    if is_running "$PID_DIR/praxis.pid"; then
        print_warning "Praxis is already running"
        return 1
    fi
    
    cd "$PRAXIS_DIR" || exit 1
    
    # Create data directory if it doesn't exist
    mkdir -p data
    
    # Check if Go is installed
    if ! command -v go &> /dev/null; then
        print_error "Go is not installed or not in PATH"
        print_error "Please install Go 1.21+ from https://golang.org/dl/"
        cd ..
        return 1
    fi
    
    # Build Praxis if not already built
    if [ ! -f "praxis" ]; then
        print_status "Building Praxis..."
        go build -o praxis cmd/praxis/main.go
    fi
    
    # Start Praxis in background
    nohup ./praxis > ../logs/praxis.log 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/praxis.pid"
    
    # Wait a moment to check if it started successfully
    sleep 2
    if is_running "$PID_DIR/praxis.pid"; then
        print_status "Praxis started successfully (PID: $pid) on port $PRAXIS_PORT"
    else
        print_error "Failed to start Praxis"
        rm -f "$PID_DIR/praxis.pid"
        return 1
    fi
    
    cd ..
}

# Function to stop Forge
stop_forge() {
    print_status "Stopping Forge..."
    
    if is_running "$PID_DIR/forge.pid"; then
        local pid=$(cat "$PID_DIR/forge.pid")
        kill "$pid" 2>/dev/null
        
        # Wait for process to stop
        local count=0
        while is_running "$PID_DIR/forge.pid" && [ $count -lt 10 ]; do
            sleep 1
            ((count++))
        done
        
        if is_running "$PID_DIR/forge.pid"; then
            print_warning "Forge didn't stop gracefully, forcing..."
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_DIR/forge.pid"
        print_status "Forge stopped"
    else
        print_warning "Forge is not running"
    fi
}

# Function to stop Praxis
stop_praxis() {
    print_status "Stopping Praxis..."
    
    if is_running "$PID_DIR/praxis.pid"; then
        local pid=$(cat "$PID_DIR/praxis.pid")
        kill "$pid" 2>/dev/null
        
        # Wait for process to stop
        local count=0
        while is_running "$PID_DIR/praxis.pid" && [ $count -lt 10 ]; do
            sleep 1
            ((count++))
        done
        
        if is_running "$PID_DIR/praxis.pid"; then
            print_warning "Praxis didn't stop gracefully, forcing..."
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_DIR/praxis.pid"
        print_status "Praxis stopped"
    else
        print_warning "Praxis is not running"
    fi
}

# Function to show status
show_status() {
    echo -e "\n${GREEN}=== GEE System Status ===${NC}\n"
    
    if is_running "$PID_DIR/forge.pid"; then
        local forge_pid=$(cat "$PID_DIR/forge.pid")
        echo -e "Forge:  ${GREEN}Running${NC} (PID: $forge_pid) on port $FORGE_PORT"
    else
        echo -e "Forge:  ${RED}Stopped${NC}"
    fi
    
    if is_running "$PID_DIR/praxis.pid"; then
        local praxis_pid=$(cat "$PID_DIR/praxis.pid")
        echo -e "Praxis: ${GREEN}Running${NC} (PID: $praxis_pid) on port $PRAXIS_PORT"
    else
        echo -e "Praxis: ${RED}Stopped${NC}"
    fi
    
    echo ""
}

# Function to tail logs
tail_logs() {
    print_status "Tailing logs (Ctrl+C to stop)..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Touch log files if they don't exist
    touch logs/forge.log logs/praxis.log
    
    # Use tail to follow both logs
    tail -f logs/forge.log logs/praxis.log
}

# Main script logic
case "$1" in
    start)
        print_status "Starting GEE System..."
        mkdir -p logs
        start_forge
        start_praxis
        show_status
        ;;
    
    stop)
        print_status "Stopping GEE System..."
        stop_forge
        stop_praxis
        show_status
        ;;
    
    restart)
        print_status "Restarting GEE System..."
        stop_forge
        stop_praxis
        sleep 2
        start_forge
        start_praxis
        show_status
        ;;
    
    status)
        show_status
        ;;
    
    logs)
        tail_logs
        ;;
    
    forge-start)
        start_forge
        ;;
    
    forge-stop)
        stop_forge
        ;;
    
    forge-restart)
        stop_forge
        sleep 1
        start_forge
        ;;
    
    praxis-start)
        start_praxis
        ;;
    
    praxis-stop)
        stop_praxis
        ;;
    
    praxis-restart)
        stop_praxis
        sleep 1
        start_praxis
        ;;
    
    *)
        echo "GEE System Management Script"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|forge-start|forge-stop|forge-restart|praxis-start|praxis-stop|praxis-restart}"
        echo ""
        echo "Commands:"
        echo "  start         - Start both Forge and Praxis"
        echo "  stop          - Stop both Forge and Praxis"
        echo "  restart       - Restart both Forge and Praxis"
        echo "  status        - Show status of both services"
        echo "  logs          - Tail logs from both services"
        echo ""
        echo "Individual service commands:"
        echo "  forge-start   - Start only Forge"
        echo "  forge-stop    - Stop only Forge"
        echo "  forge-restart - Restart only Forge"
        echo "  praxis-start  - Start only Praxis"
        echo "  praxis-stop   - Stop only Praxis"
        echo "  praxis-restart- Restart only Praxis"
        echo ""
        exit 1
        ;;
esac

exit 0