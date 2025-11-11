# Module Resolution 修复指南

## 🐛 问题描述

```
Module not found: Can't resolve '@/lib/supabase'
```

## ✅ 验证：文件确实存在

```bash
ls -la lib/supabase.ts
# ✅ 文件存在

cat tsconfig.json | grep "@/\*"
# ✅ 路径别名配置正确: "@/*": ["./*"]
```

**结论：这是 Next.js/TypeScript 缓存问题，不是文件缺失！**

---

## 🚀 快速修复（推荐）

### 方法 1: 使用修复脚本（最简单）

```bash
# 在 web 目录执行
./fix-module-resolution.sh

# 然后重启开发服务器
pnpm dev
```

### 方法 2: 手动清理（如果脚本不工作）

```bash
# 1. 停止开发服务器
# 按 Ctrl+C 或在另一个终端：
pkill -f "next dev"

# 2. 清理 Next.js 缓存
rm -rf .next

# 3. 清理 TypeScript 缓存
rm -rf tsconfig.tsbuildinfo

# 4. 重启开发服务器
pnpm dev
```

---

## 🔍 深度修复（如果上述方法无效）

### 步骤 1: 完全清理

```bash
# 停止所有进程
pkill -f "next dev"

# 清理所有缓存
rm -rf .next
rm -rf node_modules/.cache
rm -rf tsconfig.tsbuildinfo

# 清理依赖（可选，但推荐）
rm -rf node_modules
rm -f pnpm-lock.yaml
```

### 步骤 2: 重新安装

```bash
pnpm install
```

### 步骤 3: 验证配置

检查 `tsconfig.json` 的路径配置：

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### 步骤 4: 重启开发服务器

```bash
pnpm dev
```

---

## 🔧 如果 VS Code 报错

如果 VS Code 中仍然显示红色波浪线：

### 1. 重启 TypeScript 服务器

- 打开命令面板：`Cmd/Ctrl + Shift + P`
- 输入：`TypeScript: Restart TS Server`
- 回车

### 2. 重新加载 VS Code 窗口

- 命令面板：`Cmd/Ctrl + Shift + P`
- 输入：`Reload Window`
- 回车

### 3. 完全重启 VS Code

```bash
# 关闭 VS Code
# 然后重新打开项目
code .
```

---

## 💡 为什么会出现这个问题？

### 可能的原因：

1. **Next.js 缓存**
   - `.next` 目录缓存了旧的模块解析结果
   - 更新依赖后缓存未刷新

2. **TypeScript 缓存**
   - `tsconfig.tsbuildinfo` 缓存了类型信息
   - 路径别名变更后未更新

3. **pnpm 符号链接**
   - pnpm 使用符号链接管理依赖
   - 某些情况下可能导致路径解析问题

4. **开发服务器未重启**
   - 修改配置文件后需要重启开发服务器

---

## ✅ 验证修复成功

修复后，你应该看到：

1. **终端输出**
   ```
   ✓ Ready in 2.5s
   ○ Compiling / ...
   ✓ Compiled successfully
   ```

2. **浏览器**
   - 页面正常加载
   - 没有控制台错误
   - HeroUI 样式正常显示

3. **VS Code**
   - 没有红色波浪线
   - 自动补全工作正常
   - 类型检查正常

---

## 🆘 仍然无法解决？

### 检查清单：

- [ ] 确认 `lib/supabase.ts` 文件存在
- [ ] 确认 `tsconfig.json` 有 `"@/*": ["./*"]` 配置
- [ ] 已清理 `.next` 目录
- [ ] 已清理 `tsconfig.tsbuildinfo`
- [ ] 已重启开发服务器
- [ ] 已重启 VS Code TypeScript 服务器

### 终极解决方案：

```bash
# 完全重置项目
cd web

# 1. 停止所有进程
pkill -f "next dev"

# 2. 删除所有缓存和依赖
rm -rf .next node_modules tsconfig.tsbuildinfo pnpm-lock.yaml

# 3. 重新安装
pnpm install

# 4. 启动
pnpm dev
```

---

## 📝 预防措施

### 以后遇到类似问题时：

1. **修改 tsconfig.json 后**
   ```bash
   rm -rf .next
   pnpm dev
   ```

2. **安装/更新依赖后**
   ```bash
   rm -rf .next
   pnpm dev
   ```

3. **VS Code 类型检查异常时**
   - 重启 TypeScript 服务器（命令面板）
   - 或重启 VS Code

---

## 🎯 快速参考

| 问题 | 解决方案 |
|------|---------|
| Module not found | `rm -rf .next && pnpm dev` |
| VS Code 报错 | 重启 TS Server |
| 类型检查失败 | `rm tsconfig.tsbuildinfo` |
| 完全无法启动 | `rm -rf node_modules && pnpm install` |

---

## ✨ 相关文件位置

```
web/
├── lib/
│   └── supabase.ts          ✅ Supabase 客户端（存在）
├── tsconfig.json            ✅ 路径别名配置（正确）
├── next.config.js           ✅ Next.js 配置（正常）
└── .next/                   ⚠️ 缓存目录（需要清理）
```

---

**记住：90% 的模块解析问题都可以通过清理缓存解决！**

```bash
rm -rf .next && pnpm dev
```
