# App数据监控与分析平台

一个自动化的App数据监控系统，支持从Apple App Store Connect和Google Play Console自动采集数据，进行智能分析和异常告警，并通过Lark(飞书)发送通知。系统采用集成式任务调度架构，提供完整的Web管理界面和自动化执行能力。

## 🚀 功能特性

### 核心功能
- 🔄 **自动数据采集**: 支持Apple App Store Connect和Google Play Console API
- 📊 **智能数据分析**: 自动计算环比、同比增长率和趋势分析
- ⚠️ **异常检测告警**: 基于阈值规则的实时异常检测
- 📱 **Lark集成**: 丰富的卡片消息格式，支持日报和告警通知
- 🛠️ **管理后台**: 基于Django Admin的友好配置界面，支持任务调度管理
- ⏰ **集成调度器**: 内置任务调度系统，支持定时触发、手动执行、重试机制
- 📈 **执行监控**: 实时查看任务执行状态、历史记录和性能指标
- 🔐 **安全加密**: 敏感凭证加密存储

### 监控指标
- 📱 新增下载量 (日环比、周同比)
- 👥 活跃会话数 (日环比、周同比)  
- 💰 收入数据 (日环比、周同比)
- ⭐ 应用评分变化

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django Admin  │    │  集成任务调度器   │    │   Apple/Google  │
│  - 应用配置管理   │    │  - 定时触发      │    │      APIs      │
│  - 任务调度配置   │    │  - 手动触发      │    │                 │
│  - 执行历史监控   │    │  - 重试机制      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │◄───┤  数据采集分析引擎  ├───►│   Lark 通知     │
│  - 配置存储      │    │  - 数据采集      │    │  - 日报推送     │
│  - 调度配置      │    │  - 智能分析      │    │  - 异常告警     │
│  - 执行历史      │    │  - 异常检测      │    │  - 富文本卡片   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ 技术栈

- **后端**: Django 4.2 + PostgreSQL
- **数据分析**: pandas + 自研分析引擎
- **API集成**: Apple App Store Connect API + Google Play Console API
- **通知**: Lark (飞书) Webhook API
- **部署**: Docker + Docker Compose
- **任务调度**: 集成式Django调度器 + APScheduler (可选)

## 📦 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd app_data_monitor

# 复制环境变量文件
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# Django配置
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库配置
DB_NAME=app_monitor
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# 加密密钥 (用于敏感数据加密)
ENCRYPTION_KEY=your-encryption-key-here
```

### 3. 使用Docker启动

```bash
# 方法1: 使用启动脚本 (推荐)
./start.sh

# 方法2: 手动启动
docker-compose up -d
sleep 15  # 等待数据库启动
./init_db.sh  # 初始化数据库
docker-compose exec web python manage.py createsuperuser
```

### 4. 故障排除

如果遇到数据库相关错误 (如 "relation does not exist")：

```bash
# 运行快速修复脚本
./quick_fix.sh

# 或手动修复
docker-compose down --volumes
docker-compose up -d db
sleep 20
docker-compose up -d web
docker-compose exec web python manage.py migrate
```

### 5. 访问管理后台

访问 http://localhost:8000/admin 使用创建的超级用户账号登录。

## 📝 配置指南

### 1. 添加App

在管理后台 "Apps" 部分添加要监控的应用：
- App名称
- 平台 (iOS/Android)
- Bundle ID / Package Name

### 2. 配置API凭证

#### Apple App Store Connect
1. 在管理后台 "平台凭证" 部分添加iOS凭证
2. 填入以下信息：
   - Issuer ID
   - Key ID  
   - Private Key (完整的私钥内容)

#### Google Play Console
1. 在管理后台 "平台凭证" 部分添加Android凭证
2. 填入以下信息：
   - Service Account Email
   - Service Account Key (JSON格式)

### 3. 设置告警规则

为每个App配置告警规则：
- 选择监控指标 (下载量、会话数、收入等)
- 设置比较类型 (日环比、周同比、绝对值)
- 配置阈值范围
- 设置告警Webhook地址

### 4. 配置日报

为每个App配置日报设置：
- 日报通知Webhook地址
- Lark表格ID (可选，用于数据存储)

### 5. 设置任务调度

在管理后台 "任务调度" 部分配置自动化任务：
- 任务名称和类型 (数据采集、完整分析等)
- 执行频率 (每日、每周、每月)
- 执行时间 (小时、分钟)
- 关联App (可选，不指定则对所有App执行)
- 重试机制和超时设置

## 🔧 管理命令

### 执行数据采集任务

```bash
# 运行完整的每日任务
python manage.py run_daily_task

# 指定特定App
python manage.py run_daily_task --app-id 1

# 指定日期
python manage.py run_daily_task --date 2023-12-01

# 试运行模式
python manage.py run_daily_task --dry-run

# 跳过通知发送
python manage.py run_daily_task --skip-notifications
```

### 测试Webhook连接

```bash
# 测试所有配置的Webhook
python manage.py test_webhook --test-all

# 测试特定App的Webhook
python manage.py test_webhook --app-id 1

# 测试指定URL
python manage.py test_webhook --webhook-url https://your-webhook-url

# 测试API客户端连接
python manage.py test_api_clients --mock-data

# 测试真实API连接
python manage.py test_api_clients --app-id 1
```

### 生成测试数据

```bash
# 生成30天的示例数据
python manage.py generate_sample_data

# 生成包含异常的数据
python manage.py generate_sample_data --with-anomalies

# 为特定App生成数据
python manage.py generate_sample_data --app-id 1 --days 60
```

### 任务调度管理

```bash
# 启动任务调度器 (守护进程模式)
python manage.py manage_scheduler start --daemon

# 停止任务调度器
python manage.py manage_scheduler stop

# 查看调度器状态
python manage.py manage_scheduler status

# 测试调度器逻辑
python manage.py manage_scheduler test

# 测试特定调度
python manage.py manage_scheduler test --test-schedule-id 1
```

### 手动执行任务

```bash
# 查看所有可用的任务调度
python manage.py execute_task --list-schedules

# 查看所有可用的App
python manage.py execute_task --list-apps

# 执行特定的任务调度
python manage.py execute_task --schedule-id 1

# 执行特定App的任务
python manage.py execute_task --app-id 1

# 指定日期执行任务
python manage.py execute_task --app-id 1 --date 2023-12-01

# 跳过通知的执行
python manage.py execute_task --skip-notifications
```

## ⏰ 任务调度设置

### 方法一: 集成调度器 (推荐)

使用内置的任务调度系统，无需配置系统Cron Jobs：

1. **创建任务调度**: 在Django Admin → 任务调度 → 添加任务调度
2. **配置执行时间**: 设置频率、小时、分钟等参数
3. **启动调度器**:
   ```bash
   # 启动调度器 (守护进程模式)
   python manage.py manage_scheduler start --daemon
   
   # 或在Docker环境中
   docker-compose exec web python manage.py manage_scheduler start --daemon
   ```
4. **监控执行**: 在Django Admin → 任务执行记录 中查看执行状态

### 方法二: 传统Cron Jobs (向后兼容)

如需使用传统Cron Jobs，参考 `crontab.example` 文件：

```bash
# 复制示例文件
cp crontab.example /etc/cron.d/app_monitor

# 编辑定时任务
sudo crontab -e

# 添加以下行（调整路径）
0 2 * * * cd /path/to/app_data_monitor && python manage.py run_daily_task

# 启动调度器 (推荐同时使用)
@reboot cd /path/to/app_data_monitor && python manage.py manage_scheduler start --daemon
```

## 📊 API和数据格式

### Lark通知格式

系统会发送两种类型的通知：

#### 1. 日报通知
包含当日数据概览、增长率分析和数据洞察

#### 2. 异常告警
包含异常详情、触发条件和严重程度

### 数据模型

主要数据表：
- `App`: 应用信息
- `Credential`: API凭证 (加密存储)
- `AlertRule`: 告警规则配置
- `DailyReportConfig`: 日报配置
- `DataRecord`: 每日数据记录
- `AlertLog`: 告警日志
- `TaskSchedule`: 任务调度配置
- `TaskExecution`: 任务执行历史记录

## 🔍 故障排除

### 常见问题

1. **API连接失败**
   - 检查凭证配置是否正确
   - 确认API权限设置
   - 查看日志获取详细错误信息

2. **Lark通知发送失败**
   - 验证Webhook URL是否有效
   - 使用 `test_webhook` 命令进行连接测试
   - 检查网络连接

3. **数据异常**
   - 使用 `--dry-run` 模式调试
   - 检查告警规则阈值设置
   - 查看原始API响应数据

4. **任务调度问题**
   - 检查调度器运行状态: `python manage.py manage_scheduler status`
   - 查看任务执行历史记录
   - 检查任务调度配置是否正确
   - 使用手动触发测试: `python manage.py execute_task --schedule-id 1`

### 日志查看

```bash
# 查看应用日志
docker-compose logs -f web

# 查看定时任务日志  
tail -f /var/log/app_monitor/daily_task.log

# 查看调度器状态和执行日志
python manage.py manage_scheduler status

# 在Django Admin中查看详细的任务执行日志
# 访问: http://localhost:8000/admin → 任务执行记录
```

## 🚀 部署到生产环境

### 环境变量配置
- 设置 `DEBUG=False`
- 配置安全的 `SECRET_KEY`
- 使用强密码和加密密钥
- 设置正确的 `ALLOWED_HOSTS`

### 安全建议
- 使用HTTPS
- 定期更新依赖包
- 监控系统资源使用
- 定期备份数据库

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 📞 技术支持

如有问题，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件到项目维护者

---

**注意**: 本项目仅用于内部数据监控，请确保遵守相关API的使用条款和隐私政策。