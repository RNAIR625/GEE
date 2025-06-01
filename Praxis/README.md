# Praxis - Go Rules Execution Engine

Praxis is a high-performance Go-based rules execution engine that reads rule definitions from the Forge SQLite database and executes them in a thread-safe manner.

## Features

- **SQLite Database Upload**: Receive and store SQLite databases from Forge
- **Data Reading**: Read Classes, Fields, and Flow Definitions from SQLite
- **Thread-Safe Execution**: Handle multiple parallel requests without data corruption
- **RESTful API**: Clean API for database management and data retrieval

## Installation

1. Ensure Go 1.21+ is installed
2. Clone the repository
3. Install dependencies:
   ```bash
   go mod download
   ```

## Configuration

Edit `configs/praxis.yaml`:

```yaml
server:
  host: localhost
  port: 8080

database:
  storage_path: ./data
```

## Running Praxis

```bash
go run cmd/praxis/main.go
```

Or build and run:

```bash
go build -o praxis cmd/praxis/main.go
./praxis
```

## API Endpoints

### Health Check
- **GET** `/api/v1/health`
  - Returns server health status

### Status
- **GET** `/api/v1/status`
  - Returns detailed server and database status

### Database Upload
- **POST** `/api/v1/database/upload`
  - Upload SQLite database file
  - Form field: `database` (multipart file)

### Get Field Classes
- **GET** `/api/v1/field-classes`
  - Returns all field classes from the database

### Get Fields
- **GET** `/api/v1/fields`
  - Returns all fields from the database

### Get Flow Definitions
- **GET** `/api/v1/flow-definitions`
  - Returns all flow definitions from the database

## Integration with Forge

1. In Forge, navigate to Environment Configuration
2. Click "Configure Praxis" 
3. Enter Praxis host and port
4. Test the connection
5. Click "Sync to Praxis" to upload the current database

## Architecture

- **Thread-Safe Design**: Each request operates in its own execution context
- **Immutable Templates**: Configuration data is loaded once and shared read-only
- **Request Isolation**: No shared mutable state between requests

## Development

### Project Structure
```
praxis/
├── cmd/praxis/          # Application entry point
├── internal/
│   ├── api/            # HTTP API handlers
│   ├── config/         # Configuration management
│   ├── db/             # Database operations
│   └── models/         # Data models
├── configs/            # Configuration files
└── data/               # Database storage
```

### Building for Production

```bash
go build -ldflags="-s -w" -o praxis cmd/praxis/main.go
```

## Port Configuration

The default ports are configured in `/Config/ports.yaml`:
- Forge: 5000
- Praxis: 8080