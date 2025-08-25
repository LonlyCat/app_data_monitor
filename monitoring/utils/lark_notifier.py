import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class LarkNotifier:
    """Lark (飞书) 通知器"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.timeout = 30
    
    def send_daily_report(self, webhook_url: str, report_data: Dict[str, Any]) -> bool:
        """
        发送日报
        
        Args:
            webhook_url: Lark Webhook URL
            report_data: 报告数据
            
        Returns:
            发送是否成功
        """
        try:
            card = self._build_daily_report_card(report_data)
            return self._send_message(webhook_url, card)
            
        except Exception as e:
            self.logger.error(f"发送日报失败: {e}")
            return False
    
    def send_alert(self, webhook_url: str, anomaly: Dict[str, Any]) -> bool:
        """
        发送告警通知
        
        Args:
            webhook_url: Lark Webhook URL
            anomaly: 异常信息
            
        Returns:
            发送是否成功
        """
        try:
            card = self._build_alert_card(anomaly)
            return self._send_message(webhook_url, card)
            
        except Exception as e:
            self.logger.error(f"发送告警失败: {e}")
            return False
    
    def send_system_notification(self, webhook_url: str, title: str, message: str, 
                                level: str = 'info') -> bool:
        """
        发送系统通知
        
        Args:
            webhook_url: Lark Webhook URL
            title: 通知标题
            message: 通知内容
            level: 通知级别 (info, warning, error)
            
        Returns:
            发送是否成功
        """
        try:
            card = self._build_system_notification_card(title, message, level)
            return self._send_message(webhook_url, card)
            
        except Exception as e:
            self.logger.error(f"发送系统通知失败: {e}")
            return False
    
    def _build_daily_report_card(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建日报卡片"""
        app_name = report_data['app_name']
        data_date = report_data['date']
        metrics = report_data['metrics']
        insights = report_data.get('insights', [])
        summary = report_data.get('summary', '')
        message_date = datetime.now(timezone.utc).strftime('%Y-%m-%d') 

        # 构建指标元素
        metric_elements = []
        
        # 下载量
        downloads = metrics.get('downloads', {})
        downloads_text = self._format_metric_text(
            "📱 下载量", 
            downloads.get('value', 0),
            downloads.get('dod_change', 0),
            downloads.get('wow_change', 0)
        )
        metric_elements.append({
            "tag": "div",
            "text": {
                "content": downloads_text,
                "tag": "lark_md"
            }
        })
        
        # 会话数
        sessions = metrics.get('sessions', {})
        sessions_text = self._format_metric_text(
            "📊 活跃会话",
            sessions.get('value', 0),
            sessions.get('dod_change', 0),
            sessions.get('wow_change', 0)
        )
        metric_elements.append({
            "tag": "div",
            "text": {
                "content": sessions_text,
                "tag": "lark_md"
            }
        })
        
        # 卸载量
        deletions = metrics.get('deletions', {})
        deletions_text = self._format_metric_text(
            "🗑️ 卸载量",
            deletions.get('value', 0),
            deletions.get('dod_change', 0),
            deletions.get('wow_change', 0)
        )
        metric_elements.append({
            "tag": "div",
            "text": {
                "content": deletions_text,
                "tag": "lark_md"
            }
        })
        
        # 活跃独立设备数
        unique_devices = metrics.get('unique_devices', {})
        if unique_devices.get('value', 0) > 0:
            unique_devices_text = self._format_metric_text(
                "📱 独立设备",
                unique_devices.get('value', 0),
                unique_devices.get('dod_change', 0),
                unique_devices.get('wow_change', 0)
            )
            metric_elements.append({
                "tag": "div",
                "text": {
                    "content": unique_devices_text,
                    "tag": "lark_md"
                }
            })
        
        # 下载来源细分（如果有数据）
        source_breakdown = metrics.get('source_breakdown', {})
        if source_breakdown:
            # 构建来源数据映射和排序
            source_data = {
                '🔍 App Store搜索': source_breakdown.get('app_store_search', {}),
                '🌐 网页推荐': source_breakdown.get('web_referrer', {}),
                '📱 应用推荐': source_breakdown.get('app_referrer', {}),
                '🏢 机构采购': {'value': source_breakdown.get('institutional', 0)},
                '🔍 App Store浏览': {'value': source_breakdown.get('app_store_browse', 0)},
                '🔗 其他来源': {'value': source_breakdown.get('other', 0)}
            }
            
            # 过滤出非零数据并按下载量排序
            non_zero_sources = []
            for source_name, source_info in source_data.items():
                value = source_info.get('value', 0)
                if value > 0:
                    non_zero_sources.append((source_name, source_info, value))
            
            # 按下载量降序排序
            non_zero_sources.sort(key=lambda x: x[2], reverse=True)
            
            if non_zero_sources:
                # 找出主要来源
                main_source_name, _, main_source_value = non_zero_sources[0]
                total_source_downloads = sum(item[2] for item in non_zero_sources)
                main_source_percentage = (main_source_value / total_source_downloads * 100) if total_source_downloads > 0 else 0
                
                # 标题包含主要来源信息
                source_title = f"📊 **下载来源细分** (主要: {main_source_name} {main_source_percentage:.1f}%)"
                metric_elements.append({
                    "tag": "div",
                    "text": {
                        "content": source_title,
                        "tag": "lark_md"
                    }
                })
                
                # 显示所有非零来源，主要来源用✨标记
                for i, (source_name, source_info, value) in enumerate(non_zero_sources):
                    # 主要来源加特殊标记
                    display_name = f"✨ {source_name}" if i == 0 else source_name
                    
                    # 如果有增长率数据，使用完整格式；否则只显示数值
                    if 'dod_change' in source_info and 'wow_change' in source_info:
                        source_text = self._format_metric_text(
                            display_name,
                            value,
                            source_info.get('dod_change', 0),
                            source_info.get('wow_change', 0)
                        )
                    else:
                        # 简化格式，只显示数值和百分比
                        percentage = (value / total_source_downloads * 100) if total_source_downloads > 0 else 0
                        source_text = f"**{display_name}**: {value:,} ({percentage:.1f}%)"
                    
                    metric_elements.append({
                        "tag": "div",
                        "text": {
                            "content": source_text,
                            "tag": "lark_md"
                        }
                    })
        
        # 洞察部分
        insights_elements = []
        if insights:
            insights_elements.append({
                "tag": "div",
                "text": {
                    "content": "🔍 **数据洞察**",
                    "tag": "lark_md"
                }
            })
            for insight in insights[:3]:  # 最多显示3个洞察
                insights_elements.append({
                    "tag": "div",
                    "text": {
                        "content": f"• {insight}",
                        "tag": "lark_md"
                    }
                })
        
        # 构建完整卡片
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True
                },
                "header": {
                    "template": "blue",
                    "title": {
                        "content": f"📊 {app_name} 数据日报",
                        "tag": "plain_text"
                    },
                    "subtitle": {
                        "content": f"{message_date}",
                        "tag": "plain_text"
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**📈 {data_date} 数据概况**\n{summary}",
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "hr"
                    }
                ] + metric_elements + ([{
                    "tag": "hr"
                }] + insights_elements if insights else []) + [
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"报告时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
        }
        
        return card
    
    def _build_alert_card(self, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """构建告警卡片"""
        app_name = anomaly['app_name']
        metric_display = anomaly['metric_display']
        current_value = anomaly['current_value']
        threshold_value = anomaly['threshold_value']
        trigger_type = anomaly['trigger_type']
        severity = anomaly.get('severity', 'medium')
        comparison_display = anomaly.get('comparison_display', '')
        
        # 根据严重程度选择颜色和图标
        if severity == 'critical':
            color = "red"
            icon = "🚨"
        elif severity == 'high':
            color = "orange"
            icon = "⚠️"
        elif severity == 'medium':
            color = "yellow" 
            icon = "📊"
        else:
            color = "grey"
            icon = "ℹ️"
        
        # 格式化数值
        if 'dod' in anomaly.get('comparison_type', '') or 'wow' in anomaly.get('comparison_type', ''):
            current_str = f"{current_value:+.1f}%"
            threshold_str = f"{threshold_value:+.1f}%"
        else:
            current_str = f"{current_value:,.0f}" if current_value >= 1 else f"{current_value:.2f}"
            threshold_str = f"{threshold_value:,.0f}" if threshold_value >= 1 else f"{threshold_value:.2f}"
        
        # 触发方向描述
        if trigger_type == 'above_maximum':
            trigger_desc = "超过上限"
        else:
            trigger_desc = "低于下限"
        
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True
                },
                "header": {
                    "template": color,
                    "title": {
                        "content": f"{icon} {app_name} 异常告警",
                        "tag": "plain_text"
                    },
                    "subtitle": {
                        "content": f"{metric_display} {trigger_desc}",
                        "tag": "plain_text"
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**📊 监控指标**\n{metric_display}",
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**📈 比较类型**\n{comparison_display}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**🎯 当前值**\n{current_str}",
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**⚖️ 阈值**\n{trigger_desc} {threshold_str}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**🔥 严重程度**\n{self._get_severity_display(severity)}",
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "content": f"**⏰ 检测时间**\n{timezone.now().strftime('%Y-%m-%d %H:%M')}",
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "请及时关注并采取相应措施"
                            }
                        ]
                    }
                ]
            }
        }
        
        return card
    
    def _build_system_notification_card(self, title: str, message: str, level: str) -> Dict[str, Any]:
        """构建系统通知卡片"""
        color_map = {
            'info': 'blue',
            'warning': 'orange', 
            'error': 'red'
        }
        
        icon_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌'
        }
        
        color = color_map.get(level, 'blue')
        icon = icon_map.get(level, 'ℹ️')
        
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "template": color,
                    "title": {
                        "content": f"{icon} {title}",
                        "tag": "plain_text"
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": message,
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"通知时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
        }
        
        return card
    
    def _format_metric_text(self, label: str, value: float, dod_change: float = 0, 
                           wow_change: float = 0, is_currency: bool = False) -> str:
        """格式化指标文本"""
        if is_currency:
            value_str = f"${value:,.2f}" if value >= 1 else f"${value:.2f}"
        else:
            value_str = f"{value:,}" if value >= 1 else f"{value:.2f}"
        
        # DOD变化
        dod_arrow = "📈" if dod_change > 0 else "📉" if dod_change < 0 else "➡️"
        dod_text = f"{dod_change:+.1f}%" if dod_change != 0 else "0%"
        
        # WOW变化 
        wow_arrow = "📈" if wow_change > 0 else "📉" if wow_change < 0 else "➡️"
        wow_text = f"{wow_change:+.1f}%" if wow_change != 0 else "0%"
        
        return f"**{label}**: {value_str}\n{dod_arrow} 日环比: {dod_text} | {wow_arrow} 周同比: {wow_text}"
    
    def _get_severity_display(self, severity: str) -> str:
        """获取严重程度显示文本"""
        severity_map = {
            'critical': '🔴 严重',
            'high': '🟠 高',
            'medium': '🟡 中',
            'low': '🟢 低'
        }
        return severity_map.get(severity, '🟡 中')
    
    def _send_message(self, webhook_url: str, message_data: Dict[str, Any]) -> bool:
        """发送消息到Lark"""
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                webhook_url,
                headers=headers,
                json=message_data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # 检查Lark API响应
            result = response.json()
            if result.get('code') == 0:
                self.logger.info(f"消息发送成功: {webhook_url}")
                return True
            else:
                self.logger.error(f"Lark API返回错误: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"HTTP请求失败: {e}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            return False
    
    def test_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """测试Webhook连接"""
        try:
            test_message = {
                "msg_type": "text",
                "content": {
                    "text": f"🎯 App监控系统连接测试\n时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            
            success = self._send_message(webhook_url, test_message)
            
            return {
                'success': success,
                'message': '测试成功' if success else '测试失败',
                'webhook_url': webhook_url,
                'test_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'测试异常: {str(e)}',
                'webhook_url': webhook_url,
                'test_time': timezone.now().isoformat()
            }