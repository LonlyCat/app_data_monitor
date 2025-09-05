# 任务调度器使用指南

## 概述

本系统提供了两种运行任务调度器的方式：

1. **后台守护进程模式**（推荐）- 使用 `nohup` 在后台运行
2. **前台运行模式**（调试用）- 占用终端，适合调试

## 后台守护进程模式

### 启动调度器

```bash
./start_scheduler.sh
```

这个命令会：
- 检查Docker容器是否运行
- 检查调度器是否已经在运行
- 使用 `nohup` 在后台启动调度器
- 将日志输出到 `logs/scheduler.log`
- 保存进程ID到 `logs/scheduler.pid`

### 停止调度器

```bash
./stop_scheduler.sh
```

这个命令会：
- 读取PID文件并优雅地停止进程
- 如果进程无响应，强制杀死
- 通过Django命令停止调度器
- 清理PID文件

### 查看状态

```bash
./scheduler_status.sh
```

这个命令会显示：
- 后台进程状态
- 调度器运行状态
- 活跃的调度任务
- 最近执行记录
- 日志文件信息

### 查看实时日志

```bash
tail -f logs/scheduler.log
```

### 查看进程

```bash
ps aux | grep scheduler
```

## 前台运行模式（调试用）

### 启动调度器

```bash
docker compose exec web python manage.py manage_scheduler start --daemon
```

**注意：** 这个命令会占用当前终端，按 `Ctrl+C` 停止。

### 停止调度器

```bash
docker compose exec web python manage.py manage_scheduler stop
```

### 查看状态

```bash
docker compose exec web python manage.py manage_scheduler status
```

## 调度器功能

### 自动任务执行

调度器会：
- 每分钟检查一次是否有需要执行的任务
- 根据配置的Cron表达式自动执行任务
- 记录执行结果到数据库
- 发送通知（如果配置了）

### 支持的Cron表达式

- `* * * * *` - 每分钟执行
- `0 * * * *` - 每小时执行
- `0 2 * * *` - 每天凌晨2点执行
- `0 2 * * 1` - 每周一凌晨2点执行

### 任务类型

1. **每日数据采集** - 从Apple/Google API获取数据
2. **数据分析** - 计算增长率、检测异常
3. **通知发送** - 发送日报和告警通知

## 故障排除

### 调度器无法启动

1. 检查Docker容器是否运行：
   ```bash
   docker compose ps
   ```

2. 检查日志文件：
   ```bash
   cat logs/scheduler.log
   ```

3. 检查进程状态：
   ```bash
   ps aux | grep scheduler
   ```

### 调度器意外停止

1. 检查系统资源：
   ```bash
   top
   ```

2. 检查Docker容器日志：
   ```bash
   docker compose logs web
   ```

3. 重新启动调度器：
   ```bash
   ./stop_scheduler.sh
   ./start_scheduler.sh
   ```

### 任务执行失败

1. 检查任务执行记录：
   ```bash
   docker compose exec web python manage.py manage_scheduler status
   ```

2. 手动测试任务：
   ```bash
   docker compose exec web python manage.py run_daily_task --dry-run
   ```

3. 检查API凭证配置

## 最佳实践

1. **使用后台模式**：生产环境推荐使用 `./start_scheduler.sh`
2. **监控日志**：定期检查 `logs/scheduler.log`
3. **设置告警**：配置系统监控，在调度器停止时发送告警
4. **定期备份**：备份调度配置和任务执行记录
5. **测试调度**：在修改配置前先测试调度逻辑

## 系统集成

### 开机自启动

可以将调度器添加到系统启动脚本：

```bash
# 编辑系统启动脚本
sudo crontab -e

# 添加以下行（调整路径）
@reboot cd /path/to/app_data_monitor && ./start_scheduler.sh
```

### 监控集成

可以集成到监控系统：

```bash
# 检查调度器状态的脚本
#!/bin/bash
if ! ps aux | grep -q "manage_scheduler start --daemon"; then
    echo "调度器已停止，正在重启..."
    cd /path/to/app_data_monitor && ./start_scheduler.sh
fi
```
