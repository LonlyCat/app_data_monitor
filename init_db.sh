#!/bin/bash

# 数据库初始化脚本

echo "🗄️ 初始化数据库..."

# 检查是否在Docker环境中
if [ -f /.dockerenv ]; then
    # 在Docker容器内运行
    PYTHON_CMD="python"
else
    # 在宿主机运行，使用docker-compose
    PYTHON_CMD="docker-compose exec web python"
fi

echo "📊 运行Django内置应用迁移..."
$PYTHON_CMD manage.py migrate auth
$PYTHON_CMD manage.py migrate contenttypes
$PYTHON_CMD manage.py migrate sessions
$PYTHON_CMD manage.py migrate admin
$PYTHON_CMD manage.py migrate messages

echo "📱 运行monitoring应用迁移..."
$PYTHON_CMD manage.py migrate monitoring

echo "🔧 收集静态文件..."
$PYTHON_CMD manage.py collectstatic --noinput

echo "✅ 数据库初始化完成！"
echo ""
echo "📋 接下来的步骤："
echo "1. 创建超级用户: python manage.py createsuperuser"
echo "2. 访问管理后台: http://localhost:8000/admin"
echo "3. 配置App、凭证和告警规则"