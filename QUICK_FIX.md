# 🔧 快速修复指南

## 已修复的问题

### 1. ✅ Module not found 错误
- **问题**: `Can't resolve '@/lib/supabase'`
- **原因**: 包名错误 - 使用了 `@heroui/react` 而不是 `@nextui-org/react`
- **修复**: 已将所有导入更新为正确的包名

### 2. ✅ UI 样式问题
- **问题**: NextUI 组件样式不生效
- **原因**: 包名错误导致 NextUI 无法正确加载
- **修复**: 更新包名和配置

### 3. ✅ Supabase CLI 配置错误
- **问题**: `realtime.ip_version` 和 `edge_functions` 配置错误
- **修复**: 更新 `config.toml` 为最新格式

### 4. ✅ pg_cron 迁移错误
- **问题**: cron job 不存在时 `unschedule` 失败
- **修复**: 注释掉 cron jobs（推荐使用 Supabase Scheduled Functions）

## 🚀 现在需要做的操作

### 步骤 1: 重新安装依赖

```bash
cd web

# 清理旧的依赖
rm -rf node_modules .next
rm -f pnpm-lock.yaml package-lock.json yarn.lock

# 重新安装（选择你使用的包管理器）
pnpm install
# 或
npm install
# 或
yarn install
```

### 步骤 2: 配置环境变量

创建 `.env.local` 文件：

```bash
cd web
cat > .env.local << 'EOF'
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
EOF
```

### 步骤 3: 启动开发服务器

```bash
# 确保在 web 目录
cd web

# 启动
pnpm dev
```

访问: http://localhost:3000

### 步骤 4: 启动 Supabase (如果需要本地测试)

```bash
# 返回项目根目录
cd ..

# 清理并启动
supabase stop
supabase start
```

## 📋 验证清单

- [ ] `cd web && pnpm install` 成功完成
- [ ] `.env.local` 已配置
- [ ] `pnpm dev` 启动成功
- [ ] 访问 http://localhost:3000 看到界面
- [ ] NextUI 组件样式正常显示
- [ ] `supabase start` 成功（如果需要本地测试）

## ❓ 常见问题

### Q: 仍然看到 "@heroui/react" 错误？
A: 确保：
1. 已经 `git pull` 最新代码
2. 删除了 `node_modules` 和 `.next`
3. 重新运行 `pnpm install`

### Q: UI 样式还是很简陋？
A: 检查：
1. 浏览器控制台是否有 CSS 加载错误
2. `tailwind.config.ts` 是否包含 NextUI 路径
3. 尝试清理浏览器缓存

### Q: Supabase 连接失败？
A: 检查：
1. `.env.local` 文件是否存在且配置正确
2. Supabase 项目 URL 和 Key 是否正确
3. 网络连接是否正常

### Q: 想使用 pg_cron 定时任务？
A: 两个选择：
1. **推荐**: 使用 Supabase Scheduled Functions
   ```bash
   supabase functions deploy collect-data --with-schedule "0 2 * * *"
   ```
2. **高级**: 编辑 `supabase/migrations/20250106000000_setup_cron_jobs.sql`
   取消注释相应部分，然后运行 `supabase db reset`

## 📚 相关文档

- **Web 前端**: `web/README.md`
- **API 客户端**: `doc/API_CLIENTS_IMPLEMENTATION.md`
- **项目状态**: `doc/PROJECT_STATUS.md`
- **定时任务**: `doc/PG_CRON_SETUP.md`

## 🎯 下一步

系统现在应该可以正常运行了！你可以：

1. **浏览界面**: 访问所有 6 个核心页面
2. **配置凭证**: 添加 Apple/Google API 凭证
3. **测试数据采集**: 使用 dry-run 模式测试
4. **部署生产**: 部署到 Vercel 或其他平台

## 🆘 需要帮助？

如果仍有问题：
1. 查看浏览器控制台错误信息
2. 查看 Next.js 终端输出
3. 检查 Supabase 日志
4. 参考 `web/README.md` 的故障排查部分
