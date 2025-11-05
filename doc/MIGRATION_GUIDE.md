# Supabase + Next.js + HeroUI 迁移指南

本文档指导如何将现有的 Django 应用迁移到 Supabase（后端）+ Next.js（前端）+ HeroUI 的架构。

## 📋 目录

1. [迁移概览](#迁移概览)
2. [前置准备](#前置准备)
3. [阶段 A: Supabase 基础设施](#阶段-a-supabase-基础设施)
4. [阶段 B: Edge Functions 部署](#阶段-b-edge-functions-部署)
5. [阶段 C: Next.js 前端部署](#阶段-c-nextjs-前端部署)
6. [阶段 D: 数据迁移](#阶段-d-数据迁移)
7. [阶段 E: 验证与切换](#阶段-e-验证与切换)
8. [后续开发任务](#后续开发任务)

## 迁移概览

### 现状（Django）
- **后端**: Django 4.2 + PostgreSQL
- **管理界面**: Django Admin
- **任务调度**: 内置 Django Scheduler + APScheduler
- **部署**: Docker + Docker Compose

### 目标（Supabase + Next.js）
- **后端**: Supabase（Postgres + Auth + Edge Functions + pg_cron）
- **前端**: Next.js 14（App Router + HeroUI + Tailwind）
- **任务调度**: Supabase Scheduled Functions / pg_cron
- **部署**: Vercel（前端） + Supabase（后端）

### 架构对比

| 组件 | Django 架构 | Supabase 架构 |
|------|------------|---------------|
| 数据库 | PostgreSQL 15 | Supabase Postgres |
| API 层 | Django REST Framework | Supabase REST API + Edge Functions |
| 管理后台 | Django Admin | Next.js + HeroUI |
| 认证授权 | Django Auth | Supabase Auth + RLS |
| 任务调度 | Django Scheduler | pg_cron / Scheduled Functions |
| 文件存储 | 本地文件系统 | Supabase Storage |
| 部署方式 | Docker Compose | Vercel + Supabase Cloud |

## 前置准备

### 1. 工具安装

```bash
# Supabase CLI
npm install -g supabase

# Deno (用于本地测试 Edge Functions)
curl -fsSL https://deno.land/x/install/install.sh | sh

# Node.js 和 pnpm (用于 Next.js)
npm install -g pnpm
```

### 2. 创建 Supabase 项目

1. 访问 [https://supabase.com](https://supabase.com)
2. 创建新项目
3. 记录以下信息：
   - Project URL: `https://xxxxx.supabase.co`
   - Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6...`
   - Service Role Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6...`

### 3. 环境变量准备

创建 `.env` 文件：

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Edge Functions Secrets
ENCRYPTION_KEY=your-base64-encryption-key

# Source Database (for migration)
SOURCE_DB_URL=postgresql://user:pass@host:5432/app_data_monitor
```

## 阶段 A: Supabase 基础设施

### 1. 初始化 Supabase 项目

```bash
cd /home/user/app_data_monitor

# 关联到远程 Supabase 项目
supabase link --project-ref your-project-ref

# 或者初始化本地开发环境
supabase init
supabase start
```

### 2. 运行数据库迁移

```bash
# 应用数据库迁移（创建所有表）
supabase db push

# 验证迁移
supabase db diff
```

迁移文件位置：`supabase/migrations/20250105000000_initial_schema.sql`

### 3. 配置 Supabase Secrets

在 Supabase Dashboard → Settings → Vault 中添加密钥：

```
ENCRYPTION_KEY=<your-base64-encryption-key>
```

生成加密密钥（Python）：

```python
import base64
import os
key = base64.b64encode(os.urandom(32)).decode('utf-8')
print(key)
```

### 4. 启用 pg_cron 扩展

在 Supabase Dashboard → Database → Extensions 中启用 `pg_cron`。

## 阶段 B: Edge Functions 部署

### 1. 部署 Edge Functions

```bash
# 部署所有函数
supabase functions deploy collect-data
supabase functions deploy check-alerts

# 或一次性部署所有
supabase functions deploy
```

### 2. 配置 Edge Functions Secrets

```bash
# 设置加密密钥
supabase secrets set ENCRYPTION_KEY=your-base64-key

# 验证
supabase secrets list
```

### 3. 测试 Edge Functions

```bash
# 测试 collect-data
curl -X POST \
  'https://xxxxx.supabase.co/functions/v1/collect-data' \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 测试 check-alerts
curl -X POST \
  'https://xxxxx.supabase.co/functions/v1/check-alerts' \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"skip_notifications": true}'
```

### 4. 配置任务调度

#### 方案 1: 使用 pg_cron（推荐）

在 Supabase SQL Editor 中执行：

```sql
-- 每日 2:00 AM 执行数据采集
SELECT cron.schedule(
  'collect-daily-data',
  '0 2 * * *',
  $$
  SELECT net.http_post(
    url := 'https://xxxxx.supabase.co/functions/v1/collect-data',
    headers := '{"Authorization": "Bearer ' || current_setting('app.settings.service_role_key') || '"}',
    body := '{}'::jsonb
  );
  $$
);

-- 每日 3:00 AM 执行告警检查
SELECT cron.schedule(
  'check-daily-alerts',
  '0 3 * * *',
  $$
  SELECT net.http_post(
    url := 'https://xxxxx.supabase.co/functions/v1/check-alerts',
    headers := '{"Authorization": "Bearer ' || current_setting('app.settings.service_role_key') || '"}',
    body := '{}'::jsonb
  );
  $$
);

-- 查看已配置的任务
SELECT * FROM cron.job;
```

#### 方案 2: 使用 Supabase Scheduled Functions

参考 [Supabase Scheduled Functions 文档](https://supabase.com/docs/guides/functions/schedule-functions)。

## 阶段 C: Next.js 前端部署

### 1. 安装依赖

```bash
cd web
pnpm install
```

### 2. 配置环境变量

创建 `web/.env.local`：

```bash
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 3. 本地开发

```bash
pnpm dev
```

访问 [http://localhost:3000](http://localhost:3000)

### 4. 构建和部署

#### 部署到 Vercel（推荐）

```bash
# 安装 Vercel CLI
npm install -g vercel

# 部署
cd web
vercel
```

在 Vercel Dashboard 中配置环境变量：
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

#### 部署到其他平台

```bash
# 构建
pnpm build

# 启动生产服务器
pnpm start
```

## 阶段 D: 数据迁移

### 1. 准备迁移脚本

```bash
cd migration_scripts

# 安装依赖
pip install psycopg2-binary requests python-dotenv
```

### 2. 运行迁移

```bash
python migrate_to_supabase.py \
  --source-db-url "postgresql://user:password@localhost:5432/app_data_monitor" \
  --supabase-url "https://xxxxx.supabase.co" \
  --supabase-key "your-service-role-key"
```

**注意事项：**
- 使用 Service Role Key（不是 anon key）
- 迁移可能需要较长时间（取决于数据量）
- 凭证数据会原样迁移（已加密），确保 Edge Functions 使用相同的 ENCRYPTION_KEY

### 3. 验证迁移数据

在 Supabase Dashboard → Table Editor 中检查：

- ✅ Apps 表
- ✅ Credentials 表（加密数据）
- ✅ Alert Rules 表
- ✅ Daily Report Configs 表
- ✅ Data Records 表（可能数据量很大）
- ✅ Task Schedules 表
- ✅ Task Executions 表

## 阶段 E: 验证与切换

### 1. 功能验证清单

- [ ] 数据采集：手动触发 `collect-data` 函数，验证数据写入
- [ ] 告警检查：手动触发 `check-alerts` 函数，验证告警生成和 Lark 通知
- [ ] 前端访问：访问 Next.js 应用，验证数据展示
- [ ] 任务调度：验证 pg_cron 定时任务正常触发
- [ ] 权限控制：验证 RLS 策略和认证流程

### 2. 性能对比

- Django 响应时间 vs Supabase Edge Functions 响应时间
- 数据库查询性能
- 前端加载速度

### 3. 切换流程

1. **并行运行期**（推荐 1-2 周）
   - Django 和 Supabase 同时运行
   - 对比数据一致性
   - 发现和修复问题

2. **灰度切换**
   - 部分用户使用 Next.js 前端
   - 收集反馈

3. **完全切换**
   - 停止 Django 任务调度
   - 将所有用户切换到 Next.js 前端
   - 保留 Django 备份一段时间

4. **下线 Django**
   - 停止 Django 容器
   - 归档数据库备份

## 后续开发任务

### 高优先级

1. **完善 Edge Functions API 客户端**
   - [ ] 实现完整的 Apple App Store Connect API 客户端（JWT ES256）
   - [ ] 实现完整的 Google Play Console API 客户端（OAuth2）
   - [ ] 添加 API 请求重试和错误处理

2. **完善前端页面**
   - [ ] Dashboard：数据可视化（图表、趋势）
   - [ ] Credentials：凭证管理（加密展示、编辑）
   - [ ] Rules：告警规则 CRUD
   - [ ] Reports：日报配置管理
   - [ ] Schedules：任务调度管理
   - [ ] Executions：执行记录查看

3. **认证与授权**
   - [ ] 集成 Supabase Auth
   - [ ] 实现用户登录/注册
   - [ ] 配置 RLS 策略（按组织/项目隔离）

### 中优先级

4. **数据分析增强**
   - [ ] 趋势分析和洞察生成
   - [ ] 来源分布分析
   - [ ] 自定义报表

5. **通知增强**
   - [ ] 多渠道通知（Email、SMS、Webhook）
   - [ ] 告警升级和静默规则

6. **运维工具**
   - [ ] 健康检查接口
   - [ ] 日志聚合和查询
   - [ ] 性能监控

### 低优先级

7. **功能扩展**
   - [ ] 多应用对比分析
   - [ ] 数据导出（CSV、Excel）
   - [ ] API 文档和 SDK

## 常见问题

### Q: 迁移后如何回滚？

A: 保留 Django 系统运行 1-2 周作为备份，数据库定期备份。

### Q: 加密密钥如何管理？

A: 使用 Supabase Secrets 管理，不要提交到代码仓库。

### Q: Edge Functions 如何调试？

A: 使用 `supabase functions serve` 本地运行，查看日志。

### Q: RLS 策略如何配置？

A: 参考 `supabase/migrations/20250105000000_initial_schema.sql` 中的策略示例。

### Q: 如何处理大量历史数据？

A: 使用批量迁移，或者只迁移最近 N 个月的数据。

## 参考资源

- [Supabase 官方文档](https://supabase.com/docs)
- [Next.js 官方文档](https://nextjs.org/docs)
- [HeroUI 官方文档](https://www.heroui.com/)
- [pg_cron 文档](https://github.com/citusdata/pg_cron)

## 技术支持

迁移过程中遇到问题，可以：
1. 查看 Supabase Dashboard 日志
2. 查看 Edge Functions 日志：`supabase functions logs <function-name>`
3. 查看数据库日志：Supabase Dashboard → Logs
