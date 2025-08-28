#!/bin/bash

# 任务调度器后台启动脚本

echo "🚀 启动任务调度器（后台模式）..."

# 检查Docker是否运行
if ! docker compose ps | grep -q "web.*Up"; then
    echo "❌ Web容器未运行，请先启动Docker服务"
    echo "   运行: ./start_prod.sh 或 docker compose up -d"
    exit 1
fi

# 检查调度器是否已经在运行
if docker compose exec web python manage.py manage_scheduler status | grep -q "🟢 调度器状态: 运行中"; then
    echo "⚠️ 调度器已经在运行中"
    echo "   查看状态: docker compose exec web python manage.py manage_scheduler status"
    echo "   停止调度器: docker compose exec web python manage.py manage_scheduler stop"
    exit 0
fi

# 创建日志目录
mkdir -p logs

# 启动调度器到后台
echo "📝 启动调度器到后台，日志文件: logs/scheduler.log"
nohup docker compose exec -T web python manage.py manage_scheduler start --daemon > logs/scheduler.log 2>&1 &

# 获取进程ID
SCHEDULER_PID=$!
echo $SCHEDULER_PID > logs/scheduler.pid

echo "✅ 调度器已启动到后台 (PID: $SCHEDULER_PID)"
echo ""
echo "📋 常用命令："
echo "   查看状态: docker compose exec web python manage.py manage_scheduler status"
echo "   查看日志: tail -f logs/scheduler.log"
echo "   停止调度器: ./stop_scheduler.sh"
echo "   查看进程: ps aux | grep scheduler"
echo ""
echo "💡 调度器将在后台持续运行，即使关闭终端也不会停止"
