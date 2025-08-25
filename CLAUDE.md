# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **App Data Monitor and Analytics Platform** designed to automatically monitor, analyze, and alert on key business metrics from Apple App Store and Google Play Store. The system provides automated data collection, anomaly detection, and notifications via Lark (Feishu) for internal teams.

## Architecture

The system follows a **frontend-backend separation** with **integrated task scheduling** pattern:

### Core Components
1. **Management Backend (Django Admin UI)** - Configuration interface for apps, credentials, alert rules, and task scheduling
2. **Web Service (Django Web Server)** - Provides the web-based management UI (Django Admin)
3. **Database (PostgreSQL)** - Stores app configs, encrypted credentials, alert rules, data records, and task schedules
4. **Execution Module (Django Management Command)** - Worker process for data fetching and analysis
5. **Task Scheduler (Built-in Django Scheduler)** - Integrated scheduling system with admin interface
6. **Notification Module** - Handles Lark notifications and alerts with rich card formatting

### Data Flow
1. Admin configures apps, API credentials, alert thresholds, and task schedules via Django Admin interface
2. Built-in task scheduler triggers data collection tasks based on configured schedules
3. Worker fetches data from Apple/Google APIs, performs growth rate analysis and anomaly detection
4. System detects anomalies based on configured thresholds (DOD/WOW comparisons)
5. Daily reports and alerts sent to Lark channels using interactive card format
6. All data stored in PostgreSQL with encrypted sensitive credentials
7. Task execution history and logs are tracked for monitoring and debugging

## Technology Stack

- **Backend**: Django 4.2 + PostgreSQL 15
- **Database**: PostgreSQL with encrypted credential storage
- **Task Scheduling**: Built-in Django Scheduler + APScheduler (optional)
- **Data Processing**: pandas for growth rate calculations and analysis
- **Security**: cryptography library for credential encryption
- **API Integration**: Apple App Store Connect API + Google Play Console API
- **Notifications**: Lark (Feishu) Webhook API with interactive card messages
- **Deployment**: Docker + Docker Compose

## Key Models and Database Schema

- **App**: App information (name, platform iOS/Android, bundle_id, active status)
- **Credential**: Platform-specific encrypted API credentials (Apple App Store Connect, Google Play Console)
- **AlertRule**: Anomaly detection thresholds per app/metric with DOD/WOW/absolute comparison types
- **DailyReportConfig**: Lark webhook URLs and optional sheet IDs for data export
- **DataRecord**: Daily metrics storage with detailed download source breakdown
- **AlertLog**: Alert history with send status tracking
- **TaskSchedule**: Task scheduling configuration with frequency, time, and execution parameters
- **TaskExecution**: Task execution history with status, logs, and performance metrics

## Development Commands

### Environment Setup
```bash
# Start development environment
./start.sh  # Recommended - handles Docker setup and DB initialization

# Manual startup
docker-compose up -d
sleep 15
./init_db.sh
docker-compose exec web python manage.py createsuperuser

# Access Django shell in container
docker exec app_data_monitor-web-1 python manage.py shell
```

### Data Collection and Processing
```bash
# Run daily task (main data collection command)
python manage.py run_daily_task

# Run for specific app
python manage.py run_daily_task --app-id 1

# Run for specific date (YYYY-MM-DD)
python manage.py run_daily_task --date 2025-08-22

# Dry run mode (no data saving or notifications)
python manage.py run_daily_task --dry-run

# Skip notifications (data collection only)
python manage.py run_daily_task --skip-notifications
```

### Testing and Debugging
```bash
# Test API connections
python manage.py test_api_clients --mock-data  # Use mock data
python manage.py test_api_clients --app-id 1   # Test real API

# Test Lark webhooks
python manage.py test_webhook --test-all        # Test all configured webhooks
python manage.py test_webhook --app-id 1       # Test specific app webhooks
python manage.py test_webhook --webhook-url https://example.com/webhook

# Generate sample data for testing
python manage.py generate_sample_data
python manage.py generate_sample_data --with-anomalies
python manage.py generate_sample_data --app-id 1 --days 60
```

### Task Scheduling and Execution
```bash
# Manage task scheduler
python manage.py manage_scheduler start --daemon    # Start scheduler in daemon mode
python manage.py manage_scheduler stop              # Stop scheduler
python manage.py manage_scheduler status            # Show scheduler status
python manage.py manage_scheduler test              # Test scheduler logic

# Manual task execution
python manage.py execute_task --list-schedules      # List all task schedules
python manage.py execute_task --list-apps           # List all apps
python manage.py execute_task --schedule-id 1       # Execute specific schedule
python manage.py execute_task --app-id 1            # Execute task for specific app
python manage.py execute_task --date 2025-08-22     # Execute task for specific date
python manage.py execute_task --skip-notifications  # Execute without notifications

# Test specific schedule
python manage.py manage_scheduler test --test-schedule-id 1
```

### Database and Maintenance
```bash
# Database operations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# Troubleshooting database issues
./quick_fix.sh  # Reset database and volumes

# View logs
docker-compose logs -f web
```

## Task Scheduling Configuration

### Built-in Django Scheduler (Recommended)

The system now includes an integrated task scheduling system that can be managed through the Django Admin interface:

1. **Create Task Schedules**: Go to Django Admin → Task Schedules → Add Task Schedule
2. **Configure Execution Time**: Set frequency (daily/weekly/monthly), hour, minute, and other parameters
3. **Start Scheduler**: Run `python manage.py manage_scheduler start --daemon`
4. **Monitor Execution**: Check Task Execution records in Django Admin

### Legacy Cron Job Configuration (Optional)

For backward compatibility, you can still use cron jobs. Reference `crontab.example`:

```bash
# Daily data collection at 2 AM
0 2 * * * cd /path/to/app_data_monitor && python manage.py run_daily_task >> /var/log/app_monitor/daily_task.log 2>&1

# Optional: Weekly reports on Monday at 9 AM  
0 9 * * 1 cd /path/to/app_data_monitor && python manage.py run_daily_task --generate-weekly-report

# Start task scheduler (recommended approach)
@reboot cd /path/to/app_data_monitor && python manage.py manage_scheduler start --daemon
```

## Core Architecture Patterns

### Data Analysis Pipeline
The system implements a sophisticated analytics pipeline:
1. **Data Retrieval**: Platform-specific API clients handle Apple App Store Connect and Google Play Console APIs
2. **Growth Rate Calculation**: `DataAnalyzer` class computes DOD (day-over-day) and WOW (week-over-week) growth rates
3. **Anomaly Detection**: `AnomalyDetector` compares current metrics against configured thresholds
4. **Insight Generation**: Automated insight generation based on data patterns and trends
5. **Rich Reporting**: Lark card-based reports with interactive elements and detailed breakdowns

### Security Implementation
- All API credentials encrypted using `cryptography.fernet` before database storage
- Sensitive configuration via environment variables (SECRET_KEY, DB passwords, ENCRYPTION_KEY)
- No hardcoded secrets in codebase
- Encrypted credential retrieval through model property methods

### Notification System
- **Lark Integration**: Rich interactive card messages with sections, charts, and call-to-action buttons
- **Multi-channel Support**: Separate webhooks for daily reports vs. alert notifications
- **Intelligent Formatting**: Source breakdown with percentage calculations and emoji indicators
- **Error Handling**: Comprehensive notification failure handling and retry logic

## Deployment

- **Containerized**: Docker and Docker Compose for consistent deployment
- **Environment Configuration**: All sensitive config via environment variables
- **Database**: PostgreSQL 15 with persistent volumes
- **Logging**: Structured logging to stdout for container log collection
- **Health Checks**: Built-in PostgreSQL health checks in docker-compose

## Important File Locations

- `monitoring/management/commands/run_daily_task.py`: Main data collection orchestrator
- `monitoring/utils/analytics.py`: Data analysis and growth rate calculations
- `monitoring/utils/anomaly_detector.py`: Alert rule evaluation and anomaly detection
- `monitoring/utils/lark_notifier.py`: Lark notification formatting and sending
- `monitoring/utils/api_clients.py`: Apple and Google API client implementations
- `monitoring/utils/task_executor.py`: Task scheduling and execution engine
- `monitoring/models.py`: Core database models and encrypted credential handling
- `monitoring/admin.py`: Django admin customizations and export functionality
- `monitoring/management/commands/manage_scheduler.py`: Scheduler management command
- `monitoring/management/commands/execute_task.py`: Manual task execution command

## Development Notes

- The system processes data with a configurable delay (default is 2 days) to account for API data availability. This can be set with the `DATA_FETCH_DELAY_DAYS` environment variable.
- Apple App Store Connect uses JWT authentication with private key
- Google Play Console uses service account JSON authentication
- Download source breakdown includes 6 categories: App Store Search, Web Referrer, App Referrer, App Store Browse, Institutional, Other
- All monetary values stored as Decimal fields for precision
- Rate limiting and API quotas are handled by the respective API clients
- Task scheduling uses minute-level precision and supports daily, weekly, and monthly frequencies
- Task execution history includes detailed logs, performance metrics, and retry capabilities
- Built-in scheduler runs in a background thread and can be managed via Django admin or command line