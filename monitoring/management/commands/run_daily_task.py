from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import traceback

from ...models import App, Credential, DataRecord, DailyReportConfig
from ...utils.api_clients import APIClientFactory
from ...utils.analytics import DataAnalyzer
from ...utils.anomaly_detector import AnomalyDetector
from ...utils.lark_notifier import LarkNotifier


class Command(BaseCommand):
    help = '运行每日数据采集、分析和通知任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app-id',
            type=int,
            help='指定特定App的ID，不指定则处理所有活跃的App'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='指定处理的日期 (YYYY-MM-DD)，默认为昨天'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='试运行模式，不保存数据和发送通知'
        )
        parser.add_argument(
            '--skip-notifications',
            action='store_true',
            help='跳过通知发送，只采集和分析数据'
        )

    def handle(self, *args, **options):
        self.dry_run = options.get('dry_run', False)
        self.skip_notifications = options.get('skip_notifications', False)
        
        # 确定处理日期
        if options.get('date'):
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d')
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('日期格式错误，请使用 YYYY-MM-DD 格式')
                )
                return
        else:
            # 默认获取N天前的数据，N由`DATA_FETCH_DELAY_DAYS`配置决定
            # 这个延迟是为了确保Apple/Google的API数据已经完全生成并稳定
            # 默认是2天，这是一个比较安全的值，可根据实际情况在.env中调整
            delay_days = settings.DATA_FETCH_DELAY_DAYS
            target_date = datetime.now() - timedelta(days=delay_days)
        
        self.stdout.write(
            self.style.SUCCESS(f'开始处理 {target_date.strftime("%Y-%m-%d")} 的数据')
        )
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔄 试运行模式 - 不会保存数据或发送通知'))
        
        # 获取要处理的App列表
        app_filter = {'is_active': True}
        if options.get('app_id'):
            app_filter['id'] = options['app_id']
        
        apps = App.objects.filter(**app_filter)
        
        if not apps:
            self.stdout.write(self.style.WARNING('没有找到符合条件的App'))
            return
        
        self.stdout.write(f'找到 {apps.count()} 个App需要处理')
        
        # 初始化工具类
        self.analyzer = DataAnalyzer()
        self.detector = AnomalyDetector()
        self.notifier = LarkNotifier()
        
        # 统计信息
        self.stats = {
            'total_apps': apps.count(),
            'success_count': 0,
            'error_count': 0,
            'alerts_generated': 0,
            'notifications_sent': 0,
            'errors': []
        }
        
        # 处理每个App
        for app in apps:
            try:
                self.stdout.write(f'\n📱 处理App: {app.name} ({app.get_platform_display()})')
                self.process_single_app(app, target_date)
                self.stats['success_count'] += 1
                
            except Exception as e:
                self.stats['error_count'] += 1
                error_msg = f'处理App {app.name} 时发生错误: {str(e)}'
                self.stats['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
                self.stderr.write(traceback.format_exc())
                
                # 发送错误通知（如果不是试运行模式）
                if not self.dry_run and not self.skip_notifications:
                    self.send_error_notification(app, str(e))
        
        # 输出汇总信息
        self.print_summary()

    def process_single_app(self, app: App, target_date: datetime):
        """处理单个App的数据"""
        
        # 1. 获取API凭证
        try:
            credential = Credential.objects.get(platform=app.platform, is_active=True)
        except Credential.DoesNotExist:
            raise Exception(f'未找到{app.get_platform_display()}平台的有效凭证')
        
        # 2. 创建API客户端
        config_data = credential.get_config_data()
        if app.platform == 'ios':
            client = APIClientFactory.create_apple_client(config_data)
        else:
            client = APIClientFactory.create_google_client(config_data)
        
        self.stdout.write(f'  🔌 已连接到 {app.get_platform_display()} API')
        
        # 3. 获取数据
        end_date = target_date
        start_date = target_date
        
        if app.platform == 'ios':
            # Apple Analytics 新实现支持指定目标日期参数，避免重复数据
            raw_data = client.get_analytics_data(app.bundle_id, target_date)
        else:
            raw_data = client.get_statistics_data(app.bundle_id, start_date, end_date)
        
        if 'error' in raw_data:
            raise Exception(f'API数据获取失败: {raw_data["error"]}')
        
        self.stdout.write(f'  📊 获取到数据 - 下载量: {raw_data["downloads"]}, 会话数: {raw_data["sessions"]}')

        # 输出适配 AppStoreConnectClient 新增的数据与统计信息
        if app.platform == 'ios':
            # 输出详细统计信息（包含0值，便于观察数据变化）
            updates = raw_data.get('updates', 0)
            if isinstance(updates, (int, float)):
                self.stdout.write(f'    🔄 更新数: {int(updates)}')
                
            reinstalls = raw_data.get('reinstalls', 0)  
            if isinstance(reinstalls, (int, float)):
                self.stdout.write(f'    🔁 重装数: {int(reinstalls)}')
                
            deletions = raw_data.get('deletions', 0)
            if isinstance(deletions, (int, float)):
                self.stdout.write(f'    🗑️ 删除数: {int(deletions)}')

            unique_devices = raw_data.get('unique_devices')
            if isinstance(unique_devices, (int, float)) and unique_devices > 0:
                self.stdout.write(f'    📱 独立设备数: {int(unique_devices)}')

            # 分报告的实例失败统计（若存在则输出，便于观测数据完整性）
            detailed = raw_data.get('raw_data') if isinstance(raw_data.get('raw_data'), dict) else {}
            if detailed:
                install_proc = (detailed.get('install_report') or {}).get('processed_data') or {}
                if install_proc:
                    failed, total = install_proc.get('failed_instances', 0), install_proc.get('total_instances', 0)
                    if failed:
                        self.stdout.write(f'    ⚠️ 安装报告实例失败: {failed}/{total}')

                session_proc = (detailed.get('session_report') or {}).get('processed_data') or {}
                if session_proc:
                    failed, total = session_proc.get('failed_instances', 0), session_proc.get('total_instances', 0)
                    if failed:
                        self.stdout.write(f'    ⚠️ 会话报告实例失败: {failed}/{total}')
        
        # 4. 保存数据记录
        if not self.dry_run:
            _, created = DataRecord.objects.update_or_create(
                app=app,
                date=target_date.date(),
                defaults={
                    'downloads': raw_data.get('downloads', 0),
                    'sessions': raw_data.get('sessions', 0),
                    'deletions': raw_data.get('deletions', 0),
                    'unique_devices': raw_data.get('unique_devices'),
                    'revenue': raw_data.get('revenue', 0),
                    'rating': raw_data.get('rating'),
                    # 下载来源细分数据
                    'downloads_app_store_search': raw_data.get('downloads_app_store_search', 0),
                    'downloads_web_referrer': raw_data.get('downloads_web_referrer', 0),
                    'downloads_app_referrer': raw_data.get('downloads_app_referrer', 0),
                    'downloads_app_store_browse': raw_data.get('downloads_app_store_browse', 0),
                    'downloads_institutional': raw_data.get('downloads_institutional', 0),
                    'downloads_other': raw_data.get('downloads_other', 0),
                    'raw_data': raw_data
                }
            )
            action = "创建" if created else "更新"
            self.stdout.write(f'  💾 已{action}数据记录')
        
        # 5. 数据分析
        current_data = {
            'downloads': raw_data.get('downloads', 0),
            'sessions': raw_data.get('sessions', 0),
            'deletions': raw_data.get('deletions', 0),
            'unique_devices': raw_data.get('unique_devices'),
            # 下载来源细分数据
            'downloads_app_store_search': raw_data.get('downloads_app_store_search', 0),
            'downloads_web_referrer': raw_data.get('downloads_web_referrer', 0),
            'downloads_app_referrer': raw_data.get('downloads_app_referrer', 0),
            'downloads_app_store_browse': raw_data.get('downloads_app_store_browse', 0),
            'downloads_institutional': raw_data.get('downloads_institutional', 0),
            'downloads_other': raw_data.get('downloads_other', 0)
        }
        
        growth_rates = self.analyzer.calculate_growth_rates(
            current_data, app.id, target_date
        )
        
        insights = self.analyzer.generate_insights(
            app.id, current_data, growth_rates
        )
        
        self.stdout.write(f'  🔍 完成数据分析 - DOD下载增长: {growth_rates.get("downloads_dod", 0):.1f}%')
        
        # 6. 异常检测
        anomalies = self.detector.detect_anomalies(app.id, current_data, growth_rates)
        
        if anomalies:
            self.stdout.write(f'  ⚠️ 检测到 {len(anomalies)} 个异常')
            for anomaly in anomalies:
                if not self.dry_run:
                    alert_log = self.detector.log_anomaly(anomaly)
                    self.stats['alerts_generated'] += 1
                
                # 发送告警通知
                if not self.skip_notifications and not self.dry_run:
                    webhook_url = anomaly.get('webhook_url')
                    if webhook_url:
                        success = self.notifier.send_alert(webhook_url, anomaly)
                        if success:
                            self.stats['notifications_sent'] += 1
                            if not self.dry_run:
                                alert_log.is_sent = True
                                alert_log.sent_at = timezone.now()
                                alert_log.save()
                        self.stdout.write(f'    📢 告警通知: {"✅ 成功" if success else "❌ 失败"}')
        else:
            self.stdout.write(f'  ✅ 未检测到异常')
        
        # 7. 发送日报
        if not self.skip_notifications and not self.dry_run:
            try:
                report_config = DailyReportConfig.objects.get(app=app, is_active=True)
                
                report_data = self.analyzer.format_report_data(
                    app.name, current_data, growth_rates, insights, target_date
                )
                
                success = self.notifier.send_daily_report(
                    report_config.lark_webhook_daily, 
                    report_data
                )
                
                if success:
                    self.stats['notifications_sent'] += 1
                
                self.stdout.write(f'  📋 日报发送: {"✅ 成功" if success else "❌ 失败"}')
                
            except DailyReportConfig.DoesNotExist:
                self.stdout.write(f'  ⏭️ 跳过日报 - 未配置日报设置')
            except Exception as e:
                self.stdout.write(f'  ❌ 日报发送失败: {str(e)}')

    def send_error_notification(self, app: App, error_message: str):
        """发送错误通知"""
        try:
            # 尝试获取该App的日报配置来发送错误通知
            report_config = DailyReportConfig.objects.filter(
                app=app, is_active=True
            ).first()
            
            if report_config and report_config.lark_webhook_daily:
                title = f"{app.name} 数据采集失败"
                message = f"**错误详情:**\n{error_message}\n\n**时间:** {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.notifier.send_system_notification(
                    report_config.lark_webhook_daily,
                    title,
                    message,
                    'error'
                )
                
        except Exception as e:
            self.stderr.write(f'发送错误通知失败: {str(e)}')

    def print_summary(self):
        """打印汇总信息"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 任务执行汇总'))
        self.stdout.write('='*50)
        
        self.stdout.write(f'总计App数量: {self.stats["total_apps"]}')
        self.stdout.write(f'成功处理: {self.stats["success_count"]}')
        self.stdout.write(f'失败数量: {self.stats["error_count"]}')
        self.stdout.write(f'生成告警: {self.stats["alerts_generated"]}')
        self.stdout.write(f'发送通知: {self.stats["notifications_sent"]}')
        
        if self.stats['errors']:
            self.stdout.write('\n❌ 错误详情:')
            for i, error in enumerate(self.stats['errors'], 1):
                self.stdout.write(f'  {i}. {error}')
        
        # 根据结果显示不同颜色的状态
        if self.stats['error_count'] == 0:
            self.stdout.write(self.style.SUCCESS('\n🎉 所有任务执行成功！'))
        elif self.stats['success_count'] > 0:
            self.stdout.write(self.style.WARNING('\n⚠️ 部分任务执行成功'))
        else:
            self.stdout.write(self.style.ERROR('\n💥 所有任务执行失败！'))
        
        self.stdout.write('='*50)