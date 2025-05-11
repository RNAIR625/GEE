#!/bin/bash

# Create directories for project structure
mkdir -p instance
mkdir -p routes

# Install required packages
pip install flask cx_Oracle

# Set environment variables for Oracle
echo "Setting up environment variables for Oracle..."
if [ -z "$LD_LIBRARY_PATH" ]; then
    echo "LD_LIBRARY_PATH is not set. Please set it to point to your Oracle Instant Client directory."
    echo "For example: export LD_LIBRARY_PATH=~/oracle/instantclient_11_2:\$LD_LIBRARY_PATH"
else
    echo "LD_LIBRARY_PATH is already set to: $LD_LIBRARY_PATH"
fi

# Create __init__.py in routes directory to make it a package
touch routes/__init__.py

echo "Setup complete. Make sure to set LD_LIBRARY_PATH to point to your Oracle Instant Client directory."
echo "Run the application with 'python app.py'"
