# Toggl Client Reports - Docker Setup

This document explains how to set up and run the Toggl Client Reports application using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Toggl API token (get from https://track.toggl.com/profile)

## Quick Start

1. **Clone and setup environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Toggl API token
   ```

2. **Start the application**:
   ```bash
   docker-compose up -d
   ```

3. **Access the services**:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Database Admin: http://localhost:8080
   - Health Check: http://localhost:8000/health

## Services

### Backend API (Port 8000)
- FastAPI application with enhanced Toggl client
- Auto-reloading in development mode
- Swagger UI available at `/docs`

### PostgreSQL Database (Port 5432)
- Persistent data storage
- Automatic schema initialization
- Development data included

### Adminer (Port 8080)
- Web-based database administration
- Login: toggl_user / toggl_password
- Database: toggl_reports

## Development Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Access backend container
docker-compose exec backend bash

# Access database
docker-compose exec db psql -U toggl_user -d toggl_reports
```

## Testing the API

### Test Endpoints

1. **Connection test**:
   ```bash
   curl http://localhost:8000/api/test/connection
   ```

2. **Get clients** (replace {workspace_id}):
   ```bash
   curl http://localhost:8000/api/test/clients/{workspace_id}
   ```

3. **Get client reports** (replace {workspace_id}):
   ```bash
   curl http://localhost:8000/api/test/client-reports/{workspace_id}
   ```

### Using Swagger UI

Visit http://localhost:8000/docs to interact with the API using the built-in Swagger interface.

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required: Toggl API Token
TOGGL_API_TOKEN=your_api_token_here

# Optional: Default workspace ID
TOGGL_WORKSPACE_ID=123456

# Database (handled by Docker Compose)
DATABASE_URL=postgresql://toggl_user:toggl_password@db:5432/toggl_reports
```

### Database Schema

The database is automatically initialized with:
- `clients` - Client information
- `projects` - Project information with client relationships
- `members` - Team member information
- `rates` - Hourly rates (default and client-specific)
- `time_entries_cache` - Cached time entries for performance

## Troubleshooting

### Common Issues

1. **Port conflicts**:
   ```bash
   # Check if ports are in use
   lsof -i :8000
   lsof -i :5432
   ```

2. **Database connection issues**:
   ```bash
   # Check database logs
   docker-compose logs db
   
   # Reset database
   docker-compose down -v
   docker-compose up -d
   ```

3. **API authentication errors**:
   - Verify your `TOGGL_API_TOKEN` in `.env`
   - Check if token is valid: https://track.toggl.com/profile

### Container Health

Check container status:
```bash
docker-compose ps
```

Check application health:
```bash
curl http://localhost:8000/health
```

## Development Workflow

1. **Make code changes** in `backend/` directory
2. **Changes auto-reload** (no restart needed)
3. **Test changes** using the API endpoints
4. **View logs** with `docker-compose logs -f backend`

## Next Steps

Once Stage 1 is working:
- Stage 2: Add database models and rate management
- Stage 3: Build core business logic
- Stage 4: Add frontend container
- Stage 5: Production setup with Nginx

## File Structure

```
toggl-client-reports/
├── docker-compose.yml          # Development setup
├── .env                        # Environment variables
├── backend/                    # FastAPI backend
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   └── api/
│   │       └── test_routes.py  # Test endpoints
│   ├── toggl_client/
│   │   └── enhanced_client.py  # Enhanced Toggl client
│   └── config/
│       └── config.py          # Configuration
└── database/
    └── init.sql               # Database schema
```