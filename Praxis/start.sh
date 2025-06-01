#!/bin/bash

# Praxis Start Script

echo "Starting Praxis Rules Execution Engine..."
export PATH=$PATH:/usr/local/go/bin/

# Create data directory if it doesn't exist
mkdir -p data

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo "Error: Go is not installed or not in PATH"
    echo "Please install Go 1.21+ from https://golang.org/dl/"
    exit 1
fi

# Run Praxis
echo "Running on http://localhost:8080"
go run cmd/praxis/main.go