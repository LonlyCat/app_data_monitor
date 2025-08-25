import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.db.models import QuerySet
from ..models import DataRecord
import logging

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """数据分析引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def calculate_growth_rates(self, current_data: Dict[str, Any], app_id: int, date: datetime) -> Dict[str, float]:
        """
        计算增长率
        
        Args:
            current_data: 当前数据 {'downloads': 100, 'sessions': 50, ...}
            app_id: App ID
            date: 当前数据日期
            
        Returns:
            包含各种增长率的字典
        """
        try:
            # 获取历史数据
            historical_data = self._get_historical_data(app_id, date)
            
            growth_rates = {
                'downloads_dod': 0.0,  # 下载量日环比
                'downloads_wow': 0.0,  # 下载量周同比
                'sessions_dod': 0.0,   # 会话数日环比
                'sessions_wow': 0.0,   # 会话数周同比
                'deletions_dod': 0.0,  # 卸载量日环比
                'deletions_wow': 0.0,  # 卸载量周同比
                'unique_devices_dod': 0.0,  # 独立设备数日环比
                'unique_devices_wow': 0.0,  # 独立设备数周同比
                # 下载来源增长率
                'downloads_app_store_search_dod': 0.0,
                'downloads_app_store_search_wow': 0.0,
                'downloads_web_referrer_dod': 0.0,
                'downloads_web_referrer_wow': 0.0,
                'downloads_app_referrer_dod': 0.0,
                'downloads_app_referrer_wow': 0.0,
            }
            
            # 计算日环比 (DOD - Day over Day)
            yesterday_data = historical_data.get('yesterday')
            if yesterday_data:
                growth_rates['downloads_dod'] = self._calculate_percentage_change(
                    yesterday_data.get('downloads', 0),
                    current_data.get('downloads', 0)
                )
                growth_rates['sessions_dod'] = self._calculate_percentage_change(
                    yesterday_data.get('sessions', 0),
                    current_data.get('sessions', 0)
                )
                growth_rates['deletions_dod'] = self._calculate_percentage_change(
                    yesterday_data.get('deletions', 0),
                    current_data.get('deletions', 0)
                )
                growth_rates['unique_devices_dod'] = self._calculate_percentage_change(
                    yesterday_data.get('unique_devices', 0) or 0,
                    current_data.get('unique_devices', 0) or 0
                )
                # 下载来源DOD计算
                growth_rates['downloads_app_store_search_dod'] = self._calculate_percentage_change(
                    yesterday_data.get('downloads_app_store_search', 0),
                    current_data.get('downloads_app_store_search', 0)
                )
                growth_rates['downloads_web_referrer_dod'] = self._calculate_percentage_change(
                    yesterday_data.get('downloads_web_referrer', 0),
                    current_data.get('downloads_web_referrer', 0)
                )
                growth_rates['downloads_app_referrer_dod'] = self._calculate_percentage_change(
                    yesterday_data.get('downloads_app_referrer', 0),
                    current_data.get('downloads_app_referrer', 0)
                )
            
            # 计算周同比 (WOW - Week over Week)
            last_week_data = historical_data.get('last_week')
            if last_week_data:
                growth_rates['downloads_wow'] = self._calculate_percentage_change(
                    last_week_data.get('downloads', 0),
                    current_data.get('downloads', 0)
                )
                growth_rates['sessions_wow'] = self._calculate_percentage_change(
                    last_week_data.get('sessions', 0),
                    current_data.get('sessions', 0)
                )
                growth_rates['deletions_wow'] = self._calculate_percentage_change(
                    last_week_data.get('deletions', 0),
                    current_data.get('deletions', 0)
                )
                growth_rates['unique_devices_wow'] = self._calculate_percentage_change(
                    last_week_data.get('unique_devices', 0) or 0,
                    current_data.get('unique_devices', 0) or 0
                )
                # 下载来源WOW计算
                growth_rates['downloads_app_store_search_wow'] = self._calculate_percentage_change(
                    last_week_data.get('downloads_app_store_search', 0),
                    current_data.get('downloads_app_store_search', 0)
                )
                growth_rates['downloads_web_referrer_wow'] = self._calculate_percentage_change(
                    last_week_data.get('downloads_web_referrer', 0),
                    current_data.get('downloads_web_referrer', 0)
                )
                growth_rates['downloads_app_referrer_wow'] = self._calculate_percentage_change(
                    last_week_data.get('downloads_app_referrer', 0),
                    current_data.get('downloads_app_referrer', 0)
                )
            
            self.logger.info(f"计算增长率完成 - App ID: {app_id}, Date: {date}, Growth: {growth_rates}")
            return growth_rates
            
        except Exception as e:
            self.logger.error(f"计算增长率失败: {e}")
            return {}
    
    def _get_historical_data(self, app_id: int, current_date: datetime) -> Dict[str, Optional[Dict]]:
        """获取历史对比数据"""
        try:
            # 昨天的数据
            yesterday = current_date - timedelta(days=1)
            yesterday_record = DataRecord.objects.filter(
                app_id=app_id, 
                date=yesterday.date()
            ).first()
            
            # 一周前的数据
            last_week = current_date - timedelta(days=7)
            last_week_record = DataRecord.objects.filter(
                app_id=app_id, 
                date=last_week.date()
            ).first()
            
            return {
                'yesterday': {
                    'downloads': yesterday_record.downloads,
                    'sessions': yesterday_record.sessions,
                    'deletions': yesterday_record.deletions,
                    'unique_devices': yesterday_record.unique_devices,
                    'downloads_app_store_search': yesterday_record.downloads_app_store_search,
                    'downloads_web_referrer': yesterday_record.downloads_web_referrer,
                    'downloads_app_referrer': yesterday_record.downloads_app_referrer,
                    'downloads_app_store_browse': yesterday_record.downloads_app_store_browse,
                    'downloads_institutional': yesterday_record.downloads_institutional,
                    'downloads_other': yesterday_record.downloads_other
                } if yesterday_record else None,
                'last_week': {
                    'downloads': last_week_record.downloads,
                    'sessions': last_week_record.sessions,
                    'deletions': last_week_record.deletions,
                    'unique_devices': last_week_record.unique_devices,
                    'downloads_app_store_search': last_week_record.downloads_app_store_search,
                    'downloads_web_referrer': last_week_record.downloads_web_referrer,
                    'downloads_app_referrer': last_week_record.downloads_app_referrer,
                    'downloads_app_store_browse': last_week_record.downloads_app_store_browse,
                    'downloads_institutional': last_week_record.downloads_institutional,
                    'downloads_other': last_week_record.downloads_other
                } if last_week_record else None
            }
            
        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            return {'yesterday': None, 'last_week': None}
    
    def _calculate_percentage_change(self, old_value: float, new_value: float) -> float:
        """计算百分比变化"""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        
        change = ((new_value - old_value) / old_value) * 100
        return round(change, 2)
    
    def analyze_trend(self, app_id: int, days: int = 30, metric: str = 'downloads') -> Dict[str, Any]:
        """
        分析趋势
        
        Args:
            app_id: App ID
            days: 分析天数
            metric: 指标名称 ('downloads', 'sessions', 'deletions', 'unique_devices')
            
        Returns:
            趋势分析结果
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 获取历史数据
            records = DataRecord.objects.filter(
                app_id=app_id,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')
            
            if not records:
                return {'trend': 'insufficient_data', 'confidence': 0}
            
            # 转换为DataFrame进行分析
            data = []
            for record in records:
                data.append({
                    'date': record.date,
                    'value': getattr(record, metric, 0)
                })
            
            df = pd.DataFrame(data)
            
            if len(df) < 3:
                return {'trend': 'insufficient_data', 'confidence': 0}
            
            # 使用线性回归分析趋势
            df['date_numeric'] = pd.to_numeric(pd.to_datetime(df['date']))
            correlation = df['date_numeric'].corr(df['value'])
            
            # 计算移动平均
            df['ma7'] = df['value'].rolling(window=min(7, len(df))).mean()
            
            # 判断趋势
            if correlation > 0.3:
                trend = 'increasing'
            elif correlation < -0.3:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # 计算置信度
            confidence = min(abs(correlation) * 100, 100)
            
            # 计算统计信息
            stats = {
                'mean': df['value'].mean(),
                'std': df['value'].std(),
                'min': df['value'].min(),
                'max': df['value'].max(),
                'latest': df['value'].iloc[-1] if not df.empty else 0,
                'change_from_start': self._calculate_percentage_change(
                    df['value'].iloc[0], df['value'].iloc[-1]
                ) if len(df) >= 2 else 0
            }
            
            return {
                'trend': trend,
                'confidence': round(confidence, 2),
                'correlation': round(correlation, 4),
                'stats': stats,
                'data_points': len(df)
            }
            
        except Exception as e:
            self.logger.error(f"趋势分析失败: {e}")
            return {'trend': 'error', 'confidence': 0, 'error': str(e)}
    
    def generate_insights(self, app_id: int, current_data: Dict[str, Any], growth_rates: Dict[str, float]) -> List[str]:
        """
        生成数据洞察
        
        Args:
            app_id: App ID
            current_data: 当前数据
            growth_rates: 增长率数据
            
        Returns:
            洞察列表
        """
        insights = []
        
        try:
            # 下载量洞察
            downloads_dod = growth_rates.get('downloads_dod', 0)
            if downloads_dod > 50:
                insights.append(f"📈 下载量日环比大幅增长 {downloads_dod:.1f}%")
            elif downloads_dod < -30:
                insights.append(f"📉 下载量日环比显著下降 {downloads_dod:.1f}%")
            elif downloads_dod > 10:
                insights.append(f"📊 下载量日环比稳定增长 {downloads_dod:.1f}%")
            
            # 会话数洞察
            sessions_dod = growth_rates.get('sessions_dod', 0)
            if sessions_dod > 30:
                insights.append(f"🚀 活跃度显著提升，会话数增长 {sessions_dod:.1f}%")
            elif sessions_dod < -20:
                insights.append(f"⚠️ 用户活跃度下降，会话数减少 {sessions_dod:.1f}%")
            
            # 卸载量洞察
            deletions_dod = growth_rates.get('deletions_dod', 0)
            if deletions_dod > 50:
                insights.append(f"⚠️ 卸载量大幅增长 {deletions_dod:.1f}%，需要关注用户流失")
            elif deletions_dod < -30:
                insights.append(f"👍 卸载量显著降低 {deletions_dod:.1f}%，用户留存改善")
            elif deletions_dod > 20:
                insights.append(f"📊 卸载量有所增长 {deletions_dod:.1f}%")
            
            # 独立设备数洞察
            unique_devices_dod = growth_rates.get('unique_devices_dod', 0)
            if unique_devices_dod > 25:
                insights.append(f"📱 活跃设备数显著增长 {unique_devices_dod:.1f}%")
            elif unique_devices_dod < -15:
                insights.append(f"📉 活跃设备数下降 {unique_devices_dod:.1f}%")
            elif unique_devices_dod > 10:
                insights.append(f"📊 活跃设备数稳定增长 {unique_devices_dod:.1f}%")
            
            # 趋势洞察
            downloads_trend = self.analyze_trend(app_id, days=7, metric='downloads')
            if downloads_trend['trend'] == 'increasing' and downloads_trend['confidence'] > 70:
                insights.append("📈 过去一周下载量呈持续上升趋势")
            elif downloads_trend['trend'] == 'decreasing' and downloads_trend['confidence'] > 70:
                insights.append("📉 过去一周下载量呈持续下降趋势")
            
            # 卸载量趋势洞察
            deletions_trend = self.analyze_trend(app_id, days=7, metric='deletions')
            if deletions_trend['trend'] == 'increasing' and deletions_trend['confidence'] > 70:
                insights.append("⚠️ 过去一周卸载量持续上升，需要关注")
            elif deletions_trend['trend'] == 'decreasing' and deletions_trend['confidence'] > 70:
                insights.append("✅ 过去一周卸载量持续下降，用户留存良好")
            
            # 下载来源洞察
            app_store_search_dod = growth_rates.get('downloads_app_store_search_dod', 0)
            web_referrer_dod = growth_rates.get('downloads_web_referrer_dod', 0)
            app_referrer_dod = growth_rates.get('downloads_app_referrer_dod', 0)
            
            # App Store搜索流量洞察
            if app_store_search_dod > 30:
                insights.append(f"🔍 App Store搜索下载大幅增长 {app_store_search_dod:.1f}%，搜索优化效果显著")
            elif app_store_search_dod < -30:
                insights.append(f"📉 App Store搜索下载下降 {app_store_search_dod:.1f}%，建议优化ASO")
            
            # 外部推荐流量洞察
            if web_referrer_dod > 50:
                insights.append(f"🌐 网页推荐下载激增 {web_referrer_dod:.1f}%，外部推广效果良好")
            elif app_referrer_dod > 50:
                insights.append(f"📱 应用推荐下载激增 {app_referrer_dod:.1f}%，交叉推广策略有效")
            
            # 流量来源多元化分析
            total_downloads = current_data.get('downloads', 0)
            if total_downloads > 0:
                app_store_search_ratio = (current_data.get('downloads_app_store_search', 0) / total_downloads) * 100
                external_ratio = ((current_data.get('downloads_web_referrer', 0) + 
                                 current_data.get('downloads_app_referrer', 0)) / total_downloads) * 100
                
                if app_store_search_ratio > 80:
                    insights.append(f"⚠️ {app_store_search_ratio:.1f}%下载来自App Store搜索，流量来源过于集中")
                elif external_ratio > 30:
                    insights.append(f"🎯 {external_ratio:.1f}%下载来自外部推荐，流量来源多元化良好")
            
            # 如果没有明显洞察，添加基础信息
            if not insights:
                insights.append("📊 数据波动在正常范围内")
            
            return insights[:5]  # 最多返回5个洞察
            
        except Exception as e:
            self.logger.error(f"生成洞察失败: {e}")
            return ["⚠️ 数据分析过程中出现异常"]
    
    def format_report_data(self, app_name: str, current_data: Dict[str, Any], 
                          growth_rates: Dict[str, float], insights: List[str], 
                          data_date: datetime) -> Dict[str, Any]:
        """
        格式化报告数据
        
        Args:
            app_name: App名称
            current_data: 当前数据
            growth_rates: 增长率
            insights: 洞察列表
            data_date: 数据日期
            
        Returns:
            格式化后的报告数据
        """
        return {
            'app_name': app_name,
            'date': data_date.strftime('%Y-%m-%d'),
            'metrics': {
                'downloads': {
                    'value': current_data.get('downloads', 0),
                    'dod_change': growth_rates.get('downloads_dod', 0),
                    'wow_change': growth_rates.get('downloads_wow', 0)
                },
                'sessions': {
                    'value': current_data.get('sessions', 0),
                    'dod_change': growth_rates.get('sessions_dod', 0),
                    'wow_change': growth_rates.get('sessions_wow', 0)
                },
                'deletions': {
                    'value': current_data.get('deletions', 0),
                    'dod_change': growth_rates.get('deletions_dod', 0),
                    'wow_change': growth_rates.get('deletions_wow', 0)
                },
                'unique_devices': {
                    'value': current_data.get('unique_devices', 0) or 0,
                    'dod_change': growth_rates.get('unique_devices_dod', 0),
                    'wow_change': growth_rates.get('unique_devices_wow', 0)
                },
                # 下载来源细分数据
                'source_breakdown': {
                    'app_store_search': {
                        'value': current_data.get('downloads_app_store_search', 0),
                        'dod_change': growth_rates.get('downloads_app_store_search_dod', 0),
                        'wow_change': growth_rates.get('downloads_app_store_search_wow', 0)
                    },
                    'web_referrer': {
                        'value': current_data.get('downloads_web_referrer', 0),
                        'dod_change': growth_rates.get('downloads_web_referrer_dod', 0),
                        'wow_change': growth_rates.get('downloads_web_referrer_wow', 0)
                    },
                    'app_referrer': {
                        'value': current_data.get('downloads_app_referrer', 0),
                        'dod_change': growth_rates.get('downloads_app_referrer_dod', 0),
                        'wow_change': growth_rates.get('downloads_app_referrer_wow', 0)
                    },
                    'app_store_browse': current_data.get('downloads_app_store_browse', 0),
                    'institutional': current_data.get('downloads_institutional', 0),
                    'other': current_data.get('downloads_other', 0)
                }
            },
            'insights': insights,
            'summary': self._generate_summary(current_data, growth_rates)
        }
    
    def _generate_summary(self, current_data: Dict[str, Any], growth_rates: Dict[str, float]) -> str:
        """生成数据摘要"""
        downloads = current_data.get('downloads', 0)
        sessions = current_data.get('sessions', 0)
        deletions = current_data.get('deletions', 0)
        downloads_dod = growth_rates.get('downloads_dod', 0)
        sessions_dod = growth_rates.get('sessions_dod', 0)
        deletions_dod = growth_rates.get('deletions_dod', 0)
        
        # 判断整体表现
        if downloads_dod > 10 and sessions_dod > 10 and deletions_dod <= 5:
            performance = "表现优异"
        elif downloads_dod > 0 and sessions_dod > 0 and deletions_dod <= 10:
            performance = "稳步增长"
        elif downloads_dod < -10 or sessions_dod < -10 or deletions_dod > 20:
            performance = "需要关注"
        else:
            performance = "基本稳定"
        
        return f"数据{performance}，下载量 {downloads:,}（{downloads_dod:+.1f}%），会话数 {sessions:,}（{sessions_dod:+.1f}%），卸载量 {deletions:,}（{deletions_dod:+.1f}%）"