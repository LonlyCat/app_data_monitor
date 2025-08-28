from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.http import HttpResponse, Http404
from .models import (
    App, Credential, AlertRule, DailyReportConfig, 
    DataRecord, AlertLog, TaskSchedule, TaskExecution
)
from .forms import CredentialAdminForm
import json


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'bundle_id', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['name', 'bundle_id']
    list_editable = ['is_active']
    ordering = ['name']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'platform', 'bundle_id')
        }),
        ('状态', {
            'fields': ('is_active',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    form = CredentialAdminForm
    list_display = ['platform', 'is_active', 'created_at', 'config_preview']
    list_filter = ['platform', 'is_active', 'created_at']
    list_editable = ['is_active']
    
    fieldsets = (
        ('平台信息', {
            'fields': ('platform', 'is_active')
        }),
        ('Apple App Store Connect配置', {
            'fields': ('issuer_id', 'key_id', 'private_key'),
            'classes': ('collapse', 'ios-config'),
            'description': '配置Apple App Store Connect API访问凭证'
        }),
        ('Google Play Console配置', {
            'fields': ('service_account_email', 'service_account_key', 'gcs_bucket_name', 'gcs_project_id'),
            'classes': ('collapse', 'android-config'),
            'description': '配置Google Play Console API访问凭证'
        }),
    )
    
    def config_preview(self, obj):
        """显示配置预览"""
        config = obj.get_config_data()
        if not config:
            return "未配置"
        
        preview = []
        if obj.platform == 'ios':
            if config.get('issuer_id'):
                preview.append(f"Issuer ID: {config['issuer_id'][:8]}...")
            if config.get('key_id'):
                preview.append(f"Key ID: {config['key_id']}")
        elif obj.platform == 'android':
            if config.get('service_account_email'):
                preview.append(f"Email: {config['service_account_email']}")
        
        return mark_safe('<br>'.join(preview)) if preview else "已配置"
    
    config_preview.short_description = '配置预览'
    
    class Media:
        js = ('admin/js/credential_admin.js',)


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = [
        'app', 'metric', 'comparison_type', 'threshold_range', 
        'is_active', 'has_webhook', 'created_at'
    ]
    list_filter = [
        'metric', 'comparison_type', 'is_active', 'app__platform', 
        'created_at'
    ]
    search_fields = ['app__name', 'metric']
    list_editable = ['is_active']
    
    fieldsets = (
        ('基本设置', {
            'fields': ('app', 'metric', 'comparison_type', 'is_active')
        }),
        ('阈值配置', {
            'fields': ('threshold_min', 'threshold_max'),
            'description': '设置触发告警的阈值范围，可只设置上限或下限'
        }),
        ('通知配置', {
            'fields': ('lark_webhook_alert',),
            'description': '设置告警专用的Lark Webhook地址'
        }),
    )
    
    def threshold_range(self, obj):
        """显示阈值范围"""
        parts = []
        if obj.threshold_min is not None:
            parts.append(f"下限: {obj.threshold_min}%")
        if obj.threshold_max is not None:
            parts.append(f"上限: {obj.threshold_max}%")
        return " | ".join(parts) if parts else "未设置"
    
    threshold_range.short_description = '阈值范围'
    
    def has_webhook(self, obj):
        return bool(obj.lark_webhook_alert)
    
    has_webhook.short_description = '告警Webhook'
    has_webhook.boolean = True


@admin.register(DailyReportConfig)
class DailyReportConfigAdmin(admin.ModelAdmin):
    list_display = [
        'app', 'is_active', 'has_webhook', 'has_sheet', 'created_at'
    ]
    list_filter = ['is_active', 'app__platform', 'created_at']
    search_fields = ['app__name']
    list_editable = ['is_active']
    
    fieldsets = (
        ('基本设置', {
            'fields': ('app', 'is_active')
        }),
        ('通知配置', {
            'fields': ('lark_webhook_daily',),
            'description': '设置日报通知的Lark Webhook地址'
        }),
        ('数据存储', {
            'fields': ('lark_sheet_id',),
            'description': '设置存储数据的Lark表格ID（可选）'
        }),
    )
    
    def has_webhook(self, obj):
        return bool(obj.lark_webhook_daily)
    
    has_webhook.short_description = '日报Webhook'
    has_webhook.boolean = True
    
    def has_sheet(self, obj):
        return bool(obj.lark_sheet_id)
    
    has_sheet.short_description = 'Lark表格'
    has_sheet.boolean = True


@admin.register(DataRecord)
class DataRecordAdmin(admin.ModelAdmin):
    list_display = [
        'app', 'date', 'downloads', 'sessions', 'deletions',
        'unique_devices', 'top_source_type', 'created_at'
    ]
    list_filter = [
        'app', 'app__platform', 'date', 'created_at'
    ]
    search_fields = ['app__name']
    date_hierarchy = 'date'
    ordering = ['-date', 'app']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('app', 'date')
        }),
        ('数据指标', {
            'fields': ('downloads', 'sessions', 'deletions', 'unique_devices')
        }),
        ('下载来源细分', {
            'fields': (
                'downloads_app_store_search', 'downloads_web_referrer',
                'downloads_app_referrer', 'downloads_app_store_browse',
                'downloads_institutional', 'downloads_other'
            ),
            'classes': ('collapse',),
        }),
        ('原始数据', {
            'fields': ('export_raw_json_button', 'formatted_raw_data'),
            'classes': ('collapse',),
            'description': '从API获取的原始JSON数据'
        }),
    )
    
    readonly_fields = ['export_raw_json_button', 'formatted_raw_data', 'created_at']
    
    def top_source_type(self, obj):
        """显示主要下载来源"""
        source_types = {
            'App Store搜索': obj.downloads_app_store_search,
            '网页推荐': obj.downloads_web_referrer,
            '应用推荐': obj.downloads_app_referrer,
            'App Store浏览': obj.downloads_app_store_browse,
            '机构采购': obj.downloads_institutional,
            '其他': obj.downloads_other,
        }
        
        # 找到最大值的来源
        max_source = max(source_types.items(), key=lambda x: x[1])
        if max_source[1] > 0:
            total = sum(source_types.values())
            percentage = (max_source[1] / total * 100) if total > 0 else 0
            return f"{max_source[0]} ({percentage:.1f}%)"
        return "无数据"
    
    top_source_type.short_description = '主要来源'
    
    def formatted_raw_data(self, obj):
        """格式化显示原始数据"""
        if obj.raw_data:
            formatted_json = json.dumps(
                obj.raw_data, 
                indent=2, 
                ensure_ascii=False
            )
            return format_html('<pre>{}</pre>', formatted_json)
        return "无数据"
    
    formatted_raw_data.short_description = '原始数据'

    def export_raw_json_button(self, obj):
        """在详情页显示导出按钮，点击后下载原始JSON数据"""
        if not obj or not obj.pk:
            return "保存后可导出"
        url = reverse('admin:monitoring_datarecord_export_raw_json', args=[obj.pk])
        # 使用admin默认按钮样式
        return format_html('<a class="button" href="{}">导出 JSON</a>', url)

    export_raw_json_button.short_description = '导出原始数据'

    def get_urls(self):
        """注册自定义导出URL"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/export_raw_json/',
                self.admin_site.admin_view(self.export_raw_json),
                name='monitoring_datarecord_export_raw_json'
            ),
        ]
        return custom_urls + urls

    def export_raw_json(self, request, pk):
        """导出指定记录的原始JSON数据并触发浏览器下载"""
        obj = self.get_object(request, pk)
        if obj is None:
            raise Http404("记录不存在")

        data = obj.raw_data or {}
        content = json.dumps(data, indent=2, ensure_ascii=False)

        app_slug = slugify(obj.app.name)
        filename = f"datarecord_{app_slug}_{obj.date}.json"

        response = HttpResponse(content, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = [
        'app', 'alert_type', 'metric', 'current_value', 
        'threshold_value', 'is_sent', 'created_at'
    ]
    list_filter = [
        'alert_type', 'metric', 'is_sent', 'app__platform', 
        'created_at'
    ]
    search_fields = ['app__name', 'message', 'metric']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('告警信息', {
            'fields': ('app', 'alert_type', 'metric', 'message')
        }),
        ('数值信息', {
            'fields': ('current_value', 'threshold_value')
        }),
        ('发送状态', {
            'fields': ('is_sent', 'sent_at')
        }),
    )
    
    readonly_fields = ['created_at', 'sent_at']
    
    actions = ['mark_as_sent']
    
    def mark_as_sent(self, request, queryset):
        """标记为已发送"""
        from django.utils import timezone
        updated = queryset.update(is_sent=True, sent_at=timezone.now())
        self.message_user(
            request, 
            f"已标记 {updated} 条告警为已发送状态。"
        )
    
    mark_as_sent.short_description = "标记选中的告警为已发送"


@admin.register(TaskSchedule)
class TaskScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'task_type', 'app', 'frequency', 'schedule_time', 
        'is_active', 'last_execution', 'next_execution_info', 'created_at'
    ]
    list_filter = [
        'task_type', 'frequency', 'is_active', 'app__platform', 
        'created_at'
    ]
    search_fields = ['name', 'app__name']
    list_editable = ['is_active']
    
    fieldsets = (
        ('基本设置', {
            'fields': ('name', 'task_type', 'app', 'is_active')
        }),
        ('调度配置', {
            'fields': ('frequency', 'hour', 'minute', 'weekday', 'day_of_month'),
            'description': '配置任务执行的时间和频率'
        }),
        ('执行配置', {
            'fields': ('skip_notifications', 'retry_count', 'timeout_minutes'),
            'description': '配置任务执行的行为参数'
        }),
    )
    
    actions = ['execute_now', 'enable_schedules', 'disable_schedules']
    
    def schedule_time(self, obj):
        """显示调度时间"""
        time_str = f"{obj.hour:02d}:{obj.minute:02d}"
        if obj.frequency == 'daily':
            return f"每日 {time_str}"
        elif obj.frequency == 'weekly':
            weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            weekday_name = weekdays[obj.weekday] if obj.weekday is not None else '周一'
            return f"{weekday_name} {time_str}"
        elif obj.frequency == 'monthly':
            day = obj.day_of_month if obj.day_of_month else 1
            return f"每月{day}日 {time_str}"
        return time_str
    
    schedule_time.short_description = '执行时间'
    
    def last_execution(self, obj):
        """显示最后执行时间"""
        last_exec = TaskExecution.objects.filter(
            schedule=obj
        ).order_by('-created_at').first()
        
        if last_exec:
            status_color = {
                'success': 'green',
                'failed': 'red',
                'running': 'orange',
                'pending': 'blue'
            }.get(last_exec.status, 'black')
            
            return format_html(
                '<span style="color: {};">{} ({})</span>',
                status_color,
                last_exec.created_at.strftime('%Y-%m-%d %H:%M'),
                last_exec.get_status_display()
            )
        return "从未执行"
    
    last_execution.short_description = '最后执行'
    
    def next_execution_info(self, obj):
        """显示下次执行信息"""
        if not obj.is_active:
            return format_html('<span style="color: gray;">已禁用</span>')
        
        cron_expr = obj.get_cron_expression()
        return format_html(
            '<span title="Cron: {}">{}</span>',
            cron_expr,
            self.schedule_time(obj)
        )
    
    next_execution_info.short_description = '下次执行'
    
    def execute_now(self, request, queryset):
        """立即执行选中的任务"""
        from .utils.task_executor import TaskExecutor
        
        executed_count = 0
        for schedule in queryset:
            if schedule.is_active:
                executor = TaskExecutor()
                executor.execute_schedule_manual(schedule)
                executed_count += 1
        
        self.message_user(
            request,
            f"已创建 {executed_count} 个手动执行任务。"
        )
    
    execute_now.short_description = "立即执行选中的任务"
    
    def enable_schedules(self, request, queryset):
        """启用选中的调度"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"已启用 {updated} 个任务调度。"
        )
    
    enable_schedules.short_description = "启用选中的任务调度"
    
    def disable_schedules(self, request, queryset):
        """禁用选中的调度"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"已禁用 {updated} 个任务调度。"
        )
    
    disable_schedules.short_description = "禁用选中的任务调度"


@admin.register(TaskExecution)
class TaskExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'schedule_name', 'app', 'trigger_type', 'status', 
        'execution_time', 'duration_display', 'stats_summary',
        'created_at'
    ]
    list_filter = [
        'trigger_type', 'status', 'app__platform', 'created_at'
    ]
    search_fields = ['schedule__name', 'app__name']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('执行信息', {
            'fields': ('schedule', 'trigger_type', 'status', 'app', 'target_date')
        }),
        ('时间信息', {
            'fields': ('started_at', 'completed_at', 'duration_seconds', 'retry_count')
        }),
        ('执行结果', {
            'fields': ('success_count', 'error_count', 'alerts_generated', 'notifications_sent')
        }),
        ('执行日志', {
            'fields': ('output_log', 'error_log'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = [
        'duration_seconds', 'started_at', 'completed_at', 
        'output_log', 'error_log', 'created_at'
    ]
    
    actions = ['retry_failed_executions', 'clear_old_logs']
    
    def schedule_name(self, obj):
        """显示调度名称"""
        return obj.schedule.name if obj.schedule else "手动任务"
    
    schedule_name.short_description = '任务名称'
    
    def execution_time(self, obj):
        """显示执行时间"""
        if obj.started_at and obj.completed_at:
            return f"{obj.started_at.strftime('%H:%M:%S')} - {obj.completed_at.strftime('%H:%M:%S')}"
        elif obj.started_at:
            return f"{obj.started_at.strftime('%H:%M:%S')} - 进行中"
        return "未开始"
    
    execution_time.short_description = '执行时间'
    
    def duration_display(self, obj):
        """显示执行时长"""
        if obj.duration_seconds is not None:
            if obj.duration_seconds < 60:
                return f"{obj.duration_seconds}秒"
            else:
                minutes = obj.duration_seconds // 60
                seconds = obj.duration_seconds % 60
                return f"{minutes}分{seconds}秒"
        return "-"
    
    duration_display.short_description = '执行时长'
    
    def stats_summary(self, obj):
        """显示统计摘要"""
        if obj.status == 'success':
            return format_html(
                '✅ 成功:{} | ⚠️ 告警:{} | 📢 通知:{}',
                obj.success_count, obj.alerts_generated, obj.notifications_sent
            )
        elif obj.status == 'failed':
            return format_html(
                '❌ 失败:{} | ✅ 成功:{}',
                obj.error_count, obj.success_count
            )
        elif obj.status == 'running':
            return format_html('<span style="color: orange;">🔄 执行中...</span>')
        else:
            return obj.get_status_display()
    
    stats_summary.short_description = '执行摘要'
    
    def retry_failed_executions(self, request, queryset):
        """重试失败的执行"""
        from .utils.task_executor import TaskExecutor
        
        retried_count = 0
        for execution in queryset:
            if execution.can_retry():
                executor = TaskExecutor()
                executor.retry_execution(execution)
                retried_count += 1
        
        self.message_user(
            request,
            f"已创建 {retried_count} 个重试任务。"
        )
    
    retry_failed_executions.short_description = "重试选中的失败任务"
    
    def clear_old_logs(self, request, queryset):
        """清理旧的执行日志"""
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timedelta(days=30)
        old_executions = queryset.filter(created_at__lt=cutoff_date)
        
        count = old_executions.count()
        old_executions.delete()
        
        self.message_user(
            request,
            f"已清理 {count} 条30天前的执行记录。"
        )
    
    clear_old_logs.short_description = "清理30天前的执行记录"


# 自定义管理界面标题
admin.site.site_header = "App数据监控管理后台"
admin.site.site_title = "App监控系统"
admin.site.index_title = "欢迎使用App数据监控平台"