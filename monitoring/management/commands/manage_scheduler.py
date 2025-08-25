from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import time
import signal
import sys

from ...utils.task_executor import get_global_scheduler, TaskScheduler
from ...models import TaskSchedule, TaskExecution


class Command(BaseCommand):
    help = '管理任务调度器 - 启动、停止、查看状态'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['start', 'stop', 'status', 'test'],
            help='要执行的操作: start(启动), stop(停止), status(状态), test(测试)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='以守护进程模式运行调度器'
        )
        parser.add_argument(
            '--test-schedule-id',
            type=int,
            help='测试模式下要执行的调度ID'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'start':
            self.start_scheduler(daemon=options.get('daemon', False))
        elif action == 'stop':
            self.stop_scheduler()
        elif action == 'status':
            self.show_status()
        elif action == 'test':
            self.test_scheduler(schedule_id=options.get('test_schedule_id'))

    def start_scheduler(self, daemon=False):
        """启动调度器"""
        self.stdout.write(self.style.SUCCESS('🚀 启动任务调度器...'))
        
        # 显示当前活跃的调度
        active_schedules = TaskSchedule.objects.filter(is_active=True)
        if active_schedules.exists():
            self.stdout.write(f'📋 发现 {active_schedules.count()} 个活跃的任务调度:')
            for schedule in active_schedules:
                cron_expr = schedule.get_cron_expression()
                app_name = schedule.app.name if schedule.app else "所有App"
                self.stdout.write(f'  • {schedule.name} - {app_name} ({cron_expr})')
        else:
            self.stdout.write(self.style.WARNING('⚠️ 没有找到活跃的任务调度'))
            return

        scheduler = get_global_scheduler()
        
        if daemon:
            self.stdout.write('🔄 以守护进程模式启动调度器...')
            
            # 设置信号处理器
            def signal_handler(signum, frame):
                self.stdout.write('\n🛑 收到停止信号，正在优雅关闭调度器...')
                scheduler.stop()
                self.stdout.write(self.style.SUCCESS('✅ 调度器已停止'))
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # 启动调度器
            scheduler.start()
            self.stdout.write(self.style.SUCCESS('✅ 调度器已启动，按 Ctrl+C 停止'))
            
            # 保持运行
            try:
                while scheduler.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                signal_handler(signal.SIGINT, None)
        else:
            # 非守护进程模式，只是测试启动
            scheduler.start()
            self.stdout.write(self.style.SUCCESS('✅ 调度器已在后台启动'))
            self.stdout.write('💡 使用 python manage.py manage_scheduler stop 来停止调度器')

    def stop_scheduler(self):
        """停止调度器"""
        self.stdout.write('🛑 正在停止调度器...')
        
        scheduler = get_global_scheduler()
        scheduler.stop()
        
        self.stdout.write(self.style.SUCCESS('✅ 调度器已停止'))

    def show_status(self):
        """显示调度器状态"""
        self.stdout.write(self.style.SUCCESS('📊 任务调度器状态'))
        self.stdout.write('='*50)
        
        # 调度器运行状态
        scheduler = get_global_scheduler()
        if scheduler.running:
            self.stdout.write(self.style.SUCCESS('🟢 调度器状态: 运行中'))
        else:
            self.stdout.write(self.style.ERROR('🔴 调度器状态: 已停止'))
        
        # 活跃的调度
        active_schedules = TaskSchedule.objects.filter(is_active=True)
        self.stdout.write(f'\n📋 活跃调度数量: {active_schedules.count()}')
        
        if active_schedules.exists():
            for schedule in active_schedules:
                cron_expr = schedule.get_cron_expression()
                app_name = schedule.app.name if schedule.app else "所有App"
                self.stdout.write(f'  • {schedule.name} - {app_name} ({cron_expr})')
        
        # 最近执行记录
        recent_executions = TaskExecution.objects.order_by('-created_at')[:5]
        if recent_executions.exists():
            self.stdout.write(f'\n📝 最近 {recent_executions.count()} 次执行:')
            for execution in recent_executions:
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'running': '🔄',
                    'pending': '⏳',
                    'timeout': '⏰',
                    'cancelled': '🚫'
                }.get(execution.status, '❓')
                
                schedule_name = execution.schedule.name if execution.schedule else "手动任务"
                app_name = execution.app.name if execution.app else "所有App"
                time_str = execution.created_at.strftime('%Y-%m-%d %H:%M:%S')
                
                duration = ""
                if execution.duration_seconds:
                    if execution.duration_seconds < 60:
                        duration = f" ({execution.duration_seconds}秒)"
                    else:
                        minutes = execution.duration_seconds // 60
                        seconds = execution.duration_seconds % 60
                        duration = f" ({minutes}分{seconds}秒)"
                
                self.stdout.write(f'  {status_emoji} {time_str} - {schedule_name} ({app_name}){duration}')
        
        # 正在运行的任务
        running_executions = TaskExecution.objects.filter(status='running')
        if running_executions.exists():
            self.stdout.write(f'\n🔄 正在运行的任务: {running_executions.count()} 个')
            for execution in running_executions:
                schedule_name = execution.schedule.name if execution.schedule else "手动任务"
                app_name = execution.app.name if execution.app else "所有App"
                started_time = execution.started_at.strftime('%H:%M:%S') if execution.started_at else "未知"
                self.stdout.write(f'  • {schedule_name} ({app_name}) - 开始时间: {started_time}')
        
        self.stdout.write('='*50)

    def test_scheduler(self, schedule_id=None):
        """测试调度器"""
        self.stdout.write(self.style.SUCCESS('🧪 测试任务调度器'))
        self.stdout.write('='*50)
        
        if schedule_id:
            # 测试特定调度
            try:
                schedule = TaskSchedule.objects.get(id=schedule_id, is_active=True)
                self.stdout.write(f'🎯 测试调度: {schedule.name}')
                
                from ...utils.task_executor import TaskExecutor
                executor = TaskExecutor()
                
                self.stdout.write('⏳ 正在执行任务...')
                success = executor.execute_schedule_manual(schedule)
                
                if success:
                    self.stdout.write(self.style.SUCCESS('✅ 任务执行成功'))
                else:
                    self.stdout.write(self.style.ERROR('❌ 任务执行失败'))
                    
                # 显示执行结果
                latest_execution = TaskExecution.objects.filter(
                    schedule=schedule
                ).order_by('-created_at').first()
                
                if latest_execution:
                    self.stdout.write(f'\n📊 执行结果:')
                    self.stdout.write(f'  状态: {latest_execution.get_status_display()}')
                    self.stdout.write(f'  成功数量: {latest_execution.success_count}')
                    self.stdout.write(f'  失败数量: {latest_execution.error_count}')
                    self.stdout.write(f'  生成告警: {latest_execution.alerts_generated}')
                    self.stdout.write(f'  发送通知: {latest_execution.notifications_sent}')
                    
                    if latest_execution.duration_seconds:
                        duration = latest_execution.duration_seconds
                        if duration < 60:
                            self.stdout.write(f'  执行时长: {duration}秒')
                        else:
                            minutes = duration // 60
                            seconds = duration % 60
                            self.stdout.write(f'  执行时长: {minutes}分{seconds}秒')
                
            except TaskSchedule.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ 未找到ID为 {schedule_id} 的活跃调度'))
                return
                
        else:
            # 测试调度器逻辑
            scheduler = get_global_scheduler()
            
            # 测试时间匹配逻辑
            now = timezone.now()
            current_minute = now.replace(second=0, microsecond=0)
            
            self.stdout.write(f'🕐 当前时间: {now.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'🎯 检查时间点: {current_minute.strftime("%Y-%m-%d %H:%M")}')
            
            schedules = TaskSchedule.objects.filter(is_active=True)
            should_execute = []
            
            for schedule in schedules:
                if scheduler._should_execute_now(schedule, current_minute):
                    should_execute.append(schedule)
            
            if should_execute:
                self.stdout.write(f'\n⏰ 在当前时间点应该执行的调度 ({len(should_execute)} 个):')
                for schedule in should_execute:
                    app_name = schedule.app.name if schedule.app else "所有App"
                    self.stdout.write(f'  • {schedule.name} - {app_name}')
            else:
                self.stdout.write(f'\n✅ 当前时间点没有需要执行的调度')
            
            # 显示下一个执行时间
            self.stdout.write(f'\n📅 接下来24小时内的执行计划:')
            import calendar
            from datetime import timedelta
            
            for schedule in schedules[:3]:  # 只显示前3个调度的计划
                app_name = schedule.app.name if schedule.app else "所有App"
                next_times = []
                
                # 计算接下来24小时内的执行时间
                check_time = now.replace(minute=0, second=0, microsecond=0)
                for _ in range(24 * 60):  # 检查24小时 * 60分钟
                    if scheduler._should_execute_now(schedule, check_time):
                        next_times.append(check_time)
                        if len(next_times) >= 3:  # 最多显示3个时间
                            break
                    check_time += timedelta(minutes=1)
                
                if next_times:
                    times_str = ", ".join([t.strftime("%m-%d %H:%M") for t in next_times])
                    self.stdout.write(f'  • {schedule.name} ({app_name}): {times_str}')
                else:
                    self.stdout.write(f'  • {schedule.name} ({app_name}): 24小时内无执行计划')
        
        self.stdout.write('='*50)