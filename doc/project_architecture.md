# **App 数据监控与分析平台 - 技术架构设计文档**

**版本: 1.0** **关联 PRD 版本: 1.0**

### **1. 系统架构总览**

我们采用**前后端分离**加**集成任务调度**的架构模式。相比传统的外部Cron Jobs调度，新架构将任务调度完全集成到Django管理后台，提供了更好的管理体验和部署简便性。

**架构图:**

+------------------+      +---------------------+      +-----------------+  
|   用户 (管理员)   |----->|   管理后台 (Web UI)   |<---->|   API 服务      |  
+------------------+      | - App配置管理         |      | (Web Server)    |  
                          | - 任务调度管理         |      |                 |  
                          | - 执行历史监控         |      |                 |  
                          +---------------------+      +--------+--------+  
                                    |                           |  
                                    |                  +--------v--------+  
                                    |                  |    数据库 (DB)    |  
                                    |                  | - 配置、凭证、规则   |  
                          +---------v---------+        | - 任务调度配置     |  
                          | 集成任务调度器      |        | - 执行历史记录     |  
                          | (Built-in)       |<------>+-----------------+  
                          | - 定时触发        |  
                          | - 手动触发        |  
                          | - 重试机制        |  
                          +---------+---------+  
                                    |  
                          +---------v---------+        +-----------------+  
                          |   执行模块 (Worker) |------->| Apple/Google API|  
                          | - 数据采集         |        +-----------------+  
                          | - 数据分析与告警     |  
                          | - 通知发送         |  
                          +-------------------+

**数据流说明:**

1. **配置流程**: 管理员通过**管理后台**，调用 **API 服务**的接口，将 App 信息、API 密钥、告警规则、任务调度配置和 Lark Webhook 等信息存入**数据库**。  
2. **调度流程**: **集成任务调度器**根据数据库中的调度配置，在预设时间自动触发**执行模块 (Worker)**，或支持管理员手动触发执行。  
3. **数据处理**: Worker 从数据库读取配置，然后调用 **Apple/Google 的官方 API** 拉取数据，并将执行状态和日志记录到数据库。  
4. **分析与通知**: Worker 对数据进行分析，并根据数据库中的规则判断是否需要告警。最后，通过**通知模块**将报告和告警发送到 Lark。  
5. **监控流程**: 管理员可以通过**管理后台**实时查看任务执行状态、历史记录和性能指标，支持重试失败的任务。

### **2. 技术选型建议**

为了快速开发和易于维护，我们推荐以下技术栈：

| 类别 | 技术选型 | 理由 |
| :---- | :---- | :---- |
| **后端语言/框架** | **Python (Django / Flask)** | Python 在数据处理和脚本自动化方面有天然优势，拥有大量成熟的库。**Django** 自带强大的后台管理系统，可以极大加速管理后台的开发；**Flask** 则更轻量灵活。**推荐初期使用 Django**。 |
| **前端框架** | **（初期）Django Admin / (后期) Vue.js** | V1.0 阶段，直接使用 **Django Admin** 作为管理后台，几乎**零前端代码**即可实现所有配置功能。未来如果需要高度定制化的界面，再引入 **Vue.js**。 |
| **数据库** | **PostgreSQL** | 一款功能强大且开源的关系型数据库。相比 MySQL，它在处理复杂查询和数据类型上更具优势，完全能满足项目现在和未来的需求。 |
| **任务调度** | **Built-in Django Scheduler + APScheduler (可选)** | 采用集成式任务调度系统，通过Django管理后台可视化配置和管理任务调度，支持定时触发、手动触发、重试机制等功能。相比外部Cron Jobs，降低了部署复杂度并提供更好的管理体验。 |
| **依赖库推荐** | - requests: HTTP 请求 - pandas: 数据分析 - cryptography: 敏感信息加密 - apscheduler: (备选) Python 内部任务调度 | 这些库都是 Python 生态中非常成熟和稳定的选择。 |

### **3. 模块设计详述**

#### **3.1 管理后台与 API 服务 (Django App)**

* **模型 (Models)**: 定义数据库表结构，如 App, Credential, AlertRule, TaskSchedule, TaskExecution 等。  
* **后台 (Admin)**: 将上述模型注册到 Django Admin 中，提供完整的管理界面，包括任务调度配置、执行历史监控、手动触发等功能。  
* **接口 (API)**: （可选）如果未来使用独立前端，可以使用 Django REST Framework 快速构建 RESTful API。  
* **核心逻辑**:  
  * **凭证加密**: 在保存到数据库前，必须对 Private Key、Service Account 等敏感信息进行加密处理。  
  * **配置校验**: 对用户输入的 Webhook、告警阈值、调度时间等进行格式校验。  
  * **任务管理**: 提供任务调度的创建、编辑、启用/禁用、手动触发等操作界面。  
  * **执行监控**: 实时显示任务执行状态、历史记录、性能指标和错误日志。

#### **3.2 集成任务调度器 (Task Scheduler)**

新增的核心模块，负责任务的调度和执行管理：

* **任务调度器 (TaskScheduler)**: 
  * 读取数据库中的任务调度配置，按照指定时间自动触发任务
  * 支持每日、每周、每月等多种调度频率
  * 运行在后台线程中，可通过管理命令启动和停止
* **任务执行器 (TaskExecutor)**:
  * 负责实际执行任务，支持定时触发、手动触发、重试执行
  * 记录详细的执行日志和性能指标
  * 提供超时控制和异常处理机制
* **执行历史追踪**:
  * 每次任务执行都创建 TaskExecution 记录
  * 记录执行状态、开始/结束时间、成功/失败数量、错误日志等
  * 支持失败任务的重试机制

#### **3.3 执行模块 (Worker - Django Management Command)**

保持原有的 `run_daily_task` 命令，现在可以通过多种方式触发：

1. **加载配置**: 从数据库中查询所有需要监控的 App 及其配置。  
2. **循环处理**: 遍历每个 App，执行以下操作：  
   * **获取凭证**: 从数据库读取解密后的 API 凭证。  
   * **拉取数据**: 实例化对应平台的 API 客户端，拉取前一天的数据。**做好异常捕获**，防止单个 App 失败导致整个任务中断。  
   * **数据分析**: 使用 pandas 计算环比、同比。  
   * **异常检测**: 与数据库中的告警规则进行比对。  
   * **数据推送**: 将结果格式化，调用通知模块。  
3. **执行记录**: 将执行结果、统计信息、错误日志等记录到 TaskExecution 表中，便于监控和排查问题。

#### **3.4 通知模块 (Notification)**

* 可以封装成一个独立的 Python 类或函数 LarkNotifier。  
* **方法**:  
  * send_daily_report(content): 发送日常报告，使用普通格式。  
  * send_alert(content): 发送告警通知，使用醒目的富文本卡片格式，并可以 @ 指定人员。  
* **健壮性**: 对 Lark API 的请求同样需要做异常处理和重试。

### **4. 数据模型设计 (Database Schema)**

以下是核心表的初步设计：

* **App**  
  * id (主键)  
  * name (字符串, App 名称)  
  * platform (枚举: 'ios', 'android')  
  * bundle_id (字符串, 唯一)  
  * is_active (布尔, 是否启用监控)  
* **Credential**  
  * id (主键)  
  * platform (枚举: 'ios', 'android', 唯一)  
  * config_data (加密的 JSON 字符串, 存储如 issuer_id, key_id, private_key 等)  
* **AlertRule**  
  * id (主键)  
  * app_id (外键关联 App)  
  * metric (字符串, 如 'downloads', 'sessions')  
  * threshold (整数, 如 200, 代表 200%)  
  * lark_webhook_alert (字符串, 告警专用的 Webhook)  
* **DailyReportConfig**  
  * id (主键)  
  * app_id (外键关联 App)  
  * lark_webhook_daily (字符串, 日报 Webhook)  
  * lark_sheet_id (字符串, Lark 表格 ID)
* **TaskSchedule**  
  * id (主键)  
  * name (字符串, 任务名称)  
  * task_type (枚举, 任务类型: data_collection, full_analysis, alert_check)  
  * app_id (外键关联 App, 可为空表示所有App)  
  * frequency (枚举: daily, weekly, monthly)  
  * hour, minute (整数, 执行时间)  
  * weekday, day_of_month (整数, 可选, 用于周/月调度)  
  * is_active (布尔, 是否启用)  
  * skip_notifications, retry_count, timeout_minutes (执行配置参数)
* **TaskExecution**  
  * id (主键)  
  * schedule_id (外键关联 TaskSchedule, 可为空表示手动任务)  
  * trigger_type (枚举: scheduled, manual, retry)  
  * status (枚举: pending, running, success, failed, timeout, cancelled)  
  * app_id (外键关联 App, 可为空)  
  * target_date (日期, 处理的目标日期)  
  * started_at, completed_at (时间戳)  
  * duration_seconds (整数, 执行时长)  
  * success_count, error_count, alerts_generated, notifications_sent (统计信息)  
  * output_log, error_log (文本, 执行日志)  
  * retry_count (整数, 已重试次数)

### **5. 部署与运维建议**

* **部署**: 推荐使用 **Docker** 和 **Docker Compose** 进行容器化部署。这可以一键式地启动 Django 服务、PostgreSQL 数据库、集成任务调度器，并简化环境配置。  
* **配置管理**: 数据库密码、加密密钥等敏感信息，通过**环境变量**注入到容器中，严禁硬编码。  
* **任务调度**: 通过 Django Admin 界面配置任务调度，使用 `python manage.py manage_scheduler start --daemon` 启动调度器，无需配置系统 Cron Jobs。  
* **监控运维**: 
  * 通过 Django Admin 实时查看任务执行状态和历史记录
  * 支持手动触发任务和重试失败的任务
  * 使用 `python manage.py manage_scheduler status` 监控调度器状态
* **日志**: 将所有日志输出到标准输出（stdout），由 Docker 的日志驱动统一收集，任务执行日志同时记录到数据库便于查看。  
* **高可用**: 调度器支持多实例部署时的协调机制，避免重复执行任务。
