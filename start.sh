#!/bin/bash

# App数据监控系统启动脚本

echo "🚀 启动App数据监控系统..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "⚠️ 请编辑 .env 文件配置您的环境变量，然后重新运行此脚本"
    echo "🔑 特别注意设置 ENCRYPTION_KEY，可以运行以下命令生成："
    echo "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    exit 1
fi

echo "🐳 启动Docker服务..."
docker-compose up -d

echo "⏳ 等待数据库启动..."
sleep 15

echo "📊 初始化数据库..."
./init_db.sh

echo "👤 创建超级用户 (如果尚未创建)..."
echo "请按提示输入管理员账号信息："
docker-compose exec web python manage.py createsuperuser

echo ""
echo "🎉 系统启动完成！"
echo ""
echo "📋 访问信息："
echo "   管理后台: http://localhost:8000/admin"
echo "   API健康检查: http://localhost:8000/api/health/"
echo ""
echo "🔧 常用命令："
echo "   查看日志: docker-compose logs -f web"
echo "   运行测试任务: docker-compose exec web python manage.py run_daily_task --dry-run"
echo "   测试Webhook: docker-compose exec web python manage.py test_webhook --test-all"
echo "   生成测试数据: docker-compose exec web python manage.py generate_sample_data"
echo "   启动任务调度器: docker-compose exec web python manage.py manage_scheduler start --daemon"
echo "   查看调度状态: docker-compose exec web python manage.py manage_scheduler status"
echo "   手动执行任务: docker-compose exec web python manage.py execute_task --list-schedules"
echo "   停止服务: docker-compose down"
echo ""
echo "📚 详细使用说明请查看 README.md 文件"