from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from ...models import App, Credential
from ...utils.api_clients import APIClientFactory


class Command(BaseCommand):
    help = '测试API客户端连接和数据获取'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app-id',
            type=int,
            help='测试特定App的API连接'
        )
        parser.add_argument(
            '--platform',
            choices=['ios', 'android'],
            help='测试特定平台的API连接'
        )
        parser.add_argument(
            '--mock-data',
            action='store_true',
            help='使用模拟数据进行测试'
        )

    def handle(self, *args, **options):
        mock_data = options.get('mock_data', False)
        
        if mock_data:
            self.test_with_mock_data()
            return
        
        # 获取要测试的App
        app_filter = {'is_active': True}
        if options.get('app_id'):
            app_filter['id'] = options['app_id']
        if options.get('platform'):
            app_filter['platform'] = options['platform']
        
        apps = App.objects.filter(**app_filter)
        
        if not apps:
            self.stdout.write(self.style.WARNING('没有找到符合条件的App'))
            return
        
        self.stdout.write(f'🧪 测试 {apps.count()} 个App的API连接')
        
        for app in apps:
            self.test_app_api(app)

    def test_app_api(self, app: App):
        """测试单个App的API"""
        self.stdout.write(f'\n📱 测试App: {app.name} ({app.get_platform_display()})')
        
        try:
            # 获取凭证
            credential = Credential.objects.get(platform=app.platform, is_active=True)
            config_data = credential.get_config_data()
            
            self.stdout.write('  ✅ 凭证获取成功')
            
            # 创建客户端
            if app.platform == 'ios':
                client = APIClientFactory.create_apple_client(config_data)
                self.stdout.write('  ✅ Apple客户端创建成功')
                
                # 测试获取App信息
                self.stdout.write('  🔍 测试获取App信息...')
                app_info = client.get_app_info(app.bundle_id)
                if app_info:
                    self.stdout.write(f'    ✅ App信息获取成功: {app_info.get("attributes", {}).get("name", "Unknown")}')
                else:
                    self.stdout.write('    ❌ App信息获取失败')
                
                # 测试获取分析数据
                self.stdout.write('  📊 测试获取分析数据...')
                
                try:
                    # 测试时不指定日期，获取所有可用数据
                    analytics_data = client.get_analytics_data(app.bundle_id)
                    if 'error' in analytics_data:
                        self.stdout.write(f'    ⚠️ 分析数据获取有误: {analytics_data["error"]}')
                    else:
                        self.stdout.write(f'    ✅ 分析数据获取成功 - Downloads: {analytics_data["downloads"]}, Sessions: {analytics_data["sessions"]}')
                        
                        # 显示额外数据
                        if analytics_data.get('updates', 0) > 0:
                            self.stdout.write(f'      更新数: {analytics_data["updates"]}')
                        if analytics_data.get('reinstalls', 0) > 0:
                            self.stdout.write(f'      重装数: {analytics_data["reinstalls"]}')
                        if analytics_data.get('deletions', 0) > 0:
                            self.stdout.write(f'      删除数: {analytics_data["deletions"]}')
                        if analytics_data.get('unique_devices', 0) > 0:
                            self.stdout.write(f'      独立设备数: {analytics_data["unique_devices"]}')
                        
                        # 显示原始数据统计信息
                        if 'raw_data' in analytics_data:
                            raw_data = analytics_data['raw_data']
                            if 'install_report' in raw_data and 'processed_data' in raw_data['install_report']:
                                self.stdout.write('      📊 安装报告数据已获取')
                            if 'session_report' in raw_data and 'processed_data' in raw_data['session_report']:
                                self.stdout.write('      📊 会话报告数据已获取')
                        
                except Exception as e:
                    self.stdout.write(f'    ❌ 分析数据获取失败: {str(e)}')
                
            else:
                client = APIClientFactory.create_google_client(config_data)
                self.stdout.write('  ✅ Google客户端创建成功')
                
                # 测试获取App信息
                self.stdout.write('  🔍 测试获取App信息...')
                app_info = client.get_app_info(app.bundle_id)
                if app_info:
                    self.stdout.write('    ✅ App信息获取成功')
                else:
                    self.stdout.write('    ❌ App信息获取失败')
                
                # 测试获取统计数据
                self.stdout.write('  📊 测试获取统计数据...')
                yesterday = datetime.now() - timedelta(days=1)
                
                try:
                    stats_data = client.get_statistics_data(app.bundle_id, yesterday, yesterday)
                    if 'error' in stats_data:
                        self.stdout.write(f'    ⚠️ 统计数据获取有误: {stats_data["error"]}')
                    else:
                        self.stdout.write(f'    ✅ 统计数据获取成功 - Downloads: {stats_data["downloads"]}, Sessions: {stats_data["sessions"]}')
                except Exception as e:
                    self.stdout.write(f'    ❌ 统计数据获取失败: {str(e)}')
            
        except Credential.DoesNotExist:
            self.stdout.write(f'  ❌ 未找到{app.get_platform_display()}平台的有效凭证')
        except Exception as e:
            self.stdout.write(f'  ❌ 测试失败: {str(e)}')

    def test_with_mock_data(self):
        """使用模拟数据进行测试"""
        self.stdout.write('🎭 使用模拟数据进行测试')
        
        # 模拟Apple数据
        mock_apple_data = {
            'downloads': 1250,
            'sessions': 890,
            'revenue': 45.67,
            'raw_response': {'mock': True}
        }
        
        # 模拟Google数据
        mock_google_data = {
            'downloads': 2340,
            'sessions': 1560,
            'revenue': 78.90,
            'raw_response': {'mock': True}
        }
        
        self.stdout.write('\n📱 模拟Apple App Store数据:')
        self.stdout.write(f'  下载量: {mock_apple_data["downloads"]}')
        self.stdout.write(f'  会话数: {mock_apple_data["sessions"]}')
        self.stdout.write(f'  收入: ${mock_apple_data["revenue"]:.2f}')
        
        self.stdout.write('\n🤖 模拟Google Play数据:')
        self.stdout.write(f'  下载量: {mock_google_data["downloads"]}')
        self.stdout.write(f'  会话数: {mock_google_data["sessions"]}')
        self.stdout.write(f'  收入: ${mock_google_data["revenue"]:.2f}')
        
        self.stdout.write('\n✅ 模拟数据测试完成')
        self.stdout.write('\n💡 要测试真实API，请移除 --mock-data 参数')