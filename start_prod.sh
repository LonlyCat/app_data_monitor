#!/bin/bash

# App数据监控系统 - 生产环境启动脚本

echo "🚀 启动App数据监控系统（生产环境）..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否可用（支持v1和v2）
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建Docker专用的环境变量文件
echo "📝 创建Docker环境变量文件..."
cat > .env.docker << 'EOF'
# Django设置
DEBUG=True
SECRET_KEY=django-insecure-development-key-only
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库设置（PostgreSQL）
DB_ENGINE=django.db.backends.postgresql
DB_HOST=db
DB_NAME=app_monitor
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432

# 加密密钥（用于加密敏感数据）
ENCRYPTION_KEY=KBKkaJaG98akqvu7oSB2O9dBbfLxSqNHUyelJlFrpCc=

# 日志级别
DJANGO_LOG_LEVEL=INFO

# 数据获取延迟天数（等待Apple/Google处理数据的时间）
DATA_FETCH_DELAY_DAYS=2
EOF

echo "🐳 启动Docker服务..."
docker compose down --volumes --remove-orphans
docker compose up -d

echo "⏳ 等待数据库启动..."
sleep 20

echo "📊 初始化数据库..."
docker compose exec web python manage.py migrate

echo "🔧 收集静态文件..."
docker compose exec web python manage.py collectstatic --noinput

echo "👤 创建超级用户 (如果尚未创建)..."
echo "请按提示输入管理员账号信息："
docker compose exec web python manage.py createsuperuser

echo ""
echo "🎉 系统启动完成！"
echo ""
echo "📋 访问信息："
echo "   管理后台: http://localhost:8000/admin"
echo "   API健康检查: http://localhost:8000/api/health/"
echo "   API状态: http://localhost:8000/api/status/"
echo ""
echo "🔧 常用命令："
echo "   查看日志: docker compose logs -f web"
echo "   运行测试任务: docker compose exec web python manage.py run_daily_task --dry-run"
echo "   测试Webhook: docker compose exec web python manage.py test_webhook --test-all"
echo "   生成测试数据: docker compose exec web python manage.py generate_sample_data"
echo "   启动任务调度器: docker compose exec web python manage.py manage_scheduler start --daemon"
echo "   查看调度状态: docker compose exec web python manage.py manage_scheduler status"
echo "   手动执行任务: docker compose exec web python manage.py execute_task --list-schedules"
echo "   停止服务: docker compose down"
echo ""
echo "📚 详细使用说明请查看 README.md 文件"
