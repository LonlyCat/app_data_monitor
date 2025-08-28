#!/bin/bash

# 查看任务调度器状态脚本

echo "📊 任务调度器状态检查"
echo "="*50

# 检查Docker容器状态
if ! docker compose ps | grep -q "web.*Up"; then
    echo "❌ Web容器未运行"
    exit 1
fi

# 检查进程状态
if [ -f "logs/scheduler.pid" ]; then
    SCHEDULER_PID=$(cat logs/scheduler.pid)
    if ps -p $SCHEDULER_PID > /dev/null 2>&1; then
        echo "🟢 后台进程状态: 运行中 (PID: $SCHEDULER_PID)"
    else
        echo "🔴 后台进程状态: 已停止 (PID: $SCHEDULER_PID)"
    fi
else
    echo "⚠️ 后台进程状态: 未找到PID文件"
fi

echo ""

# 通过Django命令查看详细状态
docker compose exec web python manage.py manage_scheduler status

echo ""
echo "📋 日志信息："
if [ -f "logs/scheduler.log" ]; then
    echo "📝 日志文件: logs/scheduler.log"
    echo "📊 最近日志 (最后10行):"
    echo "---"
    tail -10 logs/scheduler.log
    echo "---"
    echo "💡 实时查看日志: tail -f logs/scheduler.log"
else
    echo "⚠️ 未找到日志文件"
fi

echo ""
echo "🔧 管理命令："
echo "   启动调度器: ./start_scheduler.sh"
echo "   停止调度器: ./stop_scheduler.sh"
echo "   查看状态: ./scheduler_status.sh"
