from django.core.management.base import BaseCommand
from ...utils.lark_notifier import LarkNotifier
from ...models import DailyReportConfig, AlertRule


class Command(BaseCommand):
    help = '测试Lark Webhook连接'

    def add_arguments(self, parser):
        parser.add_argument(
            '--webhook-url',
            type=str,
            help='直接测试指定的Webhook URL'
        )
        parser.add_argument(
            '--app-id',
            type=int,
            help='测试指定App的Webhook配置'
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='测试所有配置的Webhook'
        )

    def handle(self, *args, **options):
        notifier = LarkNotifier()
        
        if options.get('webhook_url'):
            # 直接测试指定URL
            webhook_url = options['webhook_url']
            self.stdout.write(f'🧪 测试Webhook: {webhook_url}')
            
            result = notifier.test_webhook(webhook_url)
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f'✅ {result["message"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ {result["message"]}'))
                
        elif options.get('app_id'):
            # 测试指定App的配置
            app_id = options['app_id']
            self.test_app_webhooks(notifier, app_id)
            
        elif options.get('test_all'):
            # 测试所有Webhook
            self.test_all_webhooks(notifier)
            
        else:
            self.stdout.write(
                self.style.ERROR('请指定测试选项: --webhook-url, --app-id, 或 --test-all')
            )

    def test_app_webhooks(self, notifier, app_id):
        """测试指定App的Webhook配置"""
        self.stdout.write(f'🧪 测试App ID {app_id} 的Webhook配置')
        
        # 测试日报Webhook
        try:
            daily_config = DailyReportConfig.objects.get(app_id=app_id, is_active=True)
            self.stdout.write(f'📋 测试日报Webhook')
            result = notifier.test_webhook(daily_config.lark_webhook_daily)
            status = '✅ 成功' if result['success'] else f'❌ 失败: {result["message"]}'
            self.stdout.write(f'   {status}')
        except DailyReportConfig.DoesNotExist:
            self.stdout.write('📋 未找到日报配置')
        
        # 测试告警Webhook
        alert_rules = AlertRule.objects.filter(
            app_id=app_id, 
            is_active=True,
            lark_webhook_alert__isnull=False
        ).exclude(lark_webhook_alert='')
        
        if alert_rules:
            self.stdout.write(f'⚠️ 测试告警Webhook ({alert_rules.count()}个)')
            tested_webhooks = set()
            
            for rule in alert_rules:
                webhook_url = rule.lark_webhook_alert
                if webhook_url not in tested_webhooks:
                    result = notifier.test_webhook(webhook_url)
                    status = '✅ 成功' if result['success'] else f'❌ 失败: {result["message"]}'
                    self.stdout.write(f'   {rule.get_metric_display()}: {status}')
                    tested_webhooks.add(webhook_url)
        else:
            self.stdout.write('⚠️ 未找到告警配置')

    def test_all_webhooks(self, notifier):
        """测试所有Webhook配置"""
        self.stdout.write('🧪 测试所有配置的Webhook')
        
        total_tested = 0
        success_count = 0
        
        # 测试所有日报Webhook
        daily_configs = DailyReportConfig.objects.filter(is_active=True)
        self.stdout.write(f'\n📋 日报Webhook ({daily_configs.count()}个)')
        
        for config in daily_configs:
            total_tested += 1
            result = notifier.test_webhook(config.lark_webhook_daily)
            if result['success']:
                success_count += 1
                status = '✅ 成功'
            else:
                status = f'❌ 失败: {result["message"]}'
            
            self.stdout.write(f'   {config.app.name}: {status}')
        
        # 测试所有告警Webhook
        alert_webhooks = AlertRule.objects.filter(
            is_active=True,
            lark_webhook_alert__isnull=False
        ).exclude(lark_webhook_alert='').values_list('lark_webhook_alert', flat=True).distinct()
        
        self.stdout.write(f'\n⚠️ 告警Webhook ({len(alert_webhooks)}个)')
        
        for webhook_url in alert_webhooks:
            total_tested += 1
            result = notifier.test_webhook(webhook_url)
            if result['success']:
                success_count += 1
                status = '✅ 成功'
            else:
                status = f'❌ 失败: {result["message"]}'
            
            # 显示使用此Webhook的规则
            rules = AlertRule.objects.filter(
                lark_webhook_alert=webhook_url, is_active=True
            )
            rules_text = ', '.join([f'{rule.app.name}-{rule.get_metric_display()}' for rule in rules])
            
            self.stdout.write(f'   {rules_text}: {status}')
        
        # 汇总
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'测试汇总: {success_count}/{total_tested} 成功')
        
        if success_count == total_tested:
            self.stdout.write(self.style.SUCCESS('🎉 所有Webhook测试通过！'))
        elif success_count > 0:
            self.stdout.write(self.style.WARNING('⚠️ 部分Webhook测试失败'))
        else:
            self.stdout.write(self.style.ERROR('💥 所有Webhook测试失败！'))