# App Data Monitor - Web Frontend

Next.js frontend for App Data Monitor, built with NextUI and Tailwind CSS.

## 快速开始

### 1. 安装依赖

```bash
pnpm install
# 或
npm install
# 或
yarn install
```

### 2. 配置环境变量

创建 `.env.local` 文件：

```bash
cp .env.example .env.local
```

编辑 `.env.local` 并填入你的 Supabase 配置：

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 3. 启动开发服务器

```bash
pnpm dev
```

访问 [http://localhost:3000](http://localhost:3000)

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI 组件库**: NextUI (原名 HeroUI)
- **样式**: Tailwind CSS
- **后端**: Supabase
- **图表**: Recharts
- **动画**: Framer Motion

## 注意事项

### NextUI vs HeroUI

NextUI 官网曾使用 heroui.com 域名，但 npm 包名始终是 `@nextui-org/react`：

- ✅ 正确: `import { Button } from '@nextui-org/react'`
- ❌ 错误: `import { Button } from '@heroui/react'`

### 依赖安装问题

如果遇到依赖安装问题，尝试：

```bash
# 清理缓存
rm -rf node_modules .next
rm package-lock.json  # 或 pnpm-lock.yaml

# 重新安装
pnpm install
```

## 项目结构

```
web/
├── app/                    # Next.js App Router 页面
│   ├── layout.tsx         # 根布局
│   ├── providers.tsx      # NextUI Provider
│   ├── page.tsx           # 首页
│   ├── dashboard/         # 仪表板页面
│   ├── apps/              # 应用管理页面
│   ├── credentials/       # 凭证管理页面
│   ├── rules/             # 告警规则页面
│   ├── reports/           # 日报配置页面
│   ├── schedules/         # 任务调度页面
│   └── executions/        # 执行历史页面
├── lib/                   # 工具库
│   └── supabase.ts        # Supabase 客户端
├── public/                # 静态资源
├── tailwind.config.ts     # Tailwind 配置
└── package.json           # 依赖配置
```

## 可用页面

### 核心页面

- **首页** (`/`) - 导航和快速开始
- **仪表板** (`/dashboard`) - 数据概览和统计
- **应用管理** (`/apps`) - 查看和管理应用
- **凭证管理** (`/credentials`) - API 凭证配置
- **告警规则** (`/rules`) - 告警规则配置
- **日报配置** (`/reports`) - Lark 日报设置
- **任务调度** (`/schedules`) - 定时任务管理
- **执行历史** (`/executions`) - 任务执行记录

## 开发指南

### 添加新页面

1. 在 `app/` 目录创建新文件夹
2. 创建 `page.tsx` 文件
3. 使用 NextUI 组件构建 UI
4. 通过 Supabase 客户端获取数据

### NextUI 组件使用

```tsx
import { Button, Card, CardBody } from '@nextui-org/react'

export default function MyPage() {
  return (
    <Card>
      <CardBody>
        <Button color="primary">点击我</Button>
      </CardBody>
    </Card>
  )
}
```

### Supabase 数据获取

```tsx
'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'

export default function DataPage() {
  const [data, setData] = useState([])

  useEffect(() => {
    async function fetchData() {
      const { data, error } = await supabase
        .from('table_name')
        .select('*')

      if (data) setData(data)
    }
    fetchData()
  }, [])

  return <div>{/* 渲染数据 */}</div>
}
```

## 构建生产版本

```bash
# 构建
pnpm build

# 启动生产服务器
pnpm start
```

## 部署

### Vercel (推荐)

1. 连接 GitHub 仓库到 Vercel
2. 配置环境变量
3. 自动部署

### 其他平台

支持任何支持 Next.js 的托管平台：
- Netlify
- Railway
- AWS Amplify
- etc.

## 故障排查

### 模块找不到错误

如果看到 "Can't resolve '@/lib/supabase'"：

1. 确保已安装依赖: `pnpm install`
2. 重启开发服务器
3. 检查 `tsconfig.json` 中的路径别名配置

### 样式不生效

如果 NextUI 样式没有应用：

1. 确认 `tailwind.config.ts` 包含 NextUI 内容路径
2. 确认 `app/providers.tsx` 正确使用 `NextUIProvider`
3. 清理缓存: `rm -rf .next && pnpm dev`

### Supabase 连接错误

1. 检查 `.env.local` 配置
2. 确认 Supabase 项目 URL 和密钥正确
3. 检查网络连接

## 文档链接

- [Next.js 文档](https://nextjs.org/docs)
- [NextUI 文档](https://nextui.org/docs)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [Supabase 文档](https://supabase.com/docs)

## 许可证

MIT
