# pg_cron 任务调度配置指南

本文档说明如何在 Supabase 中配置 pg_cron 定时任务来自动调用 Edge Functions。

## 方案选择

Supabase 提供多种任务调度方案：

### 1. Supabase Scheduled Functions（推荐）⭐

最简单的方案，无需额外配置 pg_cron。

**优点:**
- 无需手动配置数据库
- 自动管理调度
- 与 Edge Functions 深度集成
- 支持在 Dashboard 中管理

**使用方法:**

在 Edge Function 中添加 cron 配置：

```typescript
// supabase/functions/collect-data/index.ts
export const cron = '0 2 * * *'  // Every day at 2:00 AM UTC

serve(async (req) => {
  // ... function code
})
```

然后部署：

```bash
supabase functions deploy collect-data --with-schedule
```

查看和管理：
- Supabase Dashboard → Edge Functions → Crons

### 2. pg_cron + pg_net（完全自定义）

使用 PostgreSQL 的 pg_cron 扩展配合 pg_net 调用 HTTP API。

**优点:**
- 完全控制调度逻辑
- 可以执行复杂的 SQL 逻辑
- 不依赖 Supabase 特定功能

**缺点:**
- 配置复杂
- 需要手动管理

**使用方法:**

见下方详细配置。

### 3. 外部 Cron 服务

使用 GitHub Actions、AWS EventBridge 等外部服务。

**优点:**
- 与数据库解耦
- 更灵活的调度选项

**缺点:**
- 需要额外的基础设施
- 可能产生额外成本

## 推荐配置：使用 Supabase Scheduled Functions

### 1. 配置数据采集任务

编辑 `supabase/functions/collect-data/index.ts`，在文件开头添加：

```typescript
// Schedule: Every day at 2:00 AM UTC
export const cron = '0 2 * * *'
```

### 2. 配置告警检查任务

编辑 `supabase/functions/check-alerts/index.ts`，在文件开头添加：

```typescript
// Schedule: Every day at 3:00 AM UTC
export const cron = '0 3 * * *'
```

### 3. 部署带调度的函数

```bash
supabase functions deploy collect-data --with-schedule
supabase functions deploy check-alerts --with-schedule
```

### 4. 验证调度配置

在 Supabase Dashboard 中查看：
1. 进入 Edge Functions 页面
2. 点击 "Crons" 标签
3. 确认任务已正确配置

## 高级配置：使用 pg_cron

如果需要更复杂的调度逻辑，可以使用 pg_cron。

### 1. 启用扩展

在 Supabase SQL Editor 中执行：

```sql
create extension if not exists pg_cron;
create extension if not exists pg_net;
```

### 2. 配置应用设置

```sql
-- Set Supabase URL (replace with your project URL)
alter database postgres set app.settings.supabase_url to 'https://xxxxx.supabase.co';

-- Set Service Role Key (replace with your service role key)
-- IMPORTANT: This stores the key in database, ensure proper security
alter database postgres set app.settings.service_role_key to 'your-service-role-key';
```

**安全提示:** 不要将 Service Role Key 存储在公开的地方。考虑使用 Vault 或环境变量。

### 3. 创建 HTTP 调用函数

```sql
create or replace function call_edge_function(
  function_name text,
  payload jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
as $$
declare
  supabase_url text := current_setting('app.settings.supabase_url');
  service_role_key text := current_setting('app.settings.service_role_key');
  response_status int;
  response_body text;
  response_json jsonb;
begin
  -- Call Edge Function using pg_net
  select status, content::text
  into response_status, response_body
  from net.http_post(
    url := supabase_url || '/functions/v1/' || function_name,
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || service_role_key,
      'Content-Type', 'application/json'
    ),
    body := payload
  );

  -- Parse response
  if response_status = 200 then
    response_json := response_body::jsonb;
    return jsonb_build_object(
      'success', true,
      'status', response_status,
      'data', response_json
    );
  else
    raise warning 'Edge Function call failed: % - %', response_status, response_body;
    return jsonb_build_object(
      'success', false,
      'status', response_status,
      'error', response_body
    );
  end if;
end;
$$;
```

### 4. 配置定时任务

```sql
-- Daily data collection at 2:00 AM UTC
select cron.schedule(
  'collect-daily-data',
  '0 2 * * *',
  $$select call_edge_function('collect-data', '{}'::jsonb);$$
);

-- Daily alert check at 3:00 AM UTC
select cron.schedule(
  'check-daily-alerts',
  '0 3 * * *',
  $$select call_edge_function('check-alerts', '{}'::jsonb);$$
);

-- Weekly cleanup on Sunday at 1:00 AM UTC
select cron.schedule(
  'cleanup-old-executions',
  '0 1 * * 0',
  $$
  delete from task_executions
  where created_at < now() - interval '90 days'
    and status in ('success', 'failed', 'timeout', 'cancelled');
  $$
);
```

### 5. 查看和管理任务

```sql
-- View all cron jobs
select * from cron.job;

-- View job run history
select *
from cron.job_run_details
order by start_time desc
limit 100;

-- Unschedule a job
select cron.unschedule('job-name');
```

## Cron 表达式参考

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

### 常用示例

| 表达式 | 说明 |
|--------|------|
| `0 2 * * *` | 每天 2:00 AM |
| `*/15 * * * *` | 每 15 分钟 |
| `0 */4 * * *` | 每 4 小时 |
| `0 9 * * 1` | 每周一 9:00 AM |
| `0 0 1 * *` | 每月 1 日午夜 |
| `0 0 * * 0` | 每周日午夜 |

## 时区注意事项

- pg_cron 使用数据库的时区设置（通常是 UTC）
- Supabase Scheduled Functions 使用 UTC
- 建议所有时间都使用 UTC，避免夏令时问题

如果需要使用特定时区：

```sql
-- 查看当前时区
show timezone;

-- 设置时区（不推荐，建议使用 UTC）
alter database postgres set timezone to 'Asia/Shanghai';
```

## 监控和调试

### 1. 查看 Edge Function 日志

```bash
supabase functions logs collect-data
supabase functions logs check-alerts
```

### 2. 查看 pg_cron 执行历史

```sql
select
  jobid,
  job_name,
  status,
  return_message,
  start_time,
  end_time
from cron.job_run_details
where job_name in ('collect-daily-data', 'check-daily-alerts')
order by start_time desc
limit 20;
```

### 3. 测试 Edge Function 调用

```sql
-- Manually trigger the function
select call_edge_function('collect-data', '{"dry_run": true}'::jsonb);
```

## 故障排查

### 问题 1: Edge Function 未被调用

**检查清单:**
- [ ] Edge Function 已部署
- [ ] Service Role Key 正确配置
- [ ] pg_net 扩展已启用
- [ ] 网络连接正常（Supabase 可访问）

**调试:**

```sql
-- Test HTTP call manually
select * from net.http_post(
  url := 'https://xxxxx.supabase.co/functions/v1/collect-data',
  headers := '{"Authorization": "Bearer your-key", "Content-Type": "application/json"}',
  body := '{}'::jsonb
);
```

### 问题 2: Cron 任务未执行

**检查清单:**
- [ ] pg_cron 扩展已启用
- [ ] Cron 表达式正确
- [ ] 任务已调度（`select * from cron.job`）
- [ ] 数据库时区正确

**调试:**

```sql
-- Check cron configuration
select cron.schedule(
  'test-job',
  '*/5 * * * *',  -- Every 5 minutes
  $$select now();$$
);

-- Wait 5 minutes, then check
select * from cron.job_run_details where job_name = 'test-job';

-- Remove test job
select cron.unschedule('test-job');
```

### 问题 3: 权限错误

**解决方案:**

```sql
-- Grant necessary permissions
grant usage on schema cron to postgres;
grant all privileges on all tables in schema cron to postgres;
```

## 最佳实践

1. **使用 Supabase Scheduled Functions** - 除非有特殊需求，否则优先使用官方方案
2. **时区统一** - 所有时间使用 UTC
3. **日志记录** - 在 Edge Functions 中记录详细日志
4. **错误处理** - 实现重试机制和错误通知
5. **监控** - 定期检查任务执行状态
6. **清理** - 定期清理旧的执行记录

## 参考资源

- [Supabase Edge Functions Docs](https://supabase.com/docs/guides/functions)
- [pg_cron Documentation](https://github.com/citusdata/pg_cron)
- [pg_net Documentation](https://github.com/supabase/pg_net)
- [Cron Expression Generator](https://crontab.guru/)
