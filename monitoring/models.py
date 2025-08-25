from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from .utils.encryption import encrypt_data, decrypt_data
import json


class App(models.Model):
    PLATFORM_CHOICES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='App名称')
    platform = models.CharField(
        max_length=10, 
        choices=PLATFORM_CHOICES, 
        verbose_name='平台'
    )
    bundle_id = models.CharField(
        max_length=200, 
        unique=True, 
        verbose_name='Bundle ID / Package Name'
    )
    is_active = models.BooleanField(default=True, verbose_name='启用监控')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'App'
        verbose_name_plural = 'Apps'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_platform_display()})"


class Credential(models.Model):
    PLATFORM_CHOICES = [
        ('ios', 'Apple App Store Connect'),
        ('android', 'Google Play Console'),
    ]
    
    platform = models.CharField(
        max_length=10, 
        choices=PLATFORM_CHOICES, 
        unique=True,
        verbose_name='平台'
    )
    _config_data = models.TextField(verbose_name='加密配置数据')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '平台凭证'
        verbose_name_plural = '平台凭证'
    
    def set_config_data(self, data):
        """加密存储配置数据"""
        json_data = json.dumps(data)
        self._config_data = encrypt_data(json_data)
    
    def get_config_data(self):
        """解密获取配置数据"""
        if self._config_data:
            decrypted_data = decrypt_data(self._config_data)
            return json.loads(decrypted_data)
        return {}
    
    config_data = property(get_config_data, set_config_data)
    
    def __str__(self):
        return f"{self.get_platform_display()} 凭证"


class AlertRule(models.Model):
    METRIC_CHOICES = [
        ('downloads', '下载量'),
        ('sessions', '活跃会话数'),
        ('deletions', '卸载量'),
        ('unique_devices', '活跃独立设备数'),
    ]
    
    COMPARISON_CHOICES = [
        ('dod', '日环比 (DOD)'),
        ('wow', '周同比 (WOW)'),
        ('absolute', '绝对值'),
    ]
    
    app = models.ForeignKey(App, on_delete=models.CASCADE, verbose_name='App')
    metric = models.CharField(
        max_length=20, 
        choices=METRIC_CHOICES, 
        verbose_name='监控指标'
    )
    comparison_type = models.CharField(
        max_length=10,
        choices=COMPARISON_CHOICES,
        default='dod',
        verbose_name='比较类型'
    )
    threshold_min = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(-1000)],
        verbose_name='下限阈值 (%)',
        help_text='低于此值触发告警，例如：-20 表示下跌超过20%'
    )
    threshold_max = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='上限阈值 (%)',
        help_text='高于此值触发告警，例如：200 表示增长超过200%'
    )
    is_active = models.BooleanField(default=True, verbose_name='启用告警')
    lark_webhook_alert = models.URLField(
        blank=True,
        verbose_name='Lark告警Webhook',
        help_text='专用告警通知Webhook地址'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '告警规则'
        verbose_name_plural = '告警规则'
        unique_together = ['app', 'metric', 'comparison_type']
    
    def __str__(self):
        return f"{self.app.name} - {self.get_metric_display()} ({self.get_comparison_type_display()})"


class DailyReportConfig(models.Model):
    app = models.OneToOneField(
        App, 
        on_delete=models.CASCADE, 
        verbose_name='App'
    )
    lark_webhook_daily = models.URLField(
        verbose_name='Lark日报Webhook',
        help_text='日常报告通知Webhook地址'
    )
    lark_sheet_id = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Lark表格ID',
        help_text='存储数据的Lark表格ID'
    )
    is_active = models.BooleanField(default=True, verbose_name='启用日报')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '日报配置'
        verbose_name_plural = '日报配置'
    
    def __str__(self):
        return f"{self.app.name} 日报配置"


class DataRecord(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, verbose_name='App')
    date = models.DateField(verbose_name='数据日期')
    downloads = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        verbose_name='下载量'
    )
    sessions = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)], 
        verbose_name='活跃会话数'
    )
    deletions = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='卸载量'
    )
    unique_devices = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name='活跃独立设备数'
    )
    
    # 下载来源细分数据
    downloads_app_store_search = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='App Store搜索下载量'
    )
    downloads_web_referrer = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='网页推荐下载量'
    )
    downloads_app_referrer = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='应用推荐下载量'
    )
    downloads_app_store_browse = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='App Store浏览下载量'
    )
    downloads_institutional = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='机构采购下载量'
    )
    downloads_other = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='其他渠道下载量',
        help_text='包含Unavailable等未分类来源'
    )
    revenue = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='收入'
    )
    rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name='评分'
    )
    raw_data = models.JSONField(
        default=dict,
        verbose_name='原始数据',
        help_text='从API获取的原始JSON数据'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')
    
    class Meta:
        verbose_name = '数据记录'
        verbose_name_plural = '数据记录'
        unique_together = ['app', 'date']
        ordering = ['-date', 'app']
    
    def __str__(self):
        return f"{self.app.name} - {self.date}"


class AlertLog(models.Model):
    ALERT_TYPES = [
        ('threshold', '阈值告警'),
        ('error', '错误告警'),
    ]
    
    app = models.ForeignKey(
        App, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name='App'
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        verbose_name='告警类型'
    )
    metric = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='相关指标'
    )
    message = models.TextField(verbose_name='告警消息')
    current_value = models.FloatField(
        null=True, 
        blank=True,
        verbose_name='当前值'
    )
    threshold_value = models.FloatField(
        null=True,
        blank=True, 
        verbose_name='阈值'
    )
    is_sent = models.BooleanField(default=False, verbose_name='已发送')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '告警日志'
        verbose_name_plural = '告警日志'
        ordering = ['-created_at']
    
    def __str__(self):
        app_name = self.app.name if self.app else "系统"
        return f"{app_name} - {self.get_alert_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class TaskSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', '每日'),
        ('weekly', '每周'),
        ('monthly', '每月'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('data_collection', '数据采集'),
        ('full_analysis', '完整分析'),
        ('alert_check', '告警检查'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='任务名称')
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        default='data_collection',
        verbose_name='任务类型'
    )
    app = models.ForeignKey(
        App, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='关联App',
        help_text='不指定则对所有活跃App执行'
    )
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default='daily',
        verbose_name='执行频率'
    )
    hour = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        default=2,
        verbose_name='执行小时 (0-23)'
    )
    minute = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(59)],
        default=0,
        verbose_name='执行分钟 (0-59)'
    )
    weekday = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        verbose_name='星期几 (0=Monday)',
        help_text='仅当频率为每周时有效'
    )
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name='月份中的第几天',
        help_text='仅当频率为每月时有效'
    )
    is_active = models.BooleanField(default=True, verbose_name='启用')
    skip_notifications = models.BooleanField(default=False, verbose_name='跳过通知')
    retry_count = models.IntegerField(default=3, verbose_name='失败重试次数')
    timeout_minutes = models.IntegerField(default=30, verbose_name='超时时间(分钟)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '任务调度'
        verbose_name_plural = '任务调度'
        ordering = ['hour', 'minute', 'name']
    
    def __str__(self):
        app_name = self.app.name if self.app else "所有App"
        return f"{self.name} - {app_name} ({self.get_frequency_display()} {self.hour:02d}:{self.minute:02d})"
    
    def get_cron_expression(self):
        """获取cron表达式"""
        if self.frequency == 'daily':
            return f"{self.minute} {self.hour} * * *"
        elif self.frequency == 'weekly':
            weekday = self.weekday if self.weekday is not None else 0
            return f"{self.minute} {self.hour} * * {weekday}"
        elif self.frequency == 'monthly':
            day = self.day_of_month if self.day_of_month is not None else 1
            return f"{self.minute} {self.hour} {day} * *"
        return None


class TaskExecution(models.Model):
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '执行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
        ('cancelled', '已取消'),
    ]
    
    TRIGGER_CHOICES = [
        ('scheduled', '定时触发'),
        ('manual', '手动触发'),
        ('retry', '重试执行'),
    ]
    
    schedule = models.ForeignKey(
        TaskSchedule, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='任务调度'
    )
    trigger_type = models.CharField(
        max_length=10,
        choices=TRIGGER_CHOICES,
        default='scheduled',
        verbose_name='触发方式'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='执行状态'
    )
    app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='执行App'
    )
    target_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='目标日期'
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    duration_seconds = models.IntegerField(null=True, blank=True, verbose_name='执行时长(秒)')
    success_count = models.IntegerField(default=0, verbose_name='成功处理数量')
    error_count = models.IntegerField(default=0, verbose_name='失败处理数量')
    alerts_generated = models.IntegerField(default=0, verbose_name='生成告警数量')
    notifications_sent = models.IntegerField(default=0, verbose_name='发送通知数量')
    output_log = models.TextField(blank=True, verbose_name='执行日志')
    error_log = models.TextField(blank=True, verbose_name='错误日志')
    retry_count = models.IntegerField(default=0, verbose_name='已重试次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '任务执行记录'
        verbose_name_plural = '任务执行记录'
        ordering = ['-created_at']
    
    def __str__(self):
        schedule_name = self.schedule.name if self.schedule else "手动任务"
        app_name = self.app.name if self.app else "所有App"
        return f"{schedule_name} - {app_name} ({self.get_status_display()}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_started(self):
        """标记任务开始"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, success=True, output_log="", error_log="", stats=None):
        """标记任务完成"""
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.status = 'success' if success else 'failed'
        self.output_log = output_log
        self.error_log = error_log
        
        if stats:
            self.success_count = stats.get('success_count', 0)
            self.error_count = stats.get('error_count', 0)
            self.alerts_generated = stats.get('alerts_generated', 0)
            self.notifications_sent = stats.get('notifications_sent', 0)
        
        self.save(update_fields=[
            'status', 'completed_at', 'duration_seconds', 'output_log', 
            'error_log', 'success_count', 'error_count', 'alerts_generated', 
            'notifications_sent'
        ])
    
    def can_retry(self):
        """判断是否可以重试"""
        if not self.schedule:
            return False
        return (self.status in ['failed', 'timeout'] and 
                self.retry_count < self.schedule.retry_count)