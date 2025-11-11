# App Data Monitor - Web Frontend

Next.js frontend for App Data Monitor, built with **HeroUI v2.8.5** and Tailwind CSS.

## 🎯 技术栈

- **框架**: Next.js 14 (App Router)
- **UI 组件库**: HeroUI v2.8.5 (https://www.heroui.com)
- **样式**: Tailwind CSS
- **后端**: Supabase
- **图表**: Recharts
- **动画**: Framer Motion

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 pnpm (推荐)
pnpm install

# 或使用 npm
npm install

# 或使用 yarn
yarn install
```

### 2. 配置环境变量

复制示例文件并填入你的配置：

```bash
cp .env.local.example .env.local
```

编辑 `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 3. 启动开发服务器

```bash
pnpm dev
```

访问 [http://localhost:3000](http://localhost:3000)

## 📁 项目结构

```
web/
├── app/                    # Next.js App Router 页面
│   ├── layout.tsx         # 根布局
│   ├── providers.tsx      # HeroUI Provider
│   ├── page.tsx           # 首页
│   ├── dashboard/         # 仪表板
│   ├── apps/              # 应用管理
│   ├── credentials/       # 凭证管理
│   ├── rules/             # 告警规则
│   ├── reports/           # 日报配置
│   ├── schedules/         # 任务调度
│   └── executions/        # 执行历史
├── lib/
│   └── supabase.ts        # Supabase 客户端
└── tailwind.config.ts     # Tailwind + HeroUI 配置
```

## 🔧 关于 HeroUI

### 正确的包名

- ✅ **正确**: `@heroui/react` (npm 包名)
- ✅ **官网**: https://www.heroui.com
- ✅ **文档**: https://www.heroui.com/docs
- ✅ **版本**: v2.8.5

### 使用示例

```tsx
import { Button, Card, CardBody } from '@heroui/react'

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

## ❓ 故障排查

### 问题 1: Module not found '@/lib/supabase'

**原因**: 依赖未安装

**解决方案**:
```bash
cd web
rm -rf node_modules .next
pnpm install
pnpm dev
```

### 问题 2: UI 样式简陋

**原因**: 
1. 依赖未正确安装
2. 开发服务器需要重启
3. 浏览器缓存

**解决方案**:
```bash
# 1. 清理并重新安装
rm -rf node_modules .next
pnpm install

# 2. 重启开发服务器
pnpm dev

# 3. 清除浏览器缓存 (Ctrl+Shift+R 或 Cmd+Shift+R)
```

### 问题 3: Supabase 连接失败

**检查清单**:
- [ ] `.env.local` 文件是否存在
- [ ] Supabase URL 和 Key 是否正确
- [ ] Supabase 项目是否已启动

## 📦 构建生产版本

```bash
# 构建
pnpm build

# 启动生产服务器
pnpm start
```

## 🌐 部署

### Vercel (推荐)

1. 连接 GitHub 仓库
2. 配置环境变量
3. 自动部署

### 其他平台

支持任何 Next.js 托管平台：
- Netlify
- Railway
- AWS Amplify

## 📚 相关文档

- [HeroUI 官方文档](https://www.heroui.com/docs)
- [Next.js 文档](https://nextjs.org/docs)
- [Tailwind CSS 文档](https://tailwindcss.com/docs)
- [Supabase 文档](https://supabase.com/docs)

## 📝 开发笔记

### 路径别名

项目使用 `@/` 作为路径别名:

```tsx
import { supabase } from '@/lib/supabase'  // 指向 web/lib/supabase.ts
```

配置在 `tsconfig.json`:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### HeroUI Provider

必须在根布局包裹 `HeroUIProvider`:

```tsx
// app/providers.tsx
import { HeroUIProvider } from '@heroui/react'

export function Providers({ children }) {
  return (
    <HeroUIProvider>
      {children}
    </HeroUIProvider>
  )
}
```

## 🐛 已知问题

### TypeScript 路径别名不工作

**解决方案**: 重启 VS Code / IDE

```bash
# VS Code 命令面板 (Cmd/Ctrl + Shift + P)
> TypeScript: Restart TS Server
```

## 📄 许可证

MIT
