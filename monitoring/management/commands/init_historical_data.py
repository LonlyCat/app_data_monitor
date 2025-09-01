from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date, timedelta
from monitoring.models import App, DataRecord
from monitoring.utils.api_clients import AppleAppStoreClient, GooglePlayClient
from monitoring.utils.analytics import DataAnalyzer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '初始化App历史数据 (默认30天)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app-id',
            type=int,
            help='指定App ID，不指定则初始化所有活跃App'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='初始化天数，默认30天'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='开始日期 (YYYY-MM-DD)，默认从今天往前推算'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='结束日期 (YYYY-MM-DD)，默认为昨天'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制覆盖已存在的数据记录'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='试运行模式，不实际保存数据'
        )
        parser.add_argument(
            '--skip-api-delay',
            action='store_true',
            help='跳过API调用延迟（用于测试，生产环境不建议使用）'
        )

    def handle(self, *args, **options):
        app_id = options.get('app_id')
        days = options.get('days', 30)
        start_date = options.get('start_date')
        end_date = options.get('end_date')
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        skip_api_delay = options.get('skip_api_delay', False)

        self.stdout.write(
            self.style.SUCCESS('🚀 开始初始化历史数据...')
        )

        # 确定日期范围
        if end_date:
            try:
                end_date = date.fromisoformat(end_date)
            except ValueError:
                raise CommandError(f"无效的结束日期格式: {end_date}，请使用 YYYY-MM-DD")
        else:
            # 默认结束日期为昨天，避免获取当日不完整数据
            end_date = date.today() - timedelta(days=1)

        if start_date:
            try:
                start_date = date.fromisoformat(start_date)
            except ValueError:
                raise CommandError(f"无效的开始日期格式: {start_date}，请使用 YYYY-MM-DD")
        else:
            start_date = end_date - timedelta(days=days-1)

        if start_date > end_date:
            raise CommandError("开始日期不能晚于结束日期")

        # 获取要处理的App
        if app_id:
            try:
                apps = [App.objects.get(id=app_id, is_active=True)]
            except App.DoesNotExist:
                raise CommandError(f"未找到ID为 {app_id} 的活跃App")
        else:
            apps = App.objects.filter(is_active=True)

        if not apps:
            self.stdout.write(
                self.style.WARNING('⚠️ 没有找到需要处理的活跃App')
            )
            return

        self.stdout.write(
            f"📊 将为 {len(apps)} 个App初始化从 {start_date} 到 {end_date} 的历史数据"
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 试运行模式：不会实际保存数据')
            )

        total_days = (end_date - start_date).days + 1
        success_count = 0
        error_count = 0
        skipped_count = 0

        # 处理每个App
        for app in apps:
            self.stdout.write(f"\n📱 处理 {app.name} ({app.get_platform_display()})...")
            
            try:
                app_success, app_errors, app_skipped = self._init_app_historical_data(
                    app, start_date, end_date, force, dry_run, skip_api_delay
                )
                success_count += app_success
                error_count += app_errors
                skipped_count += app_skipped
                
                self.stdout.write(
                    f"  ✅ {app.name}: 成功 {app_success}，错误 {app_errors}，跳过 {app_skipped}"
                )
                
            except Exception as e:
                error_count += total_days
                self.stdout.write(
                    self.style.ERROR(f"  ❌ {app.name}: 初始化失败 - {str(e)}")
                )
                logger.exception(f"App {app.name} 历史数据初始化失败")

        # 输出总结
        self.stdout.write(f"\n📊 初始化完成总结:")
        self.stdout.write(f"  ✅ 成功记录: {success_count}")
        self.stdout.write(f"  ❌ 失败记录: {error_count}")
        self.stdout.write(f"  ⏭️  跳过记录: {skipped_count}")
        self.stdout.write(f"  📅 总处理天数: {total_days * len(apps)}")

        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'🎉 历史数据初始化完成！共成功处理 {success_count} 条记录')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️ 有 {error_count} 条记录处理失败，请检查日志')
            )

    def _init_app_historical_data(self, app, start_date, end_date, force, dry_run, skip_api_delay):
        """为单个App初始化历史数据"""
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        # 获取API客户端
        try:
            from monitoring.models import Credential
            from monitoring.utils.api_clients import APIClientFactory
            
            # 获取对应平台的凭证
            credential = Credential.objects.filter(
                platform=app.platform, 
                is_active=True
            ).first()
            
            if not credential:
                raise Exception(f"未找到 {app.get_platform_display()} 平台的有效凭证")
            
            config_data = credential.get_config_data()
            if not config_data:
                raise Exception(f"{app.get_platform_display()} 平台凭证配置为空")
            
            if app.platform == 'ios':
                api_client = APIClientFactory.create_apple_client(config_data)
            else:  # android
                api_client = APIClientFactory.create_google_client(config_data)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"    ❌ 无法创建API客户端: {str(e)}")
            )
            return 0, (end_date - start_date).days + 1, 0

        # 逐日获取数据，从最新日期开始往前获取（防止未来数据未生成导致提前停止）
        current_date = end_date
        consecutive_no_data_count = 0
        max_consecutive_no_data = 3  # 连续3天没有数据就停止
        
        while current_date >= start_date:
            try:
                # 检查是否已存在数据
                existing_record = DataRecord.objects.filter(
                    app=app, 
                    date=current_date
                ).first()
                
                if existing_record and not force:
                    skipped_count += 1
                    self.stdout.write(f"    ⏭️  跳过 {current_date}: 数据已存在")
                    consecutive_no_data_count = 0  # 重置连续无数据计数
                    current_date -= timedelta(days=1)
                    continue
                
                if not dry_run:
                    # 获取历史数据
                    data = api_client.get_historical_data(app, current_date)
                    
                    # 验证数据有效性
                    if self._is_valid_data(data):
                        # 创建或更新数据记录
                        record, created = DataRecord.objects.update_or_create(
                            app=app,
                            date=current_date,
                            defaults={
                                'downloads': data.get('downloads', 0),
                                'sessions': data.get('sessions', 0),
                                'deletions': data.get('deletions', 0),
                                'unique_devices': data.get('unique_devices'),
                                'downloads_app_store_search': data.get('downloads_app_store_search', 0),
                                'downloads_web_referrer': data.get('downloads_web_referrer', 0),
                                'downloads_app_referrer': data.get('downloads_app_referrer', 0),
                                'downloads_app_store_browse': data.get('downloads_app_store_browse', 0),
                                'downloads_institutional': data.get('downloads_institutional', 0),
                                'downloads_other': data.get('downloads_other', 0),
                                'revenue': data.get('revenue', 0),
                                'rating': data.get('rating'),
                                'raw_data': data
                            }
                        )
                        
                        action = "创建" if created else "更新"
                        success_count += 1
                        consecutive_no_data_count = 0  # 重置连续无数据计数
                        self.stdout.write(f"    ✅ {action} {current_date}: 下载量 {data.get('downloads', 0)}")
                    elif data is None or not data:
                        # API返回空数据，可能是网络错误或API问题
                        error_count += 1
                        consecutive_no_data_count += 1
                        self.stdout.write(f"    ❌ {current_date}: API未返回数据")
                        
                        # 连续多天无数据时停止
                        if consecutive_no_data_count >= max_consecutive_no_data:
                            self.stdout.write(f"    ⏹️  连续 {consecutive_no_data_count} 天无数据，停止获取")
                            break
                    else:
                        # 数据全为0或无效数据，认为是数据未更新
                        consecutive_no_data_count += 1
                        self.stdout.write(f"    ⏹️  {current_date}: 数据未更新（全为0）")
                        
                        # 连续多天无有效数据时停止
                        if consecutive_no_data_count >= max_consecutive_no_data:
                            self.stdout.write(f"    ⏹️  连续 {consecutive_no_data_count} 天无有效数据，停止获取")
                            self.stdout.write(f"    💡 提示：从 {current_date} 开始的数据可能还未生成")
                            break
                else:
                    # 试运行模式
                    success_count += 1
                    consecutive_no_data_count = 0  # 试运行模式重置计数
                    self.stdout.write(f"    🔍 [试运行] {current_date}: 将获取历史数据")
                
                # API调用延迟，避免触发限流
                if not skip_api_delay and not dry_run:
                    import time
                    time.sleep(0.5)  # 500ms延迟
                    
            except Exception as e:
                error_count += 1
                consecutive_no_data_count += 1
                self.stdout.write(f"    ❌ {current_date}: {str(e)}")
                logger.exception(f"获取 {app.name} {current_date} 数据失败")
                
                # 连续异常时也停止
                if consecutive_no_data_count >= max_consecutive_no_data:
                    self.stdout.write(f"    ⏹️  连续 {consecutive_no_data_count} 天出现异常，停止获取")
                    break
            
            current_date -= timedelta(days=1)
        
        return success_count, error_count, skipped_count
    
    def _is_valid_data(self, data):
        """验证数据是否有效（非空且不全为0）"""
        if not data or not isinstance(data, dict):
            return False
        
        # 检查是否有错误字段
        if 'error' in data:
            return False
        
        # 检查主要指标是否有有效数据
        key_metrics = ['downloads', 'sessions', 'deletions']
        
        # 至少有一个主要指标不为0
        has_non_zero_data = False
        for metric in key_metrics:
            value = data.get(metric, 0)
            if value and value > 0:
                has_non_zero_data = True
                break
        
        # 检查下载来源细分数据
        if not has_non_zero_data:
            source_fields = [
                'downloads_app_store_search', 'downloads_web_referrer',
                'downloads_app_referrer', 'downloads_app_store_browse',
                'downloads_institutional', 'downloads_other'
            ]
            for field in source_fields:
                value = data.get(field, 0)
                if value and value > 0:
                    has_non_zero_data = True
                    break
        
        # 检查收入数据
        if not has_non_zero_data:
            revenue = data.get('revenue', 0)
            if revenue and float(revenue) > 0:
                has_non_zero_data = True
        
        if has_non_zero_data:
            logger.debug(f"数据有效性检查通过: {data}")
        else:
            logger.debug(f"数据无效（全为0或无关键数据）: {data}")
            
        return has_non_zero_data