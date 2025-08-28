#!/bin/bash

# 停止任务调度器脚本

echo "🛑 停止任务调度器..."

# 检查PID文件是否存在
if [ -f "logs/scheduler.pid" ]; then
    SCHEDULER_PID=$(cat logs/scheduler.pid)
    
    # 检查进程是否还在运行
    if ps -p $SCHEDULER_PID > /dev/null 2>&1; then
        echo "📝 找到调度器进程 (PID: $SCHEDULER_PID)，正在停止..."
        kill $SCHEDULER_PID
        
        # 等待进程结束
        for i in {1..10}; do
            if ! ps -p $SCHEDULER_PID > /dev/null 2>&1; then
                break
            fi
            echo "⏳ 等待进程结束... ($i/10)"
            sleep 1
        done
        
        # 如果进程还在运行，强制杀死
        if ps -p $SCHEDULER_PID > /dev/null 2>&1; then
            echo "⚠️ 进程未响应，强制停止..."
            kill -9 $SCHEDULER_PID
        fi
        
        echo "✅ 调度器进程已停止"
    else
        echo "⚠️ 调度器进程已不存在 (PID: $SCHEDULER_PID)"
    fi
    
    # 删除PID文件
    rm -f logs/scheduler.pid
else
    echo "⚠️ 未找到调度器PID文件"
fi

# 通过Django命令停止调度器
echo "📝 通过Django命令停止调度器..."
docker compose exec web python manage.py manage_scheduler stop

echo "✅ 调度器已完全停止"
echo ""
echo "💡 如需重新启动，请运行: ./start_scheduler.sh"
