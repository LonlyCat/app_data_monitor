from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import random
from ...models import App, DataRecord


class Command(BaseCommand):
    help = '生成示例数据用于测试'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='生成多少天的数据 (默认30天)'
        )
        parser.add_argument(
            '--app-id',
            type=int,
            help='为特定App生成数据，不指定则为所有App生成'
        )
        parser.add_argument(
            '--with-anomalies',
            action='store_true',
            help='在数据中包含一些异常值'
        )

    def handle(self, *args, **options):
        days = options['days']
        with_anomalies = options['with_anomalies']
        
        # 获取要处理的App
        app_filter = {'is_active': True}
        if options.get('app_id'):
            app_filter['id'] = options['app_id']
        
        apps = App.objects.filter(**app_filter)
        
        if not apps:
            self.stdout.write(self.style.WARNING('没有找到符合条件的App'))
            return
        
        self.stdout.write(f'为 {apps.count()} 个App生成 {days} 天的示例数据')
        if with_anomalies:
            self.stdout.write('🎯 将包含异常数据点')
        
        for app in apps:
            self.stdout.write(f'\n📱 处理App: {app.name}')
            self.generate_app_data(app, days, with_anomalies)
        
        self.stdout.write(self.style.SUCCESS('\n🎉 示例数据生成完成！'))

    def generate_app_data(self, app, days, with_anomalies):
        """为单个App生成数据"""
        base_downloads = random.randint(1000, 10000)
        base_sessions = int(base_downloads * random.uniform(0.6, 0.9))
        base_revenue = random.uniform(100, 1000)
        
        anomaly_days = set()
        if with_anomalies:
            # 随机选择几天作为异常日
            num_anomalies = random.randint(2, max(3, days // 10))
            anomaly_days = set(random.sample(range(days), num_anomalies))
        
        created_count = 0
        updated_count = 0
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).date()
            
            # 生成基础趋势 (轻微上升或下降)
            trend_factor = 1 + (i / days) * random.uniform(-0.3, 0.5)
            
            # 添加随机波动
            daily_variation = random.uniform(0.8, 1.2)
            
            # 周末效应 (周末数据通常较低)
            weekday = date.weekday()
            weekend_factor = 0.7 if weekday >= 5 else 1.0
            
            # 计算基础值
            downloads = int(base_downloads * trend_factor * daily_variation * weekend_factor)
            sessions = int(base_sessions * trend_factor * daily_variation * weekend_factor)
            revenue = base_revenue * trend_factor * daily_variation * weekend_factor
            
            # 添加异常值
            if i in anomaly_days:
                anomaly_type = random.choice(['spike', 'drop'])
                if anomaly_type == 'spike':
                    # 暴增
                    multiplier = random.uniform(2.5, 5.0)
                    downloads = int(downloads * multiplier)
                    sessions = int(sessions * multiplier * 0.8)  # 会话增长通常小于下载
                    revenue *= multiplier * 0.9
                    self.stdout.write(f'  📈 异常峰值: {date}')
                else:
                    # 暴跌
                    multiplier = random.uniform(0.1, 0.4)
                    downloads = int(downloads * multiplier)
                    sessions = int(sessions * multiplier)
                    revenue *= multiplier
                    self.stdout.write(f'  📉 异常低值: {date}')
            
            # 确保最小值
            downloads = max(downloads, 0)
            sessions = max(sessions, 0)
            revenue = max(revenue, 0)
            
            # 生成评分 (4.0-5.0之间，偶尔有低分)
            rating = round(random.uniform(4.0, 5.0), 1)
            if random.random() < 0.1:  # 10%概率出现低分
                rating = round(random.uniform(2.5, 3.9), 1)
            
            # 创建或更新记录
            record, created = DataRecord.objects.update_or_create(
                app=app,
                date=date,
                defaults={
                    'downloads': downloads,
                    'sessions': sessions,
                    'revenue': round(revenue, 2),
                    'rating': rating,
                    'raw_data': {
                        'generated': True,
                        'base_downloads': base_downloads,
                        'trend_factor': round(trend_factor, 3),
                        'daily_variation': round(daily_variation, 3),
                        'weekend_factor': weekend_factor,
                        'anomaly': i in anomaly_days
                    }
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        self.stdout.write(
            f'  ✅ 完成 - 创建: {created_count}, 更新: {updated_count}'
        )
        
        # 显示数据概览
        total_downloads = sum(DataRecord.objects.filter(app=app).values_list('downloads', flat=True))
        avg_downloads = total_downloads // DataRecord.objects.filter(app=app).count() if DataRecord.objects.filter(app=app).count() > 0 else 0
        
        self.stdout.write(
            f'  📊 数据概览 - 总下载: {total_downloads:,}, 平均日下载: {avg_downloads:,}'
        )