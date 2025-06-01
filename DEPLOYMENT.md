# GEE System Deployment Guide

This guide covers various deployment options for the GEE System (Forge + Praxis).

## Quick Start

### Development (Linux/WSL)
```bash
# Start both services
./manage.sh start

# Check status
./manage.sh status

# View logs
./manage.sh logs

# Restart both services
./manage.sh restart

# Stop both services
./manage.sh stop
```

### Development (Windows)
```cmd
# Start both services
manage.bat start

# Check status
manage.bat status

# View logs (opens in Notepad)
manage.bat logs

# Restart both services
manage.bat restart

# Stop both services
manage.bat stop
```

## Management Commands

Both `manage.sh` (Linux) and `manage.bat` (Windows) support:

- `start` - Start both Forge and Praxis
- `stop` - Stop both Forge and Praxis
- `restart` - Restart both services
- `status` - Show current status
- `logs` - View/tail logs
- `forge-start` - Start only Forge
- `forge-stop` - Stop only Forge
- `forge-restart` - Restart only Forge
- `praxis-start` - Start only Praxis
- `praxis-stop` - Stop only Praxis
- `praxis-restart` - Restart only Praxis

## Docker Deployment

### Using Docker Compose
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Individual containers
```bash
# Build images
docker build -t gee-forge ./Forge
docker build -t gee-praxis ./Praxis

# Run containers
docker run -d -p 5000:5000 --name forge gee-forge
docker run -d -p 8080:8080 --name praxis gee-praxis
```

## Production Deployment (Linux)

### Using Systemd

1. Copy the application to `/opt/gee/`:
```bash
sudo mkdir -p /opt/gee
sudo cp -r Forge Praxis Config /opt/gee/
sudo chown -R gee:gee /opt/gee
```

2. Install systemd services:
```bash
cd systemd
sudo ./install.sh
```

3. Start services:
```bash
# Start all services
sudo systemctl start gee.target

# Enable auto-start on boot
sudo systemctl enable gee.target

# Check status
sudo systemctl status gee-*
```

4. View logs:
```bash
# Forge logs
sudo journalctl -u gee-forge -f

# Praxis logs
sudo journalctl -u gee-praxis -f
```

## Configuration

### Ports Configuration
Edit `/Config/ports.yaml`:
```yaml
forge:
  host: localhost
  port: 5000

praxis:
  host: localhost
  port: 8080
```

### Environment Variables

#### Forge
- `FLASK_ENV` - Set to 'production' for production deployment
- `PYTHONUNBUFFERED` - Set to '1' for real-time logging

#### Praxis
- `PRAXIS_CONFIG` - Path to configuration file
- `PRAXIS_ENV` - Environment (development/production)

## Health Monitoring

Both services expose health endpoints:
- Forge: `http://localhost:5000/health`
- Praxis: `http://localhost:8080/api/v1/health`

## Troubleshooting

### Services won't start
1. Check if ports are already in use:
   ```bash
   netstat -tlnp | grep -E '5000|8080'
   ```

2. Check logs:
   ```bash
   # Development
   tail -f logs/forge.log logs/praxis.log
   
   # Production (systemd)
   sudo journalctl -u gee-forge -n 50
   sudo journalctl -u gee-praxis -n 50
   ```

3. Verify dependencies:
   - Python 3.7+ for Forge
   - Go 1.21+ for Praxis

### Database connection issues
1. Ensure SQLite database exists:
   ```bash
   ls -la Forge/instance/GEE.db
   ```

2. Apply database updates:
   ```bash
   cd Forge
   sqlite3 instance/GEE.db < db_updates_praxis.sql
   ```

### Process management issues
- Linux: Check PID files in `/tmp/gee/`
- Windows: Check PID files in `%TEMP%\gee\`

## Security Considerations

1. **File Permissions**
   - Ensure database files are readable only by the application user
   - Log files should be write-protected

2. **Network Security**
   - Use a reverse proxy (nginx/Apache) for production
   - Enable SSL/TLS for external access
   - Configure firewall rules appropriately

3. **Database Security**
   - Regular backups of SQLite database
   - Use read-only connections where possible

## Backup and Recovery

### Backup
```bash
# Backup database
cp Forge/instance/GEE.db backup/GEE_$(date +%Y%m%d_%H%M%S).db

# Backup configurations
tar -czf backup/config_$(date +%Y%m%d_%H%M%S).tar.gz Config/
```

### Restore
```bash
# Stop services
./manage.sh stop

# Restore database
cp backup/GEE_20240115_120000.db Forge/instance/GEE.db

# Start services
./manage.sh start
```

## Monitoring

Consider using monitoring tools like:
- Prometheus + Grafana for metrics
- ELK Stack for log aggregation
- Uptime monitoring services

## Performance Tuning

### Forge (Python)
- Use production WSGI server (gunicorn/uwsgi)
- Enable response caching
- Optimize database queries

### Praxis (Go)
- Adjust GOMAXPROCS for CPU utilization
- Configure connection pooling
- Enable pprof for profiling

## Support

For issues or questions:
1. Check application logs
2. Review configuration files
3. Verify network connectivity
4. Ensure all dependencies are installed