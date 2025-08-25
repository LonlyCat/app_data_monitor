from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta

from ...utils.task_executor import TaskExecutor
from ...models import App, TaskSchedule, TaskExecution


class Command(BaseCommand):
    help = '手动执行任务 - 支持立即执行特定调度或创建临时任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='执行指定ID的任务调度'
        )
        parser.add_argument(
            '--app-id',
            type=int,
            help='执行指定App的数据采集任务'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='指定处理的日期 (YYYY-MM-DD)，默认为昨天'
        )
        parser.add_argument(
            '--skip-notifications',
            action='store_true',
            help='跳过通知发送，只采集和分析数据'
        )
        parser.add_argument(
            '--list-schedules',
            action='store_true',
            help='列出所有可用的任务调度'
        )
        parser.add_argument(
            '--list-apps',
            action='store_true',
            help='列出所有可用的App'
        )

    def handle(self, *args, **options):
        if options.get('list_schedules'):
            self.list_schedules()
            return
            
        if options.get('list_apps'):
            self.list_apps()
            return

        # 解析目标日期
        target_date = None
        if options.get('date'):
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('日期格式错误，请使用 YYYY-MM-DD 格式')
                )
                return

        executor = TaskExecutor()

        # 执行指定调度
        if options.get('schedule_id'):
            self.execute_schedule(executor, options['schedule_id'], target_date)
            return

        # 执行指定App任务
        if options.get('app_id'):
            self.execute_app_task(
                executor, 
                options['app_id'], 
                target_date,
                options.get('skip_notifications', False)
            )
            return

        # 执行所有App任务
        self.execute_all_apps_task(
            executor, 
            target_date, 
            options.get('skip_notifications', False)
        )

    def execute_schedule(self, executor: TaskExecutor, schedule_id: int, target_date=None):
        """执行指定的任务调度"""
        try:
            schedule = TaskSchedule.objects.get(id=schedule_id)
        except TaskSchedule.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'未找到ID为 {schedule_id} 的任务调度')
            )
            return

        if not schedule.is_active:
            self.stdout.write(
                self.style.WARNING(f'任务调度 "{schedule.name}" 已被禁用')
            )
            confirm = input('是否继续执行？(y/N): ')
            if confirm.lower() != 'y':
                return

        app_name = schedule.app.name if schedule.app else "所有App"
        self.stdout.write(
            self.style.SUCCESS(f'🚀 开始执行任务调度: {schedule.name} ({app_name})')
        )

        # 显示执行参数
        params = []
        if target_date:
            params.append(f"目标日期: {target_date}")
        if schedule.skip_notifications:
            params.append("跳过通知")
        if params:
            self.stdout.write(f'📋 执行参数: {", ".join(params)}')

        success = executor.execute_schedule_manual(schedule, target_date)

        if success:
            self.stdout.write(self.style.SUCCESS('✅ 任务执行完成'))
        else:
            self.stdout.write(self.style.ERROR('❌ 任务执行失败'))

        # 显示最新的执行记录
        self.show_latest_execution_result(schedule)

    def execute_app_task(self, executor: TaskExecutor, app_id: int, target_date=None, skip_notifications=False):
        """执行指定App的任务"""
        try:
            app = App.objects.get(id=app_id)
        except App.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'未找到ID为 {app_id} 的App')
            )
            return

        if not app.is_active:
            self.stdout.write(
                self.style.WARNING(f'App "{app.name}" 已被禁用')
            )
            confirm = input('是否继续执行？(y/N): ')
            if confirm.lower() != 'y':
                return

        self.stdout.write(
            self.style.SUCCESS(f'🚀 开始执行App任务: {app.name} ({app.get_platform_display()})')
        )

        # 显示执行参数
        params = []
        if target_date:
            params.append(f"目标日期: {target_date}")
        if skip_notifications:
            params.append("跳过通知")
        if params:
            self.stdout.write(f'📋 执行参数: {", ".join(params)}')

        success = executor.execute_manual_task(
            app_id=app_id,
            target_date=target_date,
            skip_notifications=skip_notifications
        )

        if success:
            self.stdout.write(self.style.SUCCESS('✅ 任务执行完成'))
        else:
            self.stdout.write(self.style.ERROR('❌ 任务执行失败'))

        # 显示最新的执行记录
        latest_execution = TaskExecution.objects.filter(
            app=app,
            schedule__isnull=True
        ).order_by('-created_at').first()

        if latest_execution:
            self.show_execution_details(latest_execution)

    def execute_all_apps_task(self, executor: TaskExecutor, target_date=None, skip_notifications=False):
        """执行所有App的任务"""
        active_apps = App.objects.filter(is_active=True)
        
        if not active_apps.exists():
            self.stdout.write(self.style.WARNING('没有找到活跃的App'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'🚀 开始执行所有App任务 (共 {active_apps.count()} 个App)')
        )

        # 显示执行参数
        params = []
        if target_date:
            params.append(f"目标日期: {target_date}")
        if skip_notifications:
            params.append("跳过通知")
        if params:
            self.stdout.write(f'📋 执行参数: {", ".join(params)}')

        success = executor.execute_manual_task(
            app_id=None,
            target_date=target_date,
            skip_notifications=skip_notifications
        )

        if success:
            self.stdout.write(self.style.SUCCESS('✅ 任务执行完成'))
        else:
            self.stdout.write(self.style.ERROR('❌ 任务执行失败'))

        # 显示最新的执行记录
        latest_execution = TaskExecution.objects.filter(
            app__isnull=True,
            schedule__isnull=True
        ).order_by('-created_at').first()

        if latest_execution:
            self.show_execution_details(latest_execution)

    def list_schedules(self):
        """列出所有任务调度"""
        self.stdout.write(self.style.SUCCESS('📋 任务调度列表'))
        self.stdout.write('='*60)

        schedules = TaskSchedule.objects.all().order_by('name')
        
        if not schedules.exists():
            self.stdout.write(self.style.WARNING('没有找到任务调度'))
            return

        for schedule in schedules:
            status_emoji = '🟢' if schedule.is_active else '🔴'
            app_name = schedule.app.name if schedule.app else "所有App"
            cron_expr = schedule.get_cron_expression()
            
            # 最后执行状态
            last_exec = TaskExecution.objects.filter(
                schedule=schedule
            ).order_by('-created_at').first()
            
            last_status = ""
            if last_exec:
                status_emoji_map = {
                    'success': '✅',
                    'failed': '❌',
                    'running': '🔄',
                    'pending': '⏳'
                }
                status_emoji_exec = status_emoji_map.get(last_exec.status, '❓')
                last_status = f" (最后: {status_emoji_exec} {last_exec.created_at.strftime('%m-%d %H:%M')})"

            self.stdout.write(
                f'{status_emoji} [{schedule.id:2d}] {schedule.name} - {app_name}'
            )
            self.stdout.write(
                f'     📅 {schedule.get_frequency_display()} {schedule.hour:02d}:{schedule.minute:02d} '
                f'({cron_expr}){last_status}'
            )
            
        self.stdout.write('='*60)
        self.stdout.write('💡 使用 --schedule-id <ID> 执行指定调度')

    def list_apps(self):
        """列出所有App"""
        self.stdout.write(self.style.SUCCESS('📱 App列表'))
        self.stdout.write('='*60)

        apps = App.objects.all().order_by('name')
        
        if not apps.exists():
            self.stdout.write(self.style.WARNING('没有找到App'))
            return

        for app in apps:
            status_emoji = '🟢' if app.is_active else '🔴'
            platform_emoji = '🍎' if app.platform == 'ios' else '🤖'
            
            # 最近数据记录
            from ...models import DataRecord
            latest_record = DataRecord.objects.filter(
                app=app
            ).order_by('-date').first()
            
            latest_data = ""
            if latest_record:
                latest_data = f" (最近数据: {latest_record.date}, 下载: {latest_record.downloads})"

            self.stdout.write(
                f'{status_emoji} [{app.id:2d}] {platform_emoji} {app.name}'
            )
            self.stdout.write(
                f'     📦 {app.bundle_id}{latest_data}'
            )
            
        self.stdout.write('='*60)
        self.stdout.write('💡 使用 --app-id <ID> 执行指定App任务')

    def show_latest_execution_result(self, schedule: TaskSchedule):
        """显示最新的执行结果"""
        latest_execution = TaskExecution.objects.filter(
            schedule=schedule
        ).order_by('-created_at').first()

        if latest_execution:
            self.show_execution_details(latest_execution)

    def show_execution_details(self, execution: TaskExecution):
        """显示执行详情"""
        self.stdout.write('\n📊 执行结果:')
        self.stdout.write('-' * 30)
        
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'running': '🔄',
            'pending': '⏳',
            'timeout': '⏰',
            'cancelled': '🚫'
        }.get(execution.status, '❓')
        
        self.stdout.write(f'状态: {status_emoji} {execution.get_status_display()}')
        
        if execution.started_at and execution.completed_at:
            duration = execution.duration_seconds
            if duration:
                if duration < 60:
                    duration_str = f'{duration}秒'
                else:
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_str = f'{minutes}分{seconds}秒'
                self.stdout.write(f'执行时长: {duration_str}')
        
        if execution.status in ['success', 'failed']:
            self.stdout.write(f'成功处理: {execution.success_count}')
            if execution.error_count > 0:
                self.stdout.write(f'处理失败: {execution.error_count}')
            if execution.alerts_generated > 0:
                self.stdout.write(f'生成告警: {execution.alerts_generated}')
            if execution.notifications_sent > 0:
                self.stdout.write(f'发送通知: {execution.notifications_sent}')
        
        if execution.error_log and execution.status == 'failed':
            self.stdout.write(f'\n❌ 错误信息:')
            # 只显示前3行错误信息
            error_lines = execution.error_log.strip().split('\n')[:3]
            for line in error_lines:
                self.stdout.write(f'   {line}')
            if len(execution.error_log.strip().split('\n')) > 3:
                self.stdout.write('   ...')
        
        self.stdout.write('-' * 30)