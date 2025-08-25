from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from django.utils import timezone
from ..models import AlertRule, AlertLog, DataRecord
import logging

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """异常波动检测器"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def detect_anomalies(self, app_id: int, current_data: Dict[str, Any], 
                        growth_rates: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        检测异常
        
        Args:
            app_id: App ID
            current_data: 当前数据
            growth_rates: 增长率数据
            
        Returns:
            异常列表，每个异常包含详细信息
        """
        anomalies = []
        
        try:
            # 获取该App的所有活跃告警规则
            alert_rules = AlertRule.objects.filter(
                app_id=app_id,
                is_active=True
            )
            
            self.logger.info(f"检测App {app_id}的异常，共有 {alert_rules.count()} 个活跃规则")
            
            for rule in alert_rules:
                anomaly = self._check_single_rule(rule, current_data, growth_rates)
                if anomaly:
                    anomalies.append(anomaly)
                    self.logger.warning(f"检测到异常: {anomaly}")
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"异常检测失败: {e}")
            return []
    
    def _check_single_rule(self, rule: AlertRule, current_data: Dict[str, Any], 
                          growth_rates: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        检查单个告警规则
        
        Args:
            rule: 告警规则
            current_data: 当前数据
            growth_rates: 增长率数据
            
        Returns:
            如果触发告警则返回异常信息，否则返回None
        """
        try:
            # 获取对应的值
            if rule.comparison_type == 'absolute':
                # 绝对值比较
                current_value = current_data.get(rule.metric, 0)
                comparison_text = "绝对值"
            else:
                # 增长率比较
                metric_key = f"{rule.metric}_{rule.comparison_type}"
                current_value = growth_rates.get(metric_key, 0)
                comparison_text = rule.get_comparison_type_display()
            
            # 检查是否触发告警
            triggered = False
            trigger_type = None
            threshold_value = None
            
            if rule.threshold_min is not None and current_value < rule.threshold_min:
                triggered = True
                trigger_type = 'below_minimum'
                threshold_value = rule.threshold_min
            
            if rule.threshold_max is not None and current_value > rule.threshold_max:
                triggered = True
                trigger_type = 'above_maximum'
                threshold_value = rule.threshold_max
            
            if not triggered:
                return None
            
            # 构建异常信息
            anomaly = {
                'rule_id': rule.id,
                'app_id': rule.app_id,
                'app_name': rule.app.name,
                'metric': rule.metric,
                'metric_display': rule.get_metric_display(),
                'comparison_type': rule.comparison_type,
                'comparison_display': comparison_text,
                'current_value': current_value,
                'threshold_value': threshold_value,
                'trigger_type': trigger_type,
                'webhook_url': rule.lark_webhook_alert,
                'message': self._generate_alert_message(
                    rule, current_value, threshold_value, trigger_type, comparison_text
                ),
                'severity': self._calculate_severity(rule, current_value, threshold_value, trigger_type)
            }
            
            return anomaly
            
        except Exception as e:
            self.logger.error(f"检查告警规则失败 (Rule ID: {rule.id}): {e}")
            return None
    
    def _generate_alert_message(self, rule: AlertRule, current_value: float, 
                               threshold_value: float, trigger_type: str, 
                               comparison_text: str) -> str:
        """生成告警消息"""
        app_name = rule.app.name
        metric_display = rule.get_metric_display()
        
        if trigger_type == 'above_maximum':
            direction = "超过上限"
            symbol = "📈" if rule.metric in ['downloads', 'sessions', 'revenue'] else "⚠️"
        else:  # below_minimum
            direction = "低于下限"
            symbol = "📉" if rule.metric in ['downloads', 'sessions', 'revenue'] else "⚠️"
        
        # 格式化数值显示
        if rule.comparison_type == 'absolute':
            current_str = f"{current_value:,.0f}" if current_value >= 1 else f"{current_value:.2f}"
            threshold_str = f"{threshold_value:,.0f}" if threshold_value >= 1 else f"{threshold_value:.2f}"
            unit = ""
        else:
            current_str = f"{current_value:+.1f}"
            threshold_str = f"{threshold_value:+.1f}"
            unit = "%"
        
        message = (
            f"{symbol} 【{app_name}】{metric_display}异常告警\n"
            f"📊 比较类型: {comparison_text}\n"
            f"📈 当前值: {current_str}{unit}\n"
            f"🎯 阈值: {direction} {threshold_str}{unit}\n"
            f"⏰ 检测时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return message
    
    def _calculate_severity(self, rule: AlertRule, current_value: float, 
                           threshold_value: float, trigger_type: str) -> str:
        """计算告警严重程度"""
        try:
            # 计算偏离程度
            if threshold_value == 0:
                deviation_ratio = float('inf') if current_value != 0 else 0
            else:
                deviation_ratio = abs(current_value - threshold_value) / abs(threshold_value)
            
            # 根据偏离程度判断严重性
            if deviation_ratio >= 2.0:  # 偏离200%以上
                return 'critical'
            elif deviation_ratio >= 1.0:  # 偏离100%-200%
                return 'high'
            elif deviation_ratio >= 0.5:  # 偏离50%-100%
                return 'medium'
            else:  # 偏离50%以下
                return 'low'
                
        except Exception:
            return 'medium'  # 默认中等严重程度
    
    def log_anomaly(self, anomaly: Dict[str, Any]) -> AlertLog:
        """
        记录异常到数据库
        
        Args:
            anomaly: 异常信息
            
        Returns:
            创建的AlertLog实例
        """
        try:
            from ..models import App
            
            app = App.objects.get(id=anomaly['app_id'])
            
            alert_log = AlertLog.objects.create(
                app=app,
                alert_type='threshold',
                metric=anomaly['metric'],
                message=anomaly['message'],
                current_value=anomaly['current_value'],
                threshold_value=anomaly['threshold_value'],
                is_sent=False
            )
            
            self.logger.info(f"异常已记录到数据库: AlertLog ID {alert_log.id}")
            return alert_log
            
        except Exception as e:
            self.logger.error(f"记录异常失败: {e}")
            raise
    
    def get_anomaly_statistics(self, app_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """
        获取异常统计信息
        
        Args:
            app_id: App ID，为None时统计所有App
            days: 统计天数
            
        Returns:
            统计信息
        """
        try:
            from datetime import timedelta
            
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # 构建查询条件
            query_kwargs = {
                'created_at__gte': start_date,
                'created_at__lte': end_date,
                'alert_type': 'threshold'
            }
            
            if app_id:
                query_kwargs['app_id'] = app_id
            
            # 查询数据
            alert_logs = AlertLog.objects.filter(**query_kwargs)
            
            # 统计信息
            total_alerts = alert_logs.count()
            sent_alerts = alert_logs.filter(is_sent=True).count()
            
            # 按指标分组统计
            metric_stats = {}
            for log in alert_logs:
                metric = log.metric
                if metric not in metric_stats:
                    metric_stats[metric] = 0
                metric_stats[metric] += 1
            
            # 按App分组统计（仅在查询所有App时）
            app_stats = {}
            if not app_id:
                for log in alert_logs:
                    app_name = log.app.name if log.app else 'Unknown'
                    if app_name not in app_stats:
                        app_stats[app_name] = 0
                    app_stats[app_name] += 1
            
            return {
                'period_days': days,
                'total_alerts': total_alerts,
                'sent_alerts': sent_alerts,
                'pending_alerts': total_alerts - sent_alerts,
                'metric_breakdown': metric_stats,
                'app_breakdown': app_stats,
                'alert_rate': round(total_alerts / days, 2) if days > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"获取异常统计失败: {e}")
            return {}
    
    def check_rule_effectiveness(self, rule_id: int, days: int = 30) -> Dict[str, Any]:
        """
        检查告警规则的有效性
        
        Args:
            rule_id: 告警规则ID
            days: 分析天数
            
        Returns:
            规则有效性分析
        """
        try:
            from datetime import timedelta
            
            rule = AlertRule.objects.get(id=rule_id)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # 获取该规则触发的告警
            alerts = AlertLog.objects.filter(
                app=rule.app,
                metric=rule.metric,
                alert_type='threshold',
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            total_alerts = alerts.count()
            
            if total_alerts == 0:
                return {
                    'rule_id': rule_id,
                    'effectiveness': 'inactive',
                    'total_alerts': 0,
                    'avg_alerts_per_day': 0,
                    'recommendation': '该规则在分析期间未触发任何告警，可能需要调整阈值'
                }
            
            # 计算统计信息
            avg_alerts_per_day = total_alerts / days
            sent_alerts = alerts.filter(is_sent=True).count()
            send_rate = (sent_alerts / total_alerts) * 100 if total_alerts > 0 else 0
            
            # 判断有效性
            if avg_alerts_per_day > 2:
                effectiveness = 'too_sensitive'
                recommendation = '规则过于敏感，建议放宽阈值以减少误报'
            elif avg_alerts_per_day < 0.1:
                effectiveness = 'not_sensitive'
                recommendation = '规则敏感度不足，建议收紧阈值以提高检测能力'
            else:
                effectiveness = 'appropriate'
                recommendation = '规则设置合理，保持当前配置'
            
            return {
                'rule_id': rule_id,
                'effectiveness': effectiveness,
                'total_alerts': total_alerts,
                'avg_alerts_per_day': round(avg_alerts_per_day, 2),
                'send_rate': round(send_rate, 2),
                'recommendation': recommendation,
                'analysis_period': f"{days}天"
            }
            
        except AlertRule.DoesNotExist:
            return {'error': f'告警规则 {rule_id} 不存在'}
        except Exception as e:
            self.logger.error(f"检查规则有效性失败: {e}")
            return {'error': str(e)}