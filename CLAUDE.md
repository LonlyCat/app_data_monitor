# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **App Data Monitor and Analytics Platform** designed to automatically monitor, analyze, and alert on key business metrics from Apple App Store and Google Play Store. The system provides automated data collection, anomaly detection, and notifications via Lark (Feishu) for internal teams.

## Architecture

The system follows a **modern serverless architecture** with **Supabase backend** and **Next.js frontend**:

### Core Components
1. **Web Application (Next.js 14)** - Modern React-based UI with HeroUI components
2. **Backend (Supabase)** - PostgreSQL database + Edge Functions + Authentication
3. **Edge Functions (Deno)** - Serverless functions for data collection and API integrations
4. **Database (PostgreSQL)** - Managed by Supabase with Row Level Security (RLS)
5. **Scheduled Functions** - Automated tasks using Supabase pg_cron integration
6. **Notification Module** - Lark notifications with rich card formatting

### Data Flow
1. User configures apps, API credentials, and alert thresholds via web interface
2. Scheduled functions trigger Edge Functions for data collection
3. Edge Functions fetch data from Apple/Google APIs using API client modules
4. Data is analyzed and stored in PostgreSQL with anomaly detection
5. Daily reports and alerts sent to Lark channels
6. All data secured with RLS policies and encrypted credential storage

## Technology Stack

- **Frontend**: Next.js 14 + React 18 + TypeScript + HeroUI 2.7.11 + Tailwind CSS 3.x
- **Backend**: Supabase (PostgreSQL 15 + Edge Functions + Authentication + Storage)
- **Edge Runtime**: Deno (TypeScript/JavaScript)
- **UI Components**: HeroUI 2.7.11 with @heroui/theme
- **Styling**: Tailwind CSS 3.x with custom theme configuration
- **Data Processing**: Edge Functions with TypeScript
- **API Integration**: Apple App Store Connect API + Google Play Console API
- **Notifications**: Lark (Feishu) Webhook API with interactive card messages
- **Package Manager**: pnpm
- **Development**: Supabase CLI + Next.js development server

## Key Architecture Patterns

### Supabase Structure
- **Migrations**: Database schema in `supabase/migrations/`
- **Edge Functions**: Serverless functions in `supabase/functions/`
- **Configuration**: Project settings in `supabase/config.toml`

### Next.js Application
- **App Router**: Using Next.js 14 App Router pattern
- **Server Components**: Default for optimal performance
- **Client Components**: Marked with 'use client' directive
- **API Routes**: Not used - all backend via Supabase Edge Functions

### Supabase Client Pattern
- **Browser Client**: `createBrowserClient` from `@supabase/ssr` for client components
- **Server Client**: `createServerClient` from `@supabase/ssr` for server components
- **Cookie Handling**: Integrated with Next.js cookies for authentication

## HeroUI Configuration (Critical)

### Correct Setup Pattern

Based on this project's configuration, HeroUI requires specific setup:

1. **Package Dependencies**:
```json
{
  "dependencies": {
    "@heroui/react": "2.7.11"
  },
  "devDependencies": {
    "@heroui/theme": "^2.0.0"
  }
}
```

2. **Tailwind Config** (`tailwind.config.ts`):
```typescript
import { heroui } from '@heroui/theme'  // CRITICAL: Import from @heroui/theme, NOT @heroui/react!

export default {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  plugins: [heroui({
    themes: {
      light: { /* theme config */ },
      dark: { /* theme config */ }
    }
  })]
}
```

3. **Layout Configuration** (`app/layout.tsx`):
```typescript
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html className="dark" lang="zh" suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

**Common Mistakes to Avoid**:
- ❌ Importing `heroui` from `@heroui/react` instead of `@heroui/theme`
- ❌ Missing `@heroui/theme` in devDependencies
- ❌ Not including theme utility classes (`bg-background`, `text-foreground`)
- ❌ Manual CSS background/foreground overrides conflicting with theme

## Development Commands

### Supabase Commands

```bash
# Start local Supabase instance
supabase start

# Stop Supabase
supabase stop

# Check status
supabase status

# Reset database
supabase db reset

# Create new migration
supabase migration new migration_name

# Apply migrations
supabase db push

# Deploy Edge Functions
supabase functions deploy

# Deploy specific function
supabase functions deploy collect-daily-data

# View function logs
supabase functions logs collect-daily-data

# Test function locally
supabase functions serve
```

### Next.js Web Application Commands

```bash
cd web

# Install dependencies
pnpm install

# Development mode
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Run linter
pnpm lint

# Clean cache
rm -rf .next
```

### Testing Commands

```bash
# Test Edge Function locally
curl -i --location --request POST \
  'http://127.0.0.1:54321/functions/v1/collect-daily-data' \
  --header 'Authorization: Bearer YOUR_ANON_KEY' \
  --header 'Content-Type: application/json' \
  --data '{"date": "2025-11-15"}'
```

## Project Structure

```
app_data_monitor/
├── web/                          # Next.js frontend application
│   ├── app/                      # Next.js App Router pages
│   ├── components/               # React components
│   ├── lib/                      # Utility libraries
│   │   ├── supabase.ts          # Main Supabase client export
│   │   └── supabase/            # Supabase client modules
│   │       ├── client.ts        # Browser client
│   │       ├── server.ts        # Server client
│   │       └── index.ts         # Type definitions
│   ├── public/                   # Static assets
│   ├── .env.local.example       # Environment variables template
│   ├── next.config.js           # Next.js configuration
│   ├── tailwind.config.ts       # Tailwind + HeroUI configuration
│   └── package.json             # Dependencies
├── supabase/                     # Supabase backend
│   ├── functions/               # Edge Functions
│   │   ├── collect-daily-data/  # Main data collection function
│   │   ├── apple-api-client/    # Apple API integration
│   │   ├── google-api-client/   # Google API integration
│   │   └── send-lark-notification/ # Lark notification sender
│   ├── migrations/              # Database migrations
│   └── config.toml              # Supabase configuration
├── README.md                    # Project readme
└── CLAUDE.md                    # This file
```

## Important File Locations

- `web/lib/supabase.ts`: Main Supabase client export for client components
- `web/lib/supabase/client.ts`: Browser-specific Supabase client
- `web/lib/supabase/server.ts`: Server-specific Supabase client with cookies
- `web/tailwind.config.ts`: Tailwind and HeroUI theme configuration
- `web/app/layout.tsx`: Root layout with theme setup
- `supabase/functions/collect-daily-data/index.ts`: Main data collection orchestrator
- `supabase/functions/apple-api-client/index.ts`: Apple API integration
- `supabase/functions/google-api-client/index.ts`: Google API integration
- `supabase/migrations/`: All database schema and RLS policies

## Database Models

Main tables (defined in `supabase/migrations/`):

- `apps`: Application information (name, platform, bundle_id, status)
- `credentials`: Platform-specific encrypted API credentials
- `alert_rules`: Anomaly detection thresholds per app/metric
- `daily_report_configs`: Lark webhook URLs for notifications
- `data_records`: Daily metrics with download source breakdown
- `alert_logs`: Alert history with send status
- `task_schedules`: Task scheduling configuration
- `task_executions`: Task execution history with logs

## Security Implementation

- **Row Level Security (RLS)**: Enabled on all tables with appropriate policies
- **Encrypted Credentials**: Sensitive API credentials encrypted before storage
- **Environment Variables**: All secrets via environment variables
- **Authentication**: Managed by Supabase Auth (to be implemented)

## Common Development Patterns

### Creating a New Edge Function

```bash
# Create new function
supabase functions new function-name

# Write your function in supabase/functions/function-name/index.ts
# Deploy function
supabase functions deploy function-name
```

### Adding a New Database Table

```bash
# Create migration
supabase migration new add_table_name

# Edit the migration file in supabase/migrations/
# Apply migration locally
supabase db reset

# Push to production
supabase db push
```

### Adding a New Page to Web App

```typescript
// Create file: web/app/my-page/page.tsx
export default function MyPage() {
  return <div>My Page</div>
}

// Accessible at http://localhost:3000/my-page
```

## Environment Variables

### Web Application (`.env.local`)
```bash
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key_here
```

### Supabase (managed in Supabase dashboard)
- `ENCRYPTION_KEY`: For encrypting API credentials
- `APPLE_API_*`: Apple API configuration (in Edge Function secrets)
- `GOOGLE_API_*`: Google API configuration (in Edge Function secrets)

## Git Workflow

This project uses feature branches with the pattern `claude/[feature-name]-[session-id]`.

Always develop on the designated branch and push when complete.

## Development Notes

- **HeroUI Version**: Fixed at 2.7.11 for Tailwind 3.x compatibility (tested and verified)
- **Import Sources**: Always import `heroui` plugin from `@heroui/theme`, not `@heroui/react`
- **Supabase Local Development**: Use `supabase start` for local testing before deployment
- **Edge Functions**: Written in TypeScript for Deno runtime (not Node.js)
- **RLS Policies**: Test thoroughly - they can be tricky to debug
- **Module Resolution**: Ensure `web/lib/` is not ignored by `.gitignore` (use `/lib/` for root only)

## Troubleshooting

### Common Issues and Solutions

1. **Module not found: '@/lib/supabase'**
   - Check `.gitignore` doesn't block `web/lib/`
   - Clear Next.js cache: `rm -rf web/.next`
   - Reinstall dependencies: `pnpm install`

2. **HeroUI styles not working**
   - Verify import from `@heroui/theme` not `@heroui/react`
   - Check `@heroui/theme` in devDependencies
   - Ensure theme utilities in layout.tsx

3. **Supabase CLI errors**
   - Check `config.toml` format (case-sensitive values)
   - Remove deprecated settings (port, edge_functions)
   - Update Supabase CLI to latest version

4. **Edge Function deployment fails**
   - Check for TypeScript errors
   - Verify Deno imports (use npm: prefix for Node modules)
   - Check function logs: `supabase functions logs function-name`

## Best Practices

1. **Use Server Components by default** - Only add 'use client' when necessary
2. **Keep Edge Functions small** - Break complex logic into helper modules
3. **Test migrations locally first** - Use `supabase db reset` before pushing
4. **Follow naming conventions** - snake_case for database, camelCase for TypeScript
5. **Document RLS policies** - They're critical for security
6. **Use TypeScript strictly** - Helps catch errors early
7. **Keep secrets in environment variables** - Never hardcode credentials

## Migration History

This project was migrated from Django + PostgreSQL to Supabase + Next.js. All legacy Django code has been removed. The current architecture is fully serverless and modern.

---

**Last Updated**: 2025-11-15
**Architecture Version**: 2.0 (Supabase + Next.js)
