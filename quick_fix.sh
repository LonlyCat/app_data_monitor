#!/bin/bash

# 快速修复脚本 - 解决常见的启动问题

echo "🔧 App监控系统快速修复..."

echo "1️⃣ 停止所有容器..."
docker-compose down

echo "2️⃣ 清理旧的容器和网络..."
docker-compose down --volumes --remove-orphans

echo "3️⃣ 重新构建镜像..."
docker-compose build --no-cache

echo "4️⃣ 启动数据库..."
docker-compose up -d db

echo "5️⃣ 等待数据库完全启动..."
sleep 20

echo "6️⃣ 启动Web服务..."
docker-compose up -d web

echo "7️⃣ 等待Web服务启动..."
sleep 10

echo "8️⃣ 运行数据库迁移..."
docker-compose exec web python manage.py migrate

echo "9️⃣ 检查服务状态..."
docker-compose ps

echo ""
echo "✅ 修复完成！"
echo ""
echo "如果还有问题，请检查："
echo "1. .env 文件是否正确配置"
echo "2. Docker是否有足够的内存和磁盘空间"
echo "3. 端口5432和8000是否被其他程序占用"
echo ""
echo "查看详细日志："
echo "docker-compose logs -f web"
echo "docker-compose logs -f db"