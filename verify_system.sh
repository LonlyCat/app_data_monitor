#!/bin/bash

# 系统验证脚本

echo "🔍 验证App数据监控系统..."

# 检查必要文件
echo "1️⃣ 检查关键文件..."
files=(
    "manage.py"
    "requirements.txt"
    "docker-compose.yml"
    "monitoring/models.py"
    "monitoring/migrations/0001_initial.py"
    ".env.example"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file 缺失"
    fi
done

# 检查脚本文件
echo "2️⃣ 检查脚本文件..."
scripts=("start.sh" "init_db.sh" "quick_fix.sh")

for script in "${scripts[@]}"; do
    if [ -f "$script" ] && [ -x "$script" ]; then
        echo "   ✅ $script (可执行)"
    elif [ -f "$script" ]; then
        echo "   ⚠️ $script (不可执行)"
        chmod +x "$script"
        echo "   🔧 已修复 $script 权限"
    else
        echo "   ❌ $script 缺失"
    fi
done

# 检查Django应用结构
echo "3️⃣ 检查Django应用结构..."
django_files=(
    "monitoring/__init__.py"
    "monitoring/models.py"
    "monitoring/admin.py"
    "monitoring/views.py"
    "monitoring/apps.py"
    "monitoring/urls.py"
    "monitoring/management/commands/run_daily_task.py"
    "monitoring/utils/api_clients.py"
    "monitoring/utils/analytics.py"
    "monitoring/utils/anomaly_detector.py"
    "monitoring/utils/lark_notifier.py"
    "monitoring/utils/encryption.py"
)

for file in "${django_files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file 缺失"
    fi
done

# 检查环境文件
echo "4️⃣ 检查环境配置..."
if [ -f ".env" ]; then
    echo "   ✅ .env 文件存在"
    if grep -q "ENCRYPTION_KEY=" .env && [ "$(grep "ENCRYPTION_KEY=" .env | cut -d'=' -f2)" != "your-encryption-key-here" ]; then
        echo "   ✅ ENCRYPTION_KEY 已配置"
    else
        echo "   ⚠️ ENCRYPTION_KEY 需要配置"
        echo "   💡 运行以下命令生成加密密钥："
        echo "      python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    fi
else
    echo "   ⚠️ .env 文件不存在，将从示例文件复制"
    cp .env.example .env
    echo "   📝 请编辑 .env 文件配置环境变量"
fi

# 检查Docker
echo "5️⃣ 检查Docker环境..."
if command -v docker &> /dev/null; then
    echo "   ✅ Docker 已安装"
    if docker ps &> /dev/null; then
        echo "   ✅ Docker 服务运行中"
    else
        echo "   ⚠️ Docker 服务未运行"
    fi
else
    echo "   ❌ Docker 未安装"
fi

if command -v docker-compose &> /dev/null; then
    echo "   ✅ Docker Compose 已安装"
else
    echo "   ❌ Docker Compose 未安装"
fi

# 检查Python依赖
echo "6️⃣ 检查Python依赖..."
if [ -f "requirements.txt" ]; then
    required_packages=("Django" "psycopg2-binary" "pandas" "cryptography" "requests")
    
    for package in "${required_packages[@]}"; do
        if grep -q "$package" requirements.txt; then
            echo "   ✅ $package"
        else
            echo "   ❌ $package 缺失"
        fi
    done
fi

echo ""
echo "🎯 验证总结:"
echo "   如果所有检查都通过 (✅)，系统应该可以正常启动"
echo "   如果有警告 (⚠️) 或错误 (❌)，请根据提示进行修复"
echo ""
echo "🚀 启动命令:"
echo "   ./start.sh    # 完整启动"
echo "   ./quick_fix.sh # 遇到问题时使用"
echo ""
echo "📚 更多信息请查看 README.md"