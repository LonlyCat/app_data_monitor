from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from monitoring.models import TaskSchedule, TaskExecution
from monitoring.utils.task_executor import TaskExecutor

import os
import errno

try:
    import fcntl  # Unix 上的文件锁
except ImportError:  # pragma: no cover - Windows 等环境不使用
    fcntl = None


class Command(BaseCommand):
    help = '单次扫描并触发到期任务（供 cron / 调度器调用，无常驻）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='试运行，仅打印将要执行的调度，不真正执行'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        # 加锁，防止并发执行（例如 cron 抖动或上一次尚未结束）
        lock_path = '/tmp/scheduler_tick.lock'
        lock_file = None
        if fcntl is not None:
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            lock_file = open(lock_path, 'w')
            try:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                if e.errno in (errno.EACCES, errno.EAGAIN):
                    self.stdout.write('已有 scheduler_tick 在运行中，跳过本次触发')
                    return
                raise

        try:
            now = timezone.localtime(timezone.now())
            current_minute = now.replace(second=0, microsecond=0)

            # 仅筛选当前分钟应触发的候选（大幅减少扫描量）
            candidates = TaskSchedule.objects.filter(
                is_active=True,
                hour=now.hour,
                minute=now.minute,
            )

            if not candidates.exists():
                self.stdout.write(f'[{current_minute.strftime("%Y-%m-%d %H:%M")}] 无到期的调度')
                return

            executor = TaskExecutor()
            executed = 0

            for schedule in candidates:
                if not self._match_by_frequency(schedule, now):
                    continue

                # 避免并发/重复：若该调度已存在进行中的执行（pending/running）则跳过
                if TaskExecution.objects.filter(
                    schedule=schedule,
                    status__in=['pending', 'running']
                ).exists():
                    continue

                if dry_run:
                    self.stdout.write(f'DRY-RUN 将执行: {schedule.name}')
                    executed += 1
                    continue

                self.stdout.write(f'⏰ 触发执行: {schedule.name}')
                executor.execute_schedule_auto(schedule)
                executed += 1

            if executed == 0:
                self.stdout.write(f'[{current_minute.strftime("%Y-%m-%d %H:%M")}] 没有需要执行的调度')
            else:
                self.stdout.write(f'✅ 已触发 {executed} 个调度')

        finally:
            # 释放锁
            try:
                if fcntl is not None and lock_file is not None:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
                    lock_file.close()
            except Exception:
                pass

    def _match_by_frequency(self, schedule: TaskSchedule, now):
        if schedule.frequency == 'daily':
            return True
        if schedule.frequency == 'weekly':
            weekday = schedule.weekday if schedule.weekday is not None else 0
            return now.weekday() == weekday
        if schedule.frequency == 'monthly':
            day = schedule.day_of_month if schedule.day_of_month is not None else 1
            return now.day == day
        return False

