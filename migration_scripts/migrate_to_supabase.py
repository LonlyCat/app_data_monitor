#!/usr/bin/env python3
"""
Data Migration Script: Django PostgreSQL → Supabase
Migrates data from existing Django database to Supabase

Usage:
    python migrate_to_supabase.py --source-db-url postgresql://user:pass@host:port/dbname \
                                   --supabase-url https://xxx.supabase.co \
                                   --supabase-key your-service-role-key

Requirements:
    pip install psycopg2-binary requests python-dotenv
"""

import os
import sys
import argparse
import psycopg2
import requests
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

# Supabase REST API client
class SupabaseClient:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip('/')
        self.service_key = service_key
        self.headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

    def insert(self, table: str, data: List[Dict[str, Any]]) -> bool:
        """Insert data into Supabase table"""
        url = f'{self.url}/rest/v1/{table}'
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            print(f'✅ Inserted {len(data)} records into {table}')
            return True
        except requests.exceptions.RequestException as e:
            print(f'❌ Failed to insert into {table}: {e}')
            if hasattr(e, 'response') and e.response is not None:
                print(f'   Response: {e.response.text}')
            return False

    def upsert(self, table: str, data: List[Dict[str, Any]], on_conflict: Optional[str] = None) -> bool:
        """Upsert data into Supabase table"""
        url = f'{self.url}/rest/v1/{table}'
        headers = self.headers.copy()
        if on_conflict:
            headers['Prefer'] = f'resolution=merge-duplicates,return=representation'
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            print(f'✅ Upserted {len(data)} records into {table}')
            return True
        except requests.exceptions.RequestException as e:
            print(f'❌ Failed to upsert into {table}: {e}')
            if hasattr(e, 'response') and e.response is not None:
                print(f'   Response: {e.response.text}')
            return False

    def count(self, table: str) -> int:
        """Get count of records in table"""
        url = f'{self.url}/rest/v1/{table}?select=count'
        headers = self.headers.copy()
        headers['Prefer'] = 'count=exact'
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            count_header = response.headers.get('Content-Range', '0-0/0')
            total = int(count_header.split('/')[-1])
            return total
        except:
            return 0


# Data migration functions
class DataMigration:
    def __init__(self, source_db_url: str, supabase_url: str, supabase_key: str):
        # Connect to source database
        parsed = urlparse(source_db_url)
        self.source_conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password
        )
        self.supabase = SupabaseClient(supabase_url, supabase_key)

    def migrate_apps(self):
        """Migrate apps table"""
        print('\n📱 Migrating apps...')
        cursor = self.source_conn.cursor()
        cursor.execute("""
            SELECT id, name, platform, bundle_id, is_active, created_at, updated_at
            FROM monitoring_app
            ORDER BY id
        """)

        rows = cursor.fetchall()
        if not rows:
            print('   No apps to migrate')
            return

        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'name': row[1],
                'platform': row[2],
                'bundle_id': row[3],
                'is_active': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None,
            })

        self.supabase.upsert('apps', data)
        cursor.close()

    def migrate_credentials(self):
        """Migrate credentials table"""
        print('\n🔑 Migrating credentials...')
        cursor = self.source_conn.cursor()
        cursor.execute("""
            SELECT id, platform, _config_data, is_active, created_at, updated_at
            FROM monitoring_credential
            ORDER BY id
        """)

        rows = cursor.fetchall()
        if not rows:
            print('   No credentials to migrate')
            return

        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'platform': row[1],
                'config_encrypted': row[2],  # Already encrypted
                'is_active': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'updated_at': row[5].isoformat() if row[5] else None,
            })

        self.supabase.upsert('credentials', data)
        cursor.close()

    def migrate_alert_rules(self):
        """Migrate alert rules"""
        print('\n⚠️  Migrating alert rules...')
        cursor = self.source_conn.cursor()
        cursor.execute("""
            SELECT id, app_id, metric, comparison_type, threshold_min, threshold_max,
                   is_active, lark_webhook_alert, created_at, updated_at
            FROM monitoring_alertrule
            ORDER BY id
        """)

        rows = cursor.fetchall()
        if not rows:
            print('   No alert rules to migrate')
            return

        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'app_id': row[1],
                'metric': row[2],
                'comparison_type': row[3],
                'threshold_min': float(row[4]) if row[4] is not None else None,
                'threshold_max': float(row[5]) if row[5] is not None else None,
                'is_active': row[6],
                'lark_webhook_alert': row[7],
                'created_at': row[8].isoformat() if row[8] else None,
                'updated_at': row[9].isoformat() if row[9] else None,
            })

        self.supabase.upsert('alert_rules', data)
        cursor.close()

    def migrate_daily_report_configs(self):
        """Migrate daily report configs"""
        print('\n📊 Migrating daily report configs...')
        cursor = self.source_conn.cursor()
        cursor.execute("""
            SELECT id, app_id, lark_webhook_daily, lark_sheet_id, is_active,
                   created_at, updated_at
            FROM monitoring_dailyreportconfig
            ORDER BY id
        """)

        rows = cursor.fetchall()
        if not rows:
            print('   No daily report configs to migrate')
            return

        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'app_id': row[1],
                'lark_webhook_daily': row[2],
                'lark_sheet_id': row[3],
                'is_active': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None,
            })

        self.supabase.upsert('daily_report_configs', data)
        cursor.close()

    def migrate_data_records(self, batch_size: int = 100):
        """Migrate data records (in batches due to potential large size)"""
        print('\n📈 Migrating data records...')
        cursor = self.source_conn.cursor()

        # Get total count
        cursor.execute('SELECT COUNT(*) FROM monitoring_datarecord')
        total = cursor.fetchone()[0]
        print(f'   Total records to migrate: {total}')

        if total == 0:
            return

        # Fetch in batches
        offset = 0
        migrated = 0

        while offset < total:
            cursor.execute(f"""
                SELECT id, app_id, date, downloads, sessions, deletions, unique_devices,
                       downloads_app_store_search, downloads_web_referrer, downloads_app_referrer,
                       downloads_app_store_browse, downloads_institutional, downloads_other,
                       revenue, rating, raw_data, created_at
                FROM monitoring_datarecord
                ORDER BY id
                LIMIT {batch_size} OFFSET {offset}
            """)

            rows = cursor.fetchall()
            if not rows:
                break

            data = []
            for row in rows:
                data.append({
                    'id': row[0],
                    'app_id': row[1],
                    'date': row[2].isoformat() if row[2] else None,
                    'downloads': row[3],
                    'sessions': row[4],
                    'deletions': row[5],
                    'unique_devices': row[6],
                    'downloads_app_store_search': row[7],
                    'downloads_web_referrer': row[8],
                    'downloads_app_referrer': row[9],
                    'downloads_app_store_browse': row[10],
                    'downloads_institutional': row[11],
                    'downloads_other': row[12],
                    'revenue': float(row[13]) if row[13] is not None else 0.0,
                    'rating': float(row[14]) if row[14] is not None else None,
                    'raw_data': row[15] if row[15] else {},
                    'created_at': row[16].isoformat() if row[16] else None,
                })

            self.supabase.upsert('data_records', data)
            migrated += len(data)
            offset += batch_size
            print(f'   Progress: {migrated}/{total} ({migrated*100//total}%)')

        cursor.close()

    def migrate_task_schedules(self):
        """Migrate task schedules"""
        print('\n⏰ Migrating task schedules...')
        cursor = self.source_conn.cursor()
        cursor.execute("""
            SELECT id, name, task_type, app_id, frequency, hour, minute, weekday, day_of_month,
                   is_active, skip_notifications, retry_count, timeout_minutes,
                   created_at, updated_at
            FROM monitoring_taskschedule
            ORDER BY id
        """)

        rows = cursor.fetchall()
        if not rows:
            print('   No task schedules to migrate')
            return

        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'name': row[1],
                'task_type': row[2],
                'app_id': row[3],
                'frequency': row[4],
                'hour': row[5],
                'minute': row[6],
                'weekday': row[7],
                'day_of_month': row[8],
                'is_active': row[9],
                'skip_notifications': row[10],
                'retry_count': row[11],
                'timeout_minutes': row[12],
                'created_at': row[13].isoformat() if row[13] else None,
                'updated_at': row[14].isoformat() if row[14] else None,
            })

        self.supabase.upsert('task_schedules', data)
        cursor.close()

    def migrate_task_executions(self, batch_size: int = 100):
        """Migrate task executions (recent only to avoid huge volume)"""
        print('\n📝 Migrating task executions (recent 1000 only)...')
        cursor = self.source_conn.cursor()
        cursor.execute("""
            SELECT id, schedule_id, trigger_type, status, app_id, target_date,
                   started_at, completed_at, duration_seconds, success_count, error_count,
                   alerts_generated, notifications_sent, output_log, error_log, retry_count,
                   created_at
            FROM monitoring_taskexecution
            ORDER BY created_at DESC
            LIMIT 1000
        """)

        rows = cursor.fetchall()
        if not rows:
            print('   No task executions to migrate')
            return

        data = []
        for row in rows:
            data.append({
                'id': row[0],
                'schedule_id': row[1],
                'trigger_type': row[2],
                'status': row[3],
                'app_id': row[4],
                'target_date': row[5].isoformat() if row[5] else None,
                'started_at': row[6].isoformat() if row[6] else None,
                'completed_at': row[7].isoformat() if row[7] else None,
                'duration_seconds': row[8],
                'success_count': row[9],
                'error_count': row[10],
                'alerts_generated': row[11],
                'notifications_sent': row[12],
                'output_log': row[13] or '',
                'error_log': row[14] or '',
                'retry_count': row[15],
                'created_at': row[16].isoformat() if row[16] else None,
            })

        self.supabase.upsert('task_executions', data)
        cursor.close()

    def run(self):
        """Run full migration"""
        print('🚀 Starting data migration from Django to Supabase...\n')

        try:
            self.migrate_apps()
            self.migrate_credentials()
            self.migrate_alert_rules()
            self.migrate_daily_report_configs()
            self.migrate_data_records()
            self.migrate_task_schedules()
            self.migrate_task_executions()

            print('\n✅ Migration completed successfully!')
            print('\nSummary:')
            print(f'   Apps: {self.supabase.count("apps")}')
            print(f'   Credentials: {self.supabase.count("credentials")}')
            print(f'   Alert Rules: {self.supabase.count("alert_rules")}')
            print(f'   Daily Report Configs: {self.supabase.count("daily_report_configs")}')
            print(f'   Data Records: {self.supabase.count("data_records")}')
            print(f'   Task Schedules: {self.supabase.count("task_schedules")}')
            print(f'   Task Executions: {self.supabase.count("task_executions")}')

        except Exception as e:
            print(f'\n❌ Migration failed: {e}')
            raise

        finally:
            self.source_conn.close()


def main():
    parser = argparse.ArgumentParser(description='Migrate data from Django PostgreSQL to Supabase')
    parser.add_argument('--source-db-url', required=True, help='Source PostgreSQL database URL')
    parser.add_argument('--supabase-url', required=True, help='Supabase project URL')
    parser.add_argument('--supabase-key', required=True, help='Supabase service role key')

    args = parser.parse_args()

    migration = DataMigration(
        source_db_url=args.source_db_url,
        supabase_url=args.supabase_url,
        supabase_key=args.supabase_key
    )

    migration.run()


if __name__ == '__main__':
    main()
