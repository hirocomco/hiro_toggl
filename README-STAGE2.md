# Toggl Client Reports - Stage 2 Complete

Stage 2 adds persistent data storage, rate management, and data synchronization capabilities.

## 🎉 Stage 2 Features Added

### Database Models & ORM
- **SQLAlchemy Models**: Complete database schema with relationships
- **Tables**: `clients`, `projects`, `members`, `rates`, `time_entries_cache`, `sync_logs`
- **Migrations**: Alembic integration for database versioning
- **Relationships**: Proper foreign key relationships and indexes

### Rate Management System
- **RateService**: Comprehensive rate management with client-specific overrides
- **Default & Client Rates**: Members can have default rates and client-specific rates
- **Rate History**: Track rate changes over time with effective dates
- **Currency Support**: USD and EUR rates with automatic calculation
- **Earnings Calculator**: Calculate earnings based on time and rates

### Data Synchronization
- **SyncService**: Sync data from Toggl API to local database
- **Selective Sync**: Sync clients, projects, members, or time entries independently
- **Full Sync**: Complete workspace synchronization
- **Sync Logging**: Track all sync operations with detailed logs
- **Background Processing**: Async sync operations
- **Data Cleanup**: Automatic cleanup of old cached data

## 🔧 New API Endpoints

### Rate Management (`/api/rates/`)
- `POST /` - Create/update rates
- `GET /member/{member_id}` - Get all rates for a member
- `GET /client/{client_id}` - Get all rates for a client
- `GET /workspace/{workspace_id}` - Get all current rates in workspace
- `PUT /{rate_id}` - Update existing rate
- `DELETE /{rate_id}` - Delete rate
- `POST /calculate-earnings/{member_id}` - Calculate earnings
- `GET /history/member/{member_id}` - Get rate history

### Data Sync (`/api/sync/`)
- `POST /start` - Start synchronization
- `GET /status/{workspace_id}` - Get sync status
- `GET /logs/{workspace_id}` - Get sync logs
- `POST /cleanup/{workspace_id}` - Cleanup old data
- `GET /test/connection` - Test Toggl API connection
- `POST /force-sync/{workspace_id}` - Force full sync
- `GET /summary/{workspace_id}` - Get data summary

## 🚀 How to Use

### 1. Start the Application
```bash
docker compose up -d
```

### 2. Initialize Database
```bash
# Run database migrations
docker compose exec backend alembic upgrade head
```

### 3. Sync Data from Toggl
```bash
# Test connection first
curl http://localhost:8000/api/sync/test/connection

# Start full sync (replace 123456 with your workspace ID)
curl -X POST http://localhost:8000/api/sync/start \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": 123456, "sync_type": "full"}'
```

### 4. Set Up Rates
```bash
# Set default rate for a member (replace member_id)
curl -X POST http://localhost:8000/api/rates/ \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": 1,
    "hourly_rate_usd": 75.00,
    "hourly_rate_eur": 70.00
  }'

# Set client-specific rate
curl -X POST http://localhost:8000/api/rates/ \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": 1,
    "client_id": 1,
    "hourly_rate_usd": 90.00,
    "hourly_rate_eur": 85.00
  }'
```

### 5. Calculate Earnings
```bash
# Calculate earnings for 8 hours of work
curl -X POST http://localhost:8000/api/rates/calculate-earnings/1 \
  -H "Content-Type: application/json" \
  -d '{
    "duration_seconds": 28800,
    "currency": "usd",
    "client_id": 1
  }'
```

## 📊 Database Schema

### Key Tables
- **clients**: Client information synced from Toggl
- **projects**: Projects with client relationships
- **members**: Team members/users
- **rates**: Hourly rates (default and client-specific)
- **time_entries_cache**: Cached time entries for performance
- **sync_logs**: Track all synchronization operations

### Rate Management Logic
1. **Default Rates**: Each member can have default USD/EUR rates
2. **Client-Specific Rates**: Override default rates for specific clients
3. **Rate History**: All rate changes are tracked with effective dates
4. **Rate Resolution**: Client-specific rates take precedence over default rates

## 🔄 Data Flow

1. **Sync**: Toggl API → Local Database
   - Clients, projects, members, time entries
   - Maintains relationships and references

2. **Rate Management**: Admin Interface
   - Set default rates per member
   - Override rates for specific clients
   - Track rate history

3. **Calculations**: Business Logic
   - Apply appropriate rates to time entries
   - Calculate earnings in USD/EUR
   - Generate financial reports

## 🧪 Testing the New Features

### Test Data Sync
```bash
# Check sync status
curl http://localhost:8000/api/sync/status/123456

# View sync logs
curl http://localhost:8000/api/sync/logs/123456

# Get data summary
curl http://localhost:8000/api/sync/summary/123456
```

### Test Rate Management
```bash
# Get member rates
curl http://localhost:8000/api/rates/member/1

# Get workspace rates
curl http://localhost:8000/api/rates/workspace/123456

# Get rate history
curl http://localhost:8000/api/rates/history/member/1
```

## 🔗 API Documentation

Visit http://localhost:8000/docs for interactive API documentation with all the new endpoints.

## 📁 Updated File Structure

```
backend/
├── app/
│   ├── models/
│   │   ├── database.py        # Database connection
│   │   └── models.py          # SQLAlchemy models
│   ├── services/
│   │   ├── rate_service.py    # Rate management logic
│   │   └── sync_service.py    # Data synchronization logic
│   ├── api/
│   │   ├── rates.py           # Rate management endpoints
│   │   ├── sync.py            # Sync endpoints
│   │   └── test_routes.py     # Original test endpoints
│   └── main.py                # Updated FastAPI app
├── alembic/                   # Database migrations
├── alembic.ini                # Alembic configuration
└── requirements.txt           # Updated dependencies
```

## 🎯 Next Steps - Stage 3

Stage 3 will add:
- **Core Business Logic**: Report generation with financial calculations
- **Client Reports**: Detailed client reports with member breakdowns
- **Financial Totals**: USD/EUR totals based on rates
- **Advanced Filtering**: Date ranges, client/member filtering
- **Report Caching**: Performance optimizations

Ready to continue with Stage 3?