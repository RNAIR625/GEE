#!/bin/bash

# GEE Execution Demo Startup Script
echo "Starting GEE Execution Demo..."

# Check if required directories exist
if [ ! -d "Forge" ] || [ ! -d "Praxis" ]; then
    echo "Error: Please run this script from the GEE root directory"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to kill background processes on exit
cleanup() {
    echo "Stopping services..."
    kill $FORGE_PID 2>/dev/null
    kill $PRAXIS_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Praxis (Go execution engine) in background
echo "Starting Praxis execution engine on port 8080..."
cd Praxis
if [ ! -f "praxis" ]; then
    echo "Building Praxis..."
    go build -o praxis cmd/praxis/main.go
    if [ $? -ne 0 ]; then
        echo "Failed to build Praxis"
        exit 1
    fi
fi

./praxis > ../logs/praxis.log 2>&1 &
PRAXIS_PID=$!
cd ..

# Wait for Praxis to start
echo "Waiting for Praxis to start..."
sleep 3

# Check if Praxis is running
if ! curl -s http://localhost:8080/api/v1/health > /dev/null; then
    echo "Warning: Praxis may not have started correctly. Check logs/praxis.log"
else
    echo "✓ Praxis started successfully on http://localhost:8080"
fi

# Start Forge (Python Flask UI) in background
echo "Starting Forge builder UI on port 5001..."
cd Forge

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Initialize database if needed
if [ ! -f "instance/GEE.db" ]; then
    echo "Initializing database..."
    python3 -c "from db_helpers import init_db; init_db()"
fi

python3 app.py > ../logs/forge.log 2>&1 &
FORGE_PID=$!
cd ..

# Wait for Forge to start
echo "Waiting for Forge to start..."
sleep 3

# Check if Forge is running
if ! curl -s http://localhost:5001/health > /dev/null; then
    echo "Warning: Forge may not have started correctly. Check logs/forge.log"
else
    echo "✓ Forge started successfully on http://localhost:5001"
fi

echo ""
echo "=== GEE Execution Demo Ready ==="
echo "Forge Builder UI:     http://localhost:5001"
echo "Praxis Execution API: http://localhost:8080"
echo "Execution Test Page:  http://localhost:5001/execution/test"
echo ""
echo "Services are running in background. Press Ctrl+C to stop all services."
echo "Logs are available in the logs/ directory."
echo ""

# Keep script running
while true; do
    # Check if both services are still running
    if ! kill -0 $FORGE_PID 2>/dev/null; then
        echo "Forge stopped unexpectedly"
        break
    fi
    if ! kill -0 $PRAXIS_PID 2>/dev/null; then
        echo "Praxis stopped unexpectedly"
        break
    fi
    sleep 5
done

# Cleanup
cleanup