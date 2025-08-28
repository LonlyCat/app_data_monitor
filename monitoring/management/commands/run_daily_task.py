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
        if app.platform == 'ios':
            # Apple Analytics 新实现支持指定目标日期参数，避免重复数据
            raw_data = client.get_analytics_data(app.bundle_id, target_date)
        else:
            # Android: 报表按月生成且延迟较大，客户端会返回有效日期与日度映射
            raw_data = client.get_statistics_data(app.bundle_id, target_date)
        
        if 'error' in raw_data:
            raise Exception(f'API数据获取失败: {raw_data["error"]}')
        
        # 输出数据与有效日期信息（Android特别关注effective_date）
        eff = raw_data.get('effective_date')
        if app.platform == 'android' and eff and eff != target_date.strftime('%Y-%m-%d'):
            self.stdout.write(f'  📊 获取到数据 - 下载量: {raw_data["downloads"]}, 会话数: {raw_data["sessions"]}（实际日期: {eff}）')
        else:
            self.stdout.write(f'  📊 获取到数据 - 下载量: {raw_data["downloads"]}, 会话数: {raw_data["sessions"]}')
        
        # 4. 保存数据记录
        if not self.dry_run:
            if app.platform == 'android':
                # 缺口补齐：将本次 overview 中出现的、且尚未入库的最近一段日期（不晚于目标日期或最大可用日期）补齐
                daily_map = raw_data.get('daily_map') or {}
                if daily_map:
                    # 仅考虑不晚于 max_available_date 的日期，避免未来空值
                    max_date_str = raw_data.get('max_available_date')
                    date_keys = sorted([d for d in daily_map.keys() if not max_date_str or d <= max_date_str])
                    created_count = 0
                    for d_str in date_keys:
                        try:
                            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
                        except Exception:
                            continue
                        # 若记录已存在则跳过
                        if DataRecord.objects.filter(app=app, date=d_obj).exists():
                            continue
                        d_stats = daily_map[d_str]
                        DataRecord.objects.update_or_create(
                            app=app,
                            date=d_obj,
                            defaults={
                                'downloads': int(d_stats.get('downloads', 0)),
                                'sessions': 0,
                                'deletions': int(d_stats.get('deletions', 0)),
                                'unique_devices': None,
                                'revenue': 0,
                                'rating': None,
                                'raw_data': {'source': 'gplay_overview', 'note': 'backfill from overview', 'blob_name': (raw_data.get('raw_response') or {}).get('blob_name')}
                            }
                        )
                        created_count += 1
                    if created_count:
                        self.stdout.write(f'  💾 已补齐Android缺口记录 {created_count} 天')
                # 仍然确保写入本次“有效日期”的匀质记录（若未被补齐循环覆盖）
                eff_str = raw_data.get('effective_date')
                record_date = target_date.date()
                if eff_str:
                    try:
                        record_date = datetime.strptime(eff_str, '%Y-%m-%d').date()
                    except Exception:
                        record_date = target_date.date()
                DataRecord.objects.update_or_create(
                    app=app,
                    date=record_date,
                    defaults={
                        'downloads': raw_data.get('downloads', 0),
                        'sessions': raw_data.get('sessions', 0),
                        'deletions': raw_data.get('deletions', 0),
                        'unique_devices': raw_data.get('unique_devices'),
                        'revenue': raw_data.get('revenue', 0),
                        'rating': raw_data.get('rating'),
                        'raw_data': raw_data
                    }
                )
                self.stdout.write(f'  💾 已更新Android记录（记录日期: {record_date}）')
            else:
                # iOS 原有逻辑
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
        # 确定用于分析/展示的日期：iOS 用 target_date；Android 用 effective_date（若有）
        data_date_for_analysis = target_date
        if app.platform == 'android':
            eff_str = raw_data.get('effective_date')
            if eff_str:
                try:
                    data_date_for_analysis = datetime.strptime(eff_str, '%Y-%m-%d')
                except Exception:
                    data_date_for_analysis = target_date

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
            current_data, app.id, data_date_for_analysis
        )
        
        # 标记哪些指标有效，传给通知层以便隐藏无数据指标
        metric_availability = {
            'sessions_available': bool(raw_data.get('sessions_available', True) if app.platform == 'ios' else raw_data.get('sessions_available', False))
        }

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
                    app.name, current_data, growth_rates, insights, data_date_for_analysis
                )
                report_data['metric_availability'] = metric_availability
                
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