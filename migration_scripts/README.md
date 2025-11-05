# 数据迁移脚本

从 Django PostgreSQL 数据库迁移到 Supabase。

## 安装依赖

```bash
pip install psycopg2-binary requests python-dotenv
```

## 使用方法

### 1. 准备 Supabase 项目

1. 创建 Supabase 项目
2. 运行数据库迁移：`supabase db push` （在项目根目录）
3. 获取 Supabase URL 和 Service Role Key（在 Supabase Dashboard → Settings → API）

### 2. 获取源数据库连接信息

从 Django 项目的数据库配置中获取 PostgreSQL 连接信息。

### 3. 运行迁移脚本

```bash
python migrate_to_supabase.py \
  --source-db-url "postgresql://user:password@localhost:5432/app_data_monitor" \
  --supabase-url "https://xxxxx.supabase.co" \
  --supabase-key "your-service-role-key"
```

**注意：**
- `--source-db-url`: Django PostgreSQL 数据库连接 URL
- `--supabase-url`: Supabase 项目 URL
- `--supabase-key`: 使用 **Service Role Key**（不是 anon key），因为需要完全访问权限

### 4. 验证迁移结果

迁移完成后，脚本会输出各表的记录数统计。

您可以在 Supabase Dashboard → Table Editor 中查看迁移的数据。

## 迁移内容

脚本会迁移以下数据：

1. ✅ Apps（应用配置）
2. ✅ Credentials（平台凭证，加密数据原样迁移）
3. ✅ Alert Rules（告警规则）
4. ✅ Daily Report Configs（日报配置）
5. ✅ Data Records（数据记录，分批迁移）
6. ✅ Task Schedules（任务调度）
7. ✅ Task Executions（最近 1000 条执行记录）

## 重要提示

1. **凭证加密**：迁移脚本会原样复制加密的凭证数据。确保 Supabase Edge Functions 使用相同的 `ENCRYPTION_KEY`。

2. **数据记录量大**：如果 `data_records` 表数据量很大，迁移可能需要较长时间。脚本使用分批处理（每批 100 条）。

3. **幂等性**：脚本使用 `upsert` 操作，可以多次运行而不会重复插入数据。

4. **备份**：迁移前建议备份源数据库。

## 故障排查

### 连接错误

```
FATAL: password authentication failed
```

检查数据库连接 URL 是否正确。

### Supabase API 错误

```
Failed to insert into XXX: 401 Unauthorized
```

检查是否使用了正确的 Service Role Key（不是 anon key）。

### RLS 策略错误

如果遇到权限错误，确保：
- 使用 Service Role Key（bypass RLS）
- 或者临时禁用 RLS 策略进行迁移
