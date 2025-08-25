import logging
import traceback
from datetime import datetime, timedelta
from io import StringIO
import sys
import threading
import signal
from django.utils import timezone
from django.core.management import call_command
from django.core.management.base import CommandError

from ..models import TaskSchedule, TaskExecution, App

logger = logging.getLogger(__name__)


class TaskExecutor:
    """任务执行器 - 负责执行调度任务和手动任务"""
    
    def __init__(self):
        self.current_execution = None
        self.should_stop = False
        
    def execute_schedule_auto(self, schedule: TaskSchedule, target_date=None):
        """自动执行调度任务（由调度器调用）"""
        return self._execute_schedule(
            schedule, 
            trigger_type='scheduled',
            target_date=target_date
        )
    
    def execute_schedule_manual(self, schedule: TaskSchedule, target_date=None):
        """手动执行调度任务（由管理后台调用）"""
        return self._execute_schedule(
            schedule,
            trigger_type='manual', 
            target_date=target_date
        )
    
    def execute_manual_task(self, app_id=None, target_date=None, skip_notifications=False):
        """执行手动任务（不基于调度配置）"""
        execution = TaskExecution.objects.create(
            schedule=None,
            trigger_type='manual',
            status='pending',
            app_id=app_id,
            target_date=target_date
        )
        
        return self._execute_task(
            execution=execution,
            app_id=app_id,
            target_date=target_date,
            skip_notifications=skip_notifications
        )
    
    def retry_execution(self, execution: TaskExecution):
        """重试失败的执行"""
        if not execution.can_retry():
            logger.warning(f"执行 {execution.id} 不能重试")
            return False
            
        # 创建新的重试执行记录
        retry_execution = TaskExecution.objects.create(
            schedule=execution.schedule,
            trigger_type='retry',
            status='pending',
            app=execution.app,
            target_date=execution.target_date,
            retry_count=execution.retry_count + 1
        )
        
        # 确定执行参数
        app_id = execution.app.id if execution.app else None
        skip_notifications = execution.schedule.skip_notifications if execution.schedule else False
        
        return self._execute_task(
            execution=retry_execution,
            app_id=app_id,
            target_date=execution.target_date,
            skip_notifications=skip_notifications
        )
    
    def _execute_schedule(self, schedule: TaskSchedule, trigger_type='scheduled', target_date=None):
        """执行调度任务的内部方法"""
        if not schedule.is_active:
            logger.info(f"跳过已禁用的任务调度: {schedule.name}")
            return False
        
        # 检查是否已有正在运行的任务
        running_execution = TaskExecution.objects.filter(
            schedule=schedule,
            status='running'
        ).first()
        
        if running_execution:
            logger.warning(f"任务调度 {schedule.name} 已有执行中的任务，跳过此次执行")
            return False
        
        # 创建执行记录
        execution = TaskExecution.objects.create(
            schedule=schedule,
            trigger_type=trigger_type,
            status='pending',
            app=schedule.app,
            target_date=target_date
        )
        
        # 确定执行参数
        app_id = schedule.app.id if schedule.app else None
        
        return self._execute_task(
            execution=execution,
            app_id=app_id,
            target_date=target_date,
            skip_notifications=schedule.skip_notifications,
            timeout_minutes=schedule.timeout_minutes
        )
    
    def _execute_task(self, execution: TaskExecution, app_id=None, target_date=None, 
                      skip_notifications=False, timeout_minutes=30):
        """执行任务的核心方法"""
        self.current_execution = execution
        self.should_stop = False
        
        # 标记开始执行
        execution.mark_started()
        logger.info(f"开始执行任务: {execution}")
        
        # 准备命令参数
        cmd_args = []
        cmd_options = {
            'skip_notifications': skip_notifications,
            'verbosity': 1,
        }
        
        if app_id:
            cmd_options['app_id'] = app_id
            
        if target_date:
            if isinstance(target_date, datetime):
                target_date = target_date.date()
            cmd_options['date'] = target_date.strftime('%Y-%m-%d')
        
        # 捕获输出
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        success = False
        stats = {
            'success_count': 0,
            'error_count': 0,
            'alerts_generated': 0,
            'notifications_sent': 0,
            'errors': []
        }
        
        try:
            # 设置超时处理
            def timeout_handler(signum, frame):
                self.should_stop = True
                raise TimeoutError(f"任务执行超时 ({timeout_minutes}分钟)")
            
            # 在支持的系统上设置超时信号 (仅在主线程中)
            if hasattr(signal, 'SIGALRM') and threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_minutes * 60)
            
            # 重定向输出
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            try:
                # 执行Django管理命令
                call_command('run_daily_task', *cmd_args, **cmd_options)
                success = True
                
            except CommandError as e:
                logger.error(f"命令执行错误: {e}")
                stats['errors'].append(f"命令执行错误: {str(e)}")
                stats['error_count'] = 1
                
            except TimeoutError as e:
                logger.error(f"任务执行超时: {e}")
                stats['errors'].append(f"执行超时: {str(e)}")
                execution.status = 'timeout'
                
            except Exception as e:
                logger.error(f"任务执行异常: {e}")
                logger.error(traceback.format_exc())
                stats['errors'].append(f"执行异常: {str(e)}")
                stats['error_count'] = 1
                
            finally:
                # 恢复输出
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
                # 取消超时信号 (仅在主线程中)
                if hasattr(signal, 'SIGALRM') and threading.current_thread() is threading.main_thread():
                    signal.alarm(0)
        
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            logger.error(traceback.format_exc())
            stats['errors'].append(f"执行失败: {str(e)}")
        
        # 获取输出内容
        output_log = stdout_capture.getvalue()
        error_log = stderr_capture.getvalue()
        
        # 尝试从输出日志中解析统计信息
        try:
            stats.update(self._parse_execution_stats(output_log))
        except Exception as e:
            logger.warning(f"解析执行统计信息失败: {e}")
        
        # 标记执行完成
        if execution.status != 'timeout':
            execution.mark_completed(
                success=success,
                output_log=output_log,
                error_log=error_log,
                stats=stats
            )
        else:
            execution.mark_completed(
                success=False,
                output_log=output_log,
                error_log=error_log,
                stats=stats
            )
        
        self.current_execution = None
        
        logger.info(f"任务执行完成: {execution}, 成功: {success}")
        return success
    
    def _parse_execution_stats(self, output_log: str):
        """从输出日志中解析执行统计信息"""
        stats = {
            'success_count': 0,
            'error_count': 0,
            'alerts_generated': 0,
            'notifications_sent': 0
        }
        
        # 简单的日志解析逻辑
        lines = output_log.split('\n')
        for line in lines:
            line = line.strip()
            
            # 解析汇总信息
            if '成功处理:' in line:
                try:
                    stats['success_count'] = int(line.split('成功处理:')[1].strip())
                except (ValueError, IndexError):
                    pass
                    
            elif '失败数量:' in line:
                try:
                    stats['error_count'] = int(line.split('失败数量:')[1].strip())
                except (ValueError, IndexError):
                    pass
                    
            elif '生成告警:' in line:
                try:
                    stats['alerts_generated'] = int(line.split('生成告警:')[1].strip())
                except (ValueError, IndexError):
                    pass
                    
            elif '发送通知:' in line:
                try:
                    stats['notifications_sent'] = int(line.split('发送通知:')[1].strip())
                except (ValueError, IndexError):
                    pass
        
        return stats
    
    def stop_current_execution(self):
        """停止当前正在执行的任务"""
        if self.current_execution:
            self.should_stop = True
            logger.info(f"请求停止当前执行的任务: {self.current_execution}")
            return True
        return False


class TaskScheduler:
    """任务调度器 - 负责管理定时任务"""
    
    def __init__(self):
        self.executor = TaskExecutor()
        self.running = False
        self.scheduler_thread = None
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已经在运行")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self.running:
            try:
                self._check_and_execute_schedules()
            except Exception as e:
                logger.error(f"调度器执行异常: {e}")
                logger.error(traceback.format_exc())
            
            # 每分钟检查一次
            import time
            time.sleep(60)
    
    def _check_and_execute_schedules(self):
        """检查并执行到期的任务调度"""
        now = timezone.localtime(timezone.now())  # 使用本地时间
        current_minute = now.replace(second=0, microsecond=0)
        
        logger.debug(f"调度器检查时间: {current_minute.strftime('%Y-%m-%d %H:%M')}")
        
        # 获取所有活跃的调度
        schedules = TaskSchedule.objects.filter(is_active=True)
        logger.debug(f"找到 {schedules.count()} 个活跃调度")
        
        for schedule in schedules:
            schedule_time = f"{schedule.hour:02d}:{schedule.minute:02d}"
            should_execute = self._should_execute_now(schedule, current_minute)
            
            logger.debug(f"检查调度 '{schedule.name}' (预定时间: {schedule_time}, 当前: {current_minute.strftime('%H:%M')}): {'应执行' if should_execute else '无需执行'}")
            
            if should_execute:
                logger.info(f"触发任务调度: {schedule.name}")
                
                # 在新线程中执行任务，避免阻塞调度器
                task_thread = threading.Thread(
                    target=self.executor.execute_schedule_auto,
                    args=(schedule,),
                    daemon=True
                )
                task_thread.start()
    
    def _should_execute_now(self, schedule: TaskSchedule, current_time: datetime):
        """判断调度是否应该在当前时间执行"""
        # 检查小时和分钟是否匹配
        if (schedule.hour != current_time.hour or 
            schedule.minute != current_time.minute):
            return False
        
        # 检查频率
        if schedule.frequency == 'daily':
            return True
        elif schedule.frequency == 'weekly':
            # 检查星期几（0=周一）
            weekday = schedule.weekday if schedule.weekday is not None else 0
            return current_time.weekday() == weekday
        elif schedule.frequency == 'monthly':
            # 检查月份中的第几天
            day = schedule.day_of_month if schedule.day_of_month is not None else 1
            return current_time.day == day
        
        return False


# 全局调度器实例
_global_scheduler = None

def get_global_scheduler():
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TaskScheduler()
    return _global_scheduler

def start_scheduler():
    """启动全局调度器"""
    scheduler = get_global_scheduler()
    scheduler.start()

def stop_scheduler():
    """停止全局调度器"""
    scheduler = get_global_scheduler()
    scheduler.stop()