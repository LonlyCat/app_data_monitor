#!/bin/bash

echo "🔧 修复 Next.js 模块解析问题..."
echo ""

# 停止所有运行的进程
echo "1️⃣ 停止开发服务器..."
pkill -f "next dev" 2>/dev/null || true
sleep 1

# 清理缓存
echo "2️⃣ 清理 Next.js 缓存..."
rm -rf .next

# 清理 TypeScript 缓存
echo "3️⃣ 清理 TypeScript 缓存..."
rm -rf tsconfig.tsbuildinfo

# 清理 node_modules 缓存（如果需要）
if [ "$1" == "--full" ]; then
    echo "4️⃣ 完全重新安装依赖..."
    rm -rf node_modules
    rm -f pnpm-lock.yaml
    pnpm install
else
    echo "4️⃣ 跳过依赖重装（使用 --full 可以完全重装）"
fi

echo ""
echo "✅ 修复完成！现在请运行："
echo "   pnpm dev"
echo ""
