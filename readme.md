# SLEP Application with Oracle Integration

This application provides a management interface for field classes, fields, tables, and environments with Oracle database integration.

## Project Structure

The application has been restructured for better maintainability:

```
slep-app/
├── app.py                  # Main application file
├── db_helpers.py           # Database helper functions
├── oracle_helpers.py       # Oracle connectivity functions
├── routes/                 # Route modules
│   ├── __init__.py         # Makes routes a package
│   ├── base.py             # Basic routes (homepage, etc.)
│   ├── classes.py          # Class management routes
│   ├── env_config.py       # Environment configuration routes
│   ├── fields.py           # Field management routes
│   ├── tables.py           # Table management routes
├── instance/               # SQLite database location
│   └── SLEP.db             # SQLite database
├── static/                 # Static files
└── templates/              # HTML templates
```

## Features

- Modular code organization with route blueprints
- Oracle database connectivity
- Unique application runtime ID for connection isolation
- Proper error handling and resource cleanup
- Enhanced security for database connections

## Prerequisites

- Python 3.6 or higher
- Oracle Instant Client (for Oracle connectivity)
- Flask and cx_Oracle Python packages

## Setup

1. Run the setup script to create required directories and install dependencies:

```bash
chmod +x setup.sh
./setup.sh
```

2. Set up the Oracle Instant Client:

```bash
# Set environment variable to point to your Oracle Instant Client
export LD_LIBRARY_PATH=~/oracle/instantclient_11_2:$LD_LIBRARY_PATH
```

3. Run the application:

```bash
python app.py
```

## Oracle Connectivity

This application supports connecting to Oracle databases using the following approach:

1. Configure an Oracle environment in the Environment Configuration page
2. Test the connection to verify credentials
3. Access Oracle tables and run queries through the Tables page

## Troubleshooting

- If you encounter Oracle connectivity issues, ensure that:
  - Oracle Instant Client is installed correctly
  - The LD_LIBRARY_PATH environment variable is set correctly
  - Your Oracle credentials are valid
  - The database is accessible from your network

- For runtime errors, check the Flask debug output which will provide detailed information about the error.

- For database errors, check that your SQLite database is properly initialized.
