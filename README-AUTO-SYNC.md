# Automatic Daily Sync Setup

This document explains how to set up and use the automatic daily sync feature for your Toggl data.

## Features

- **Automatic Daily Sync**: Syncs recent time entries daily at your chosen time
- **Free Plan Optimized**: Designed to work within the 30 API calls/hour limit
- **One-time Historical Import**: Import all historical data in chunks
- **Rate Limit Protection**: Prevents exceeding API limits
- **Smart Recommendations**: Automatically calculates optimal sync ranges

## Setup Instructions

### 1. Initial Historical Import

Before enabling automatic sync, you need to import historical data:

1. Go to **Settings** → **Data Synchronization**
2. Click **"Import Historical"** in the blue box
3. This will import all your historical data in 30-day chunks
4. Wait for completion (may take several hours for large datasets)

### 2. Enable Automatic Daily Sync

1. In the same Settings section, toggle **"Automatic Daily Sync"** to ON
2. Choose your preferred sync time (6 AM, 9 AM, 12 PM, 6 PM, or 9 PM)
3. Save your settings

### 3. Cron Job Setup (Optional)

For server environments, you can set up a cron job to ensure automatic sync runs:

```bash
# Edit your crontab
crontab -e

# Add this line to run every hour (the script will check if sync is needed)
0 * * * * cd /path/to/your/backend && python scripts/run_auto_sync.py

# Or use Docker
0 * * * * docker exec toggle-backend-1 python scripts/run_auto_sync.py
```

### 4. Environment Variables

Ensure these environment variables are set:

```bash
# Required
TOGGL_API_TOKEN=your_api_token_here
DATABASE_URL=postgresql://user:password@host:port/database

# Optional
LOG_LEVEL=INFO
```

## How It Works

### Automatic Sync Logic

1. **Time Check**: Runs only during the hour you specified
2. **Daily Limit**: Only syncs once per day, even if triggered multiple times
3. **Rate Limit Safety**: Calculates API usage before syncing
4. **Smart Range**: Syncs only days since last successful sync
5. **Free Plan Safe**: Typically uses 3-5 API calls per day

### API Usage Breakdown

| Operation | API Calls | Frequency |
|-----------|-----------|-----------|
| Daily Sync | 3-5 calls | Once daily |
| Historical Import | 5-8 calls per chunk | One-time setup |
| Manual Sync | Varies | As needed |

## Troubleshooting

### Common Issues

1. **"Sync not triggered"**: Check if auto_sync is enabled in settings
2. **"Rate limit exceeded"**: Wait an hour and try again
3. **"No historical data"**: Run the historical import first
4. **"Sync failed"**: Check API credentials and internet connection

### Checking Sync Status

Use the API endpoints to check sync status:

```bash
# Check if auto sync would run for a workspace
curl -X GET "http://localhost:8001/api/sync/daily-recommendation/842441"

# Manually trigger auto sync for testing
curl -X POST "http://localhost:8001/api/sync/auto-sync/842441"

# Trigger for all workspaces
curl -X POST "http://localhost:8001/api/sync/auto-sync-all"
```

### Logs

Check the application logs for sync activity:

```bash
# Docker logs
docker logs toggle-backend-1 | grep -i sync

# Application logs
tail -f /var/log/toggl-auto-sync.log
```

## Best Practices

### For Free Plan Users

1. **Run historical import during off-peak hours**
2. **Enable automatic daily sync** instead of manual syncing
3. **Set sync time** when you're not actively using the app
4. **Monitor API usage** through the UI warnings

### For Premium Plan Users

1. **Same setup as free plan** - works even better with higher limits
2. **Consider more frequent syncing** if needed
3. **Multiple workspace support** with no rate limit concerns

## Configuration Options

### Frontend Settings

- **Automatic Daily Sync**: Enable/disable automatic sync
- **Sync Time**: Choose daily sync time (6 AM, 9 AM, 12 PM, 6 PM, 9 PM)
- **Historical Import**: One-time import of all historical data

### Backend Settings

Settings are stored in the database:

```sql
-- Check current settings
SELECT * FROM settings WHERE key IN ('auto_sync', 'sync_interval');

-- Enable auto sync for workspace
INSERT INTO settings (key, value, workspace_id, scope) 
VALUES ('auto_sync', 'true', 842441, 'workspace');

-- Set sync time to 9 AM
INSERT INTO settings (key, value, workspace_id, scope) 
VALUES ('sync_interval', '9', 842441, 'workspace');
```

## Monitoring

### Health Checks

The system provides several ways to monitor sync health:

1. **Settings UI**: Shows last sync time and status
2. **API Endpoints**: Programmatic access to sync status
3. **Logs**: Detailed sync activity logging
4. **Database**: Sync history in `sync_logs` table

### Metrics

Monitor these metrics:

- **Daily sync success rate**
- **API calls per day**
- **Sync duration**
- **Data freshness** (time since last successful sync)

## Security

- **API tokens** are stored securely in environment variables
- **Rate limiting** prevents abuse
- **Database** access is properly authenticated
- **Logs** don't contain sensitive information

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review application logs
3. Verify environment variables
4. Test manual sync first
5. Contact support with specific error messages 