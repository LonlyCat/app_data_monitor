# App数据监控与分析平台

一个自动化的App数据监控系统，支持从Apple App Store Connect和Google Play Console自动采集数据，进行智能分析和异常告警，并通过Lark(飞书)发送通知。系统采用Supabase + Next.js架构，提供现代化的Web界面和自动化执行能力。

## 🚀 功能特性

### 核心功能
- 🔄 **自动数据采集**: 支持Apple App Store Connect和Google Play Console API
- 📊 **智能数据分析**: 自动计算环比、同比增长率和趋势分析
- ⚠️ **异常检测告警**: 基于阈值规则的实时异常检测
- 📱 **Lark集成**: 丰富的卡片消息格式，支持日报和告警通知
- 🛠️ **现代化界面**: 基于Next.js 14和HeroUI的响应式Web界面
- ⏰ **自动调度**: Supabase Edge Functions和Scheduled Functions实现定时任务
- 🔐 **安全性**: Row Level Security (RLS) 和安全的API密钥管理

### 监控指标
- 📱 新增下载量 (日环比、周同比)
- 👥 活跃会话数 (日环比、周同比)
- 💰 收入数据 (日环比、周同比)
- ⭐ 应用评分变化

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js Web   │    │     Supabase    │    │   Apple/Google  │
│   - 数据展示     │◄───┤  - PostgreSQL   │◄───┤      APIs      │
│   - 配置管理     │    │  - Edge Funcs   │    │                 │
│   - HeroUI      │    │  - Scheduled    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Lark 通知     │
                       │  - 日报推送     │
                       │  - 异常告警     │
                       │  - 富文本卡片   │
                       └─────────────────┘
```

## 🛠️ 技术栈

- **前端**: Next.js 14 (App Router) + React 18 + TypeScript
- **UI框架**: HeroUI 2.7.11 + Tailwind CSS 3.x
- **后端**: Supabase (PostgreSQL + Edge Functions + Scheduled Functions)
- **数据分析**: Edge Functions (Deno/TypeScript)
- **API集成**: Apple App Store Connect API + Google Play Console API
- **通知**: Lark (飞书) Webhook API
- **包管理**: pnpm

## 📦 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd app_data_monitor

# 安装Supabase CLI
brew install supabase/tap/supabase  # macOS
# 或参考: https://supabase.com/docs/guides/cli/getting-started

# 安装pnpm
npm install -g pnpm
```

### 2. 启动Supabase本地开发环境

```bash
# 启动Supabase本地服务
supabase start

# 获取API密钥（首次启动后会显示）
# NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
# NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...
```

### 3. 配置Next.js环境变量

```bash
# 进入web目录
cd web

# 复制环境变量示例文件
cp .env.local.example .env.local

# 编辑.env.local，填入Supabase提供的URL和密钥
```

`.env.local` 文件内容：
```bash
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 4. 安装依赖并启动Web应用

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

访问 http://localhost:3000 查看应用。

## 📝 数据库结构

主要数据表（位于 `supabase/migrations/`）：

- `apps`: 应用信息
- `credentials`: API凭证（加密存储）
- `alert_rules`: 告警规则配置
- `daily_report_configs`: 日报配置
- `data_records`: 每日数据记录
- `alert_logs`: 告警日志
- `task_schedules`: 任务调度配置
- `task_executions`: 任务执行历史

## 🔧 Supabase Edge Functions

Edge Functions位于 `supabase/functions/`：

- `collect-daily-data`: 数据采集主函数
- `apple-api-client`: Apple App Store Connect API集成
- `google-api-client`: Google Play Console API集成
- `send-lark-notification`: Lark通知发送

### 部署Edge Functions

```bash
# 部署所有函数
supabase functions deploy

# 部署特定函数
supabase functions deploy collect-daily-data

# 查看函数日志
supabase functions logs collect-daily-data
```

## ⏰ 任务调度

使用Supabase Scheduled Functions（基于pg_cron）：

```sql
-- 每天早上2点执行数据采集
SELECT cron.schedule(
  'collect-daily-data',
  '0 2 * * *',
  $$
  SELECT net.http_post(
    url := 'https://your-project.supabase.co/functions/v1/collect-daily-data',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
  );
  $$
);
```

参考 `supabase/migrations/` 中的迁移文件进行配置。

## 🔍 开发指南

### Web应用开发

```bash
cd web

# 开发模式
pnpm dev

# 构建生产版本
pnpm build

# 启动生产服务器
pnpm start

# 代码检查
pnpm lint
```

### Supabase本地开发

```bash
# 查看Supabase状态
supabase status

# 停止Supabase服务
supabase stop

# 重置数据库
supabase db reset

# 创建新迁移
supabase migration new migration_name

# 应用迁移
supabase db push
```

### 测试Edge Functions

```bash
# 本地调用函数
supabase functions serve

# 使用curl测试
curl -i --location --request POST \
  'http://127.0.0.1:54321/functions/v1/collect-daily-data' \
  --header 'Authorization: Bearer YOUR_ANON_KEY' \
  --header 'Content-Type: application/json' \
  --data '{"date": "2025-11-15"}'
```

## 🚀 生产部署

### 1. 部署到Supabase

```bash
# 登录Supabase CLI
supabase login

# 关联到你的Supabase项目
supabase link --project-ref your-project-ref

# 推送数据库迁移
supabase db push

# 部署Edge Functions
supabase functions deploy
```

### 2. 部署Next.js应用

推荐使用Vercel部署Next.js应用：

```bash
cd web

# 安装Vercel CLI
npm i -g vercel

# 部署
vercel

# 生产部署
vercel --prod
```

或使用其他平台（Netlify、Railway等）。

### 3. 配置环境变量

在部署平台设置以下环境变量：
- `NEXT_PUBLIC_SUPABASE_URL`: 你的Supabase项目URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase匿名密钥

## 🔐 安全配置

### Row Level Security (RLS)

数据库已启用RLS策略，确保数据安全。参考 `supabase/migrations/` 中的RLS配置。

### API密钥管理

- 凭证信息加密存储在数据库中
- 使用Supabase的安全存储功能
- 生产环境请使用强加密密钥

## 📊 HeroUI配置要点

根据本项目的配置经验，正确使用HeroUI需要：

1. **安装依赖**：
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

2. **Tailwind配置** (`tailwind.config.ts`)：
   ```typescript
   import { heroui } from '@heroui/theme' // 从 @heroui/theme 导入，而非 @heroui/react!

   export default {
     plugins: [heroui({ /* theme config */ })]
   }
   ```

3. **主题配置**：确保在layout中使用 `className="dark"` 和主题工具类 `bg-background text-foreground`

详见 `web/tailwind.config.ts` 和 `web/app/layout.tsx`。

## 📄 文档

- [项目架构文档](doc/project_architecture.md) - 系统架构和设计模式（待更新）

## 🔍 故障排除

### Supabase CLI问题

如遇到配置验证错误，检查 `supabase/config.toml`：
- `ip_version` 必须是 "IPv4" 或 "IPv6"（大小写敏感）
- 移除已弃用的 `port` 和 `edge_functions` 配置

### 模块解析错误

如遇到 `Module not found: '@/lib/supabase'`：
1. 确认 `web/lib/` 目录未被 `.gitignore` 忽略
2. 清除Next.js缓存：`rm -rf web/.next`
3. 重新安装依赖：`pnpm install`

### HeroUI样式不生效

确保：
1. 从 `@heroui/theme` 导入 `heroui` 插件（不是从 `@heroui/react`）
2. `@heroui/theme` 已安装在 `devDependencies`
3. Tailwind content配置包含 HeroUI 主题路径

## 📄 许可证

本项目采用 MIT 许可证。

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

---

**注意**: 本项目仅用于内部数据监控，请确保遵守相关API的使用条款和隐私政策。
