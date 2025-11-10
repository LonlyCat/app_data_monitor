# API Clients Implementation Guide

## Overview

This document describes the TypeScript/Deno implementation of Apple App Store Connect and Google Play Console API clients for Supabase Edge Functions. These clients were ported from the original Python implementation in `monitoring/utils/api_clients.py`.

## File Location

- **Implementation**: `supabase/functions/_shared/api-clients.ts`
- **Usage**: `supabase/functions/collect-data/index.ts`
- **Reference**: `monitoring/utils/api_clients.py` (original Python)

## Apple App Store Connect Client

### Overview

`AppleAppStoreConnectClient` fetches analytics data from Apple's App Store Connect API, including downloads, sessions, deletions, and download source breakdown.

### Authentication

Uses **JWT ES256** authentication:
- Requires: `issuer_id`, `key_id`, `private_key`
- Token validity: 20 minutes
- Auto-refreshes when expired

```typescript
const client = new AppleAppStoreConnectClient({
  issuer_id: 'xxx',
  key_id: 'yyy',
  private_key: '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----'
});
```

### Key Features

#### 1. Analytics Report Management

- **Check for existing reports**: Finds ONGOING analytics report requests
- **Create new reports**: Creates analytics report request if none exists
- **Fetch report instances**: Gets daily granularity report instances with date filtering

#### 2. Data Collection

Processes three types of reports:
- **Standard Install Report**: First-time downloads, updates, reinstalls, source breakdown
- **Detailed Install Report**: Deletion events
- **Session Report**: App sessions and unique devices

#### 3. Source Type Breakdown

Extracts download sources into 6 categories:
- `App Store search`
- `Web referrer`
- `App referrer`
- `App Store browse`
- `Institutional purchase`
- `Other`

#### 4. CSV Processing

- Downloads gzip-compressed TSV files
- Decompresses using Deno's `DecompressionStream`
- Parses tab-separated values
- Aggregates daily data by date

### API Methods

```typescript
// Get app info by bundle ID
async getAppInfo(bundleId: string): Promise<any>

// Get analytics data for a specific date
async getAnalyticsData(bundleId: string, targetDate?: Date): Promise<AppleAnalyticsData>
```

### Response Structure

```typescript
interface AppleAnalyticsData {
  downloads: number;              // First-time downloads
  sessions: number;               // App sessions
  deletions: number;              // App deletions
  unique_devices?: number;        // Unique devices (from sessions)
  updates?: number;               // App updates
  reinstalls?: number;            // Auto-downloads, restores

  // Source breakdown
  downloads_app_store_search: number;
  downloads_web_referrer: number;
  downloads_app_referrer: number;
  downloads_app_store_browse: number;
  downloads_institutional: number;
  downloads_other: number;

  raw_data?: any;                 // Full API response
  error?: string;                 // Error message if any
}
```

### Implementation Details

#### JWT Token Generation

Uses `jose` library for ES256 signing:

```typescript
const privateKey = await jose.importPKCS8(this.privateKey, 'ES256');
const jwt = await new jose.SignJWT({})
  .setProtectedHeader({ alg: 'ES256', kid: this.keyId, typ: 'JWT' })
  .setIssuer(this.issuerId)
  .setIssuedAt(now)
  .setExpirationTime(expires)
  .setAudience('appstoreconnect-v1')
  .sign(privateKey);
```

#### Retry Logic

Uses exponential backoff for transient errors:
- Max retries: 3
- Initial delay: 1 second
- Max delay: 10 seconds
- No retry for 400, 401, 403, 404 errors

#### Date Handling

- Target date: Date for which data is requested
- Processing date: Target date + 1 day (Apple generates reports next day)
- Daily aggregation: Groups data by date and optionally filters to target date

### Error Handling

- Returns zero data with error message on failure
- Logs warnings for partial data
- Continues processing other apps on individual failures

## Google Play Console Client

### Overview

`GooglePlayConsoleClient` fetches statistics data from Google Play Console using Google Cloud Storage (GCS) integration. Downloads are extracted from overview CSV reports stored in GCS buckets.

### Authentication

Uses **OAuth2 Service Account** with JWT:
- Requires: `service_account_key` (JSON), `gcs_bucket_name`, `gcs_project_id`
- Token validity: 1 hour
- Auto-refreshes when expired

```typescript
const client = new GooglePlayConsoleClient({
  service_account_key: '{"type":"service_account",...}',
  gcs_bucket_name: 'pubsite_prod_rev_xxxxx',
  gcs_project_id: 'your-project-id'
});
```

### Key Features

#### 1. GCS Integration

- **List blobs**: Searches for overview CSV reports in GCS
- **Download blobs**: Fetches CSV files from GCS
- **Encoding detection**: Auto-detects UTF-16/UTF-8 encoding

#### 2. Month-based Lookup

- Searches for reports in target month
- Falls back to previous month if not found
- Selects most recent report by update time

#### 3. Data Extraction

Parses overview CSV to extract:
- **Daily User Installs**: New installations per day
- **Daily User Uninstalls**: Uninstallations per day

#### 4. Date Fallback Logic

- Attempts exact date match first
- Falls back to nearest available date (≤ target date)
- Logs warnings for fallback usage

### API Methods

```typescript
// Get app info by package name
async getAppInfo(packageName: string): Promise<any>

// Get statistics data for a specific date
async getStatisticsData(packageName: string, targetDate: Date): Promise<GoogleAnalyticsData>

// Alias for getStatisticsData
async getHistoricalData(packageName: string, targetDate: Date): Promise<GoogleAnalyticsData>
```

### Response Structure

```typescript
interface GoogleAnalyticsData {
  downloads: number;              // Daily user installs
  sessions: number;               // Always 0 (not available)
  deletions: number;              // Daily user uninstalls
  sessions_available: boolean;    // Always false

  effective_date?: string;        // Actual date used (may differ from target)
  available_dates?: string[];     // All available dates in CSV
  daily_map?: Record<string, {    // All daily data
    downloads: number;
    deletions: number;
  }>;
  max_available_date?: string;    // Latest date in CSV

  raw_data?: any;                 // Full CSV data
  error?: string;                 // Error message if any
}
```

### Implementation Details

#### OAuth2 Token Generation

Uses `jose` library for RS256 signing:

```typescript
const privateKey = await jose.importPKCS8(
  this.serviceAccountInfo.private_key,
  'RS256'
);

const jwt = await new jose.SignJWT({
  scope: 'https://www.googleapis.com/auth/androidpublisher https://www.googleapis.com/auth/devstorage.read_only',
})
  .setProtectedHeader({ alg: 'RS256', typ: 'JWT' })
  .setIssuer(this.serviceAccountInfo.client_email)
  .setAudience('https://oauth2.googleapis.com/token')
  .setIssuedAt(now)
  .setExpirationTime(expires)
  .sign(privateKey);

// Exchange JWT for access token
const response = await fetch('https://oauth2.googleapis.com/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    assertion: jwt,
  }),
});
```

#### GCS Blob Lookup

Constructs prefix based on package name and target month:

```typescript
// Example: stats/installs/installs_com.example.app_202501
const prefix = `stats/installs/installs_${packageName}_${yearMonth}`;
```

Filters for overview reports:
```typescript
const overviewBlobs = items.filter(
  (item: any) =>
    item.name.endsWith('_overview.csv') ||
    (item.name.includes('overview') && item.name.endsWith('.csv'))
);
```

#### CSV Encoding Detection

Tries multiple encodings in order:
1. `utf-16le` (most common for Play Console)
2. `utf-16`
3. `utf-8`

Validates encoding by checking for CSV characters (`,`, `\t`, `\n`).

#### Date Fallback Strategy

1. Build map of all dates in CSV
2. Try exact date match first
3. If no match, filter dates ≤ target date
4. Use most recent available date
5. Log warning about fallback usage

### Error Handling

- Returns zero data with error message on failure
- Logs detailed error messages with context
- Provides available dates in error messages for debugging

## Integration in collect-data Function

### Usage Example

```typescript
// For iOS apps
const client = new AppleAppStoreConnectClient(config);
const targetDate = new Date('2025-01-10');
const data = await client.getAnalyticsData('com.example.app', targetDate);

// For Android apps
const client = new GooglePlayConsoleClient(config);
const targetDate = new Date('2025-01-10');
const data = await client.getStatisticsData('com.example.app', targetDate);
```

### Data Mapping to DataRecord

```typescript
// Apple data
const dataRecord: Partial<DataRecord> = {
  downloads: analyticsData.downloads,
  sessions: analyticsData.sessions,
  deletions: analyticsData.deletions,
  unique_devices: analyticsData.unique_devices,
  downloads_app_store_search: analyticsData.downloads_app_store_search,
  downloads_web_referrer: analyticsData.downloads_web_referrer,
  downloads_app_referrer: analyticsData.downloads_app_referrer,
  downloads_app_store_browse: analyticsData.downloads_app_store_browse,
  downloads_institutional: analyticsData.downloads_institutional,
  downloads_other: analyticsData.downloads_other,
  // ...
};

// Google data (no source breakdown)
const dataRecord: Partial<DataRecord> = {
  downloads: statsData.downloads,
  sessions: 0, // Not available
  deletions: statsData.deletions,
  // Source fields all set to 0
  // ...
};
```

## Key Differences from Python Implementation

### Apple Client

1. **JWT Library**: Uses `jose` instead of `PyJWT`
2. **Decompression**: Uses Deno's `DecompressionStream` instead of `gzip`
3. **CSV Parsing**: Uses Deno std library's CSV parser instead of `pandas`
4. **Async/Await**: Native async/await syntax (similar to Python)

### Google Client

1. **GCS Access**: Uses REST API instead of `google-cloud-storage` library
2. **Encoding Detection**: Uses Deno's `TextDecoder` with multiple encodings
3. **CSV Parsing**: Uses Deno std library's CSV parser instead of `pandas`
4. **No pandas**: All data processing done with native TypeScript

## Configuration Requirements

### Apple Credentials

Required fields in `credentials` table (encrypted):
```json
{
  "issuer_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "key_id": "XXXXXXXXXX",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```

### Google Credentials

Required fields in `credentials` table (encrypted):
```json
{
  "service_account_key": "{\"type\":\"service_account\",...}",
  "gcs_bucket_name": "pubsite_prod_rev_xxxxx",
  "gcs_project_id": "your-project-id"
}
```

## Environment Variables

- `DATA_FETCH_DELAY_DAYS`: Days to delay data fetching (default: 2)
- `ENCRYPTION_KEY`: Key for credential encryption/decryption
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key for database access

## Testing

### Local Testing

```bash
# Test with specific app and date
curl -X POST http://localhost:54321/functions/v1/collect-data \
  -H "Authorization: Bearer $SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"app_id": 1, "date": "2025-01-10", "dry_run": true}'

# Test all active apps
curl -X POST http://localhost:54321/functions/v1/collect-data \
  -H "Authorization: Bearer $SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

### Dry Run Mode

Pass `"dry_run": true` to fetch data without saving to database. Useful for:
- Testing API credentials
- Verifying data format
- Debugging data issues

## Monitoring and Logs

View function logs:
```bash
supabase functions logs collect-data --tail
```

Key log messages:
- `Generated Apple JWT token` - JWT authentication successful
- `Generated Google OAuth2 token` - OAuth2 authentication successful
- `Selected overview report` - Found GCS CSV report
- `Extracted [Apple/Google] data for [date]` - Successfully fetched data
- `Using fallback date` - Date fallback occurred (Google only)

## Error Scenarios

### Apple Errors

1. **Invalid credentials**: Check `issuer_id`, `key_id`, `private_key`
2. **No analytics report request**: Automatically creates new request
3. **No data for date**: Check if app has analytics enabled
4. **Report processing delay**: Apple generates reports next day

### Google Errors

1. **Invalid service account**: Check `service_account_key` JSON
2. **GCS bucket not found**: Verify `gcs_bucket_name`
3. **No overview CSV**: Check if reporting is enabled in Play Console
4. **Date not available**: Uses fallback to nearest date

## Performance Considerations

### Apple

- JWT token cached for 20 minutes
- Report instances fetched once per date
- CSV downloads may take several seconds (gzip compressed)
- Multiple API calls per app (app info, report request, instances, segments)

### Google

- OAuth2 token cached for 1 hour
- GCS listing may take 1-2 seconds
- CSV download may take several seconds (can be large)
- Encoding detection adds minimal overhead

### Optimization Tips

1. **Batch processing**: Process multiple apps in parallel (already implemented)
2. **Caching**: Consider caching report data for recent dates
3. **Rate limiting**: Add delays between API calls if hitting rate limits
4. **Retry strategy**: Current implementation uses 3 retries with exponential backoff

## Future Enhancements

### Potential Improvements

1. **Revenue data**: Add in-app purchase and subscription revenue fetching
2. **Rating data**: Fetch app ratings and review counts
3. **Crash data**: Add crash analytics from App Store Connect
4. **More metrics**: Add active devices, retention, etc.
5. **Caching layer**: Cache recent reports to reduce API calls
6. **Webhook notifications**: Send alerts on data collection failures

### Additional APIs

1. **Apple Sales and Trends**: Financial data and app units
2. **Google Play Developer API**: Additional metrics and reports
3. **Apple Search Ads**: Advertising performance data
4. **Firebase Analytics**: Additional user behavior data

## References

- [Apple App Store Connect API](https://developer.apple.com/documentation/appstoreconnectapi)
- [Google Play Developer API](https://developers.google.com/android-publisher)
- [Google Cloud Storage API](https://cloud.google.com/storage/docs/json_api)
- [jose (JWT library)](https://github.com/panva/jose)
- [Deno Standard Library](https://deno.land/std)

## Support

For issues or questions:
1. Check function logs for detailed error messages
2. Verify credentials are correctly encrypted and stored
3. Test API credentials using dry-run mode
4. Review this documentation for common error scenarios
5. Check Python implementation for reference behavior
