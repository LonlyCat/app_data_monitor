# App数据监控系统 - 快速启动指南

## 🚀 启动方式

### 方式1：开发环境（推荐用于开发调试）

使用SQLite数据库，无需安装PostgreSQL，适合本地开发和调试：

```bash
# 启动开发环境
./start_dev.sh
```

### 方式2：生产环境（推荐用于生产部署）

使用Docker + PostgreSQL，适合生产环境部署：

```bash
# 启动生产环境
./start_prod.sh
```

## 📋 系统信息

- **管理后台**: http://localhost:8000/admin
- **用户名**: admin
- **密码**: admin123
- **健康检查**: http://localhost:8000/api/health/
- **API状态**: http://localhost:8000/api/status/

## 🔧 常用命令

### 开发环境

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动开发服务器
python manage.py runserver

# 运行测试任务
python manage.py run_daily_task --dry-run

# 测试Webhook
python manage.py test_webhook --test-all

# 生成测试数据
python manage.py generate_sample_data

# 启动任务调度器
python manage.py manage_scheduler start --daemon

# 查看调度状态
python manage.py manage_scheduler status

# 手动执行任务
python manage.py execute_task --list-schedules
```

### 生产环境

```bash
# 查看日志
docker compose logs -f web

# 运行测试任务
docker compose exec web python manage.py run_daily_task --dry-run

# 测试Webhook
docker compose exec web python manage.py test_webhook --test-all

# 生成测试数据
docker compose exec web python manage.py generate_sample_data

# 启动任务调度器
docker compose exec web python manage.py manage_scheduler start --daemon

# 查看调度状态
docker compose exec web python manage.py manage_scheduler status

# 手动执行任务
docker compose exec web python manage.py execute_task --list-schedules

# 停止服务
docker compose down
```

## 🛠️ 故障排除

### Docker网络问题

如果遇到Docker镜像拉取失败，请使用开发环境：

```bash
./start_dev.sh
```

### 数据库连接问题

如果使用PostgreSQL遇到连接问题，可以切换到SQLite：

```bash
# 编辑.env文件，添加以下配置
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

### 权限问题

如果脚本无法执行，请添加执行权限：

```bash
chmod +x start_dev.sh
chmod +x start_prod.sh
chmod +x quick_fix.sh
chmod +x verify_system.sh
```

## 📚 更多信息

- 详细文档：README.md
- 项目架构：doc/project_architecture.md
- API文档：doc/app_store_connect_api_openapi.json
