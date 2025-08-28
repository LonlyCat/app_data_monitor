#!/bin/bash

# App数据监控系统 - 开发环境启动脚本

echo "🚀 启动App数据监控系统（开发环境）..."

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3"
    exit 1
fi

# 检查pip是否安装
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3未安装，请先安装pip3"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "⚠️ 请编辑 .env 文件配置您的环境变量，然后重新运行此脚本"
    echo "🔑 特别注意设置 ENCRYPTION_KEY，可以运行以下命令生成："
    echo "python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    exit 1
fi

# 配置SQLite数据库
echo "🗄️ 配置SQLite数据库..."
sed -i '' 's/DB_ENGINE=django.db.backends.postgresql/DB_ENGINE=django.db.backends.sqlite3/' .env
sed -i '' 's/DB_NAME=app_monitor/DB_NAME=db.sqlite3/' .env
sed -i '' 's/DB_HOST=db/DB_HOST=/' .env
sed -i '' 's/DB_USER=postgres/DB_USER=/' .env
sed -i '' 's/DB_PASSWORD=postgres/DB_PASSWORD=/' .env
sed -i '' 's/DB_PORT=5432/DB_PORT=/' .env

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "🐍 创建Python虚拟环境..."
    python3 -m venv venv
fi

echo "🔧 激活虚拟环境..."
source venv/bin/activate

echo "📦 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📊 运行数据库迁移..."
python manage.py migrate

echo "🔧 收集静态文件..."
python manage.py collectstatic --noinput

echo "👤 创建超级用户 (如果尚未创建)..."
echo "请按提示输入管理员账号信息："
python manage.py createsuperuser

echo ""
echo "🎉 系统启动完成！"
echo ""
echo "📋 访问信息："
echo "   管理后台: http://localhost:8000/admin"
echo "   API健康检查: http://localhost:8000/api/health/"
echo ""
echo "🚀 启动开发服务器："
echo "   python manage.py runserver"
echo ""
echo "🔧 常用命令："
echo "   运行测试任务: python manage.py run_daily_task --dry-run"
echo "   测试Webhook: python manage.py test_webhook --test-all"
echo "   生成测试数据: python manage.py generate_sample_data"
echo "   启动任务调度器: python manage.py manage_scheduler start --daemon"
echo "   查看调度状态: python manage.py manage_scheduler status"
echo "   手动执行任务: python manage.py execute_task --list-schedules"
echo ""
echo "📚 详细使用说明请查看 README.md 文件"
