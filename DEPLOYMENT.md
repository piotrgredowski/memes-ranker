# Production Deployment Guide

This guide provides instructions for deploying the memes-ranker application to production with Docker, capable of handling 2000 concurrent users.

## Architecture Overview

The production setup includes:

- **Scalable FastAPI application** running with Gunicorn workers
- **Nginx load balancer** for distributing requests
- **Optimized SQLite database** with WAL mode for concurrent access
- **Docker containers** for easy deployment and scaling

## Prerequisites

- Docker and Docker Compose installed
- At least 2GB RAM and 2 CPU cores
- Static meme files in `static/memes/` directory

## Quick Start

1. **Configure environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your production settings
   ```

1. **Build and start the application:**

   ```bash
   docker-compose up --build
   ```

   The application will automatically:

   - Initialize the database if it doesn't exist
   - Create the required tables and schema
   - Start the FastAPI application with Gunicorn
   - Set up the Nginx load balancer

1. **Access the application:**

   - Main app: http://localhost
   - Admin dashboard: http://localhost/admin

## Database Management

### Host Database Storage

The database is stored on the host filesystem at `./data/memes.db` and bind-mounted into the container. This provides:

- **Direct access** from host system using any SQLite tool
- **Persistent storage** that survives container restarts
- **Easy backup** using standard file system tools
- **No volume management** complexity

### Automatic Initialization

The database is automatically initialized when the application starts. The Docker container will:

1. Check if the database exists at `/app/data/memes.db` (maps to `./data/memes.db` on host)
1. If not found, create the database with the required schema
1. Enable WAL mode for better concurrency
1. Set up foreign key constraints

### Manual Database Operations

To manually manage the database in a running container:

```bash
# Access running container
docker-compose exec app bash

# Initialize database manually (if needed)
python /app/init_db_prod.py

# Check database status
ls -la /app/data/

# Access SQLite directly
sqlite3 /app/data/memes.db ".tables"
```

### Database Backup

The database is stored on the host filesystem in the `./data` directory. To backup:

```bash
# Create backup (simple file copy)
cp data/memes.db backups/memes-backup-$(date +%Y%m%d).db

# Or create compressed backup
tar czf db-backup-$(date +%Y%m%d).tar.gz data/

# Restore backup
cp backups/memes-backup-YYYYMMDD.db data/memes.db
```

### Direct Database Access

Since the database is now stored on the host, you can access it directly:

```bash
# Direct SQLite access
sqlite3 data/memes.db

# View tables
sqlite3 data/memes.db ".tables"

# Query data
sqlite3 data/memes.db "SELECT * FROM sessions;"

# Use any SQLite GUI tool
# - DB Browser for SQLite
# - TablePlus
# - DBeaver
# - SQLite Studio
```

### Migration from Docker Volumes

If you're upgrading from a previous version that used Docker volumes:

```bash
# Stop the application
docker-compose down

# Copy data from old volume to host
docker run --rm -v memes-ranker_app-data:/olddata -v $(pwd):/host alpine cp -r /olddata /host/data

# Start with new configuration
docker-compose up -d
```

## Configuration

### Environment Variables (.env)

```bash
# Security - CHANGE THESE IN PRODUCTION
ADMIN_PASSWORD=your_secure_admin_password_here
JWT_SECRET_KEY=your_very_secure_jwt_secret_key_here

# Application
QR_CODE_URL=https://yourdomain.com
GUNICORN_WORKERS=4
```

### Scaling

To handle more concurrent users, you can:

1. **Scale application instances:**

   ```bash
   docker-compose up --scale app=5
   ```

1. **Adjust worker processes per instance:**

   - Edit `GUNICORN_WORKERS` in `.env`
   - Recommended: 2 × CPU cores + 1

1. **Optimize database:**

   - Database is already optimized for concurrent access
   - Consider PostgreSQL for very high loads

## Performance Specifications

This setup is designed to handle:

- **2000 concurrent users**
- **High-frequency voting/ranking operations**
- **Real-time WebSocket connections**
- **Static file serving**

## Monitoring

### Health Checks

- Application health: http://localhost/api/session/status
- Nginx health: http://localhost/health
- Docker health checks are configured automatically

### Logs

View application logs:

```bash
docker-compose logs -f app
```

View Nginx logs:

```bash
docker-compose logs -f nginx
```

## Security Features

- Rate limiting (10 requests/second for API endpoints)
- Security headers (XSS protection, CSRF protection)
- Non-root user in containers
- Secure cookie settings
- Input validation

## Backup Strategy

The database and logs are stored in Docker volumes:

- `app-data`: Contains the SQLite database
- `app-logs`: Contains application logs

Backup volumes regularly:

```bash
docker run --rm -v memes-ranker_app-data:/data -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz /data
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change the port in docker-compose.yml
1. **Memory issues**: Reduce GUNICORN_WORKERS
1. **Database locks**: Check SQLite WAL mode is enabled
1. **Static files not loading**: Ensure meme files are in `static/memes/`

### Performance Tuning

1. **Database optimization is automatic**
1. **Nginx caching** for static files
1. **Gunicorn worker management**
1. **Connection pooling** and keepalive

## Production Checklist

- [ ] Change default admin password
- [ ] Generate secure JWT secret key
- [ ] Configure proper domain in QR_CODE_URL
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerting
- [ ] Test with load testing script

## Load Testing

Use the provided load testing script:

```bash
python load_test.py
```

This will simulate concurrent users and measure performance.
