# Toggl Reports Dashboard

A comprehensive web application for visualizing Toggl time tracking data with client reports, member performance analytics, and financial calculations. Built with FastAPI backend, React frontend, and PostgreSQL database.

## 🚀 Features

### 📊 Dashboard & Reports
- **Workspace Overview**: Total hours, earnings, and team performance metrics
- **Client Reports**: Detailed breakdown by client with billable hours and earnings
- **Member Performance**: Individual team member analytics and client allocation
- **Interactive Charts**: Bar charts and pie charts for visual data representation
- **Multi-Currency Support**: USD and EUR financial calculations

### ⚙️ Administration
- **Rate Management**: Set default hourly rates and client-specific overrides
- **User Management**: Track team members and their performance
- **Data Synchronization**: Automatic and manual sync with Toggl API
- **Settings Configuration**: Workspace preferences and sync intervals

### 🔧 Technical Features
- **Real-time Data**: Integration with Toggl Track API v9 and Reports API v3
- **Rate Limiting**: Smart API throttling and exponential backoff
- **Caching**: Performance optimization with TTL-based caching
- **Error Handling**: Comprehensive error management and fallback mechanisms
- **Responsive Design**: Mobile-friendly interface with Tailwind CSS

## 📋 Requirements

- Docker and Docker Compose
- Toggl Track account with API access
- Valid Toggl API token ([Get from Toggl Track](https://track.toggl.com/profile))
- Workspace ID from your Toggl workspace

## 🛠️ Quick Start

### Environment Setup

1. **Navigate to the project:**
   ```bash
   cd /path/to/toggl
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables:**
   ```bash
   # Required
   TOGGL_API_TOKEN=your_api_token_here
   TOGGL_WORKSPACE_ID=123456

   # Optional
   TOGGL_EMAIL=your_email@example.com
   TOGGL_PASSWORD=your_password
   ```

### Development Setup

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Access the application:**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Database Admin**: http://localhost:8080

3. **Initialize the database:**
   ```bash
   # The database will auto-initialize on first run
   # Check logs: docker-compose logs backend
   ```

### Production Deployment

1. **Build for production:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
   ```

## 🏗️ Architecture

### Backend (FastAPI)
- **Location**: `./backend/`
- **API Documentation**: Auto-generated OpenAPI docs at `/docs`
- **Key Components**:
  - `app/api/`: REST API endpoints
  - `app/services/`: Business logic and data processing
  - `app/models/`: Database models with SQLAlchemy
  - `toggl_client/`: Enhanced Toggl API integration

### Frontend (React + TypeScript)
- **Location**: `./frontend/`
- **Framework**: React 18 with TypeScript and Vite
- **Styling**: Tailwind CSS with custom design system
- **Charts**: Recharts for data visualization
- **Key Features**:
  - Responsive dashboard with client/member drill-downs
  - Admin panel for rate management
  - Settings page for configuration
  - Error handling and loading states

### Database (PostgreSQL)
- **Models**: Users, Clients, Projects, TimeEntries, Rates
- **Features**: Automatic migrations, indexing, relationships
- **Admin**: Adminer interface for database management

## 📡 API Endpoints

### Reports
- `GET /api/reports/workspace/{workspace_id}` - Workspace overview
- `GET /api/reports/client/{client_id}` - Client details
- `GET /api/reports/member/{member_id}` - Member performance

### Rate Management
- `GET /api/rates/workspace/{workspace_id}` - All workspace rates
- `POST /api/rates/` - Create/update rate
- `GET /api/rates/{member_id}` - Member-specific rates

### Data Management
- `POST /api/sync/workspace/{workspace_id}` - Manual sync
- `GET /api/members/{workspace_id}` - Team members
- `GET /api/clients/{workspace_id}` - Workspace clients

## 🔧 Development

### Local Development
```bash
# Backend only
cd backend && pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# Frontend only  
cd frontend && npm install
npm run dev

# Database
docker run -d -p 5432:5432 -e POSTGRES_DB=toggl_reports postgres:15-alpine
```

### Testing
```bash
# Backend tests
cd backend && pytest tests/ --cov=app

# Frontend tests
cd frontend && npm test

# API testing
# Use the interactive docs at http://localhost:8000/docs
```

### Code Quality
```bash
# Backend
black backend/ && flake8 backend/ && mypy backend/

# Frontend
cd frontend && npm run lint && npm run type-check
```

## ⚙️ Configuration

### Environment Variables
- `TOGGL_API_TOKEN`: Your Toggl API token (required)
- `TOGGL_WORKSPACE_ID`: Default workspace ID (optional)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis cache URL (optional)
- `LOG_LEVEL`: Application log level (DEBUG, INFO, WARNING, ERROR)

### Rate Limiting
- Default: 1 request/second to Toggl API
- Automatic exponential backoff for 429 responses
- Configurable via environment variables

### Caching
- Default TTL: 300 seconds (5 minutes)
- Automatic invalidation on data updates
- Redis backend for production environments

## 🚨 Troubleshooting

### Common Issues

1. **API Authentication Errors**
   ```bash
   # Check your API token
   curl -H "Authorization: Basic $(echo -n 'your_token:api_token' | base64)" \
        https://api.track.toggl.com/api/v9/me
   ```

2. **Database Connection Issues**
   ```bash
   # Check database logs
   docker-compose logs db
   
   # Test connection
   docker-compose exec db psql -U toggl_user -d toggl_reports
   ```

3. **Frontend Build Issues**
   ```bash
   # Clear node modules and reinstall
   cd frontend && rm -rf node_modules package-lock.json
   npm install
   ```

### Logs and Monitoring
```bash
# View all logs
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Check health
curl http://localhost:8000/health
curl http://localhost:3000/health
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks
5. Submit pull request

### Code Standards
- **Backend**: Black formatting, Flake8 linting, MyPy type checking
- **Frontend**: ESLint, Prettier, TypeScript strict mode
- **Commits**: Conventional commit messages
- **Testing**: Minimum 80% code coverage

## 📚 Resources

- **Documentation**: Check the `/docs` API endpoint
- **Issues**: Report bugs via GitHub issues
- **API**: Toggl API documentation at https://developers.track.toggl.com/

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with** FastAPI, React, PostgreSQL, Docker, and ❤️ 