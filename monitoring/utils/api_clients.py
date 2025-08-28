from re import I
import requests
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import logging
from requests import PreparedRequest
from functools import wraps
import random
import math
from io import StringIO
try:
    import numpy as np  # 用于数值清洗
except Exception:  # pragma: no cover
    np = None

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, delay_base: float = 1.0, backoff_factor: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay_base: 基础延迟时间（秒）
        backoff_factor: 退避因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    # 添加速率限制 - 在非首次尝试时增加延迟
                    if attempt > 0:
                        delay = delay_base * (backoff_factor ** (attempt - 1))
                        # 添加随机抖动以避免同时重试
                        jitter = random.uniform(0, delay * 0.1)
                        sleep_time = delay + jitter
                        logger.info(f"重试 {func.__name__} (尝试 {attempt + 1}/{max_retries + 1})，等待 {sleep_time:.2f} 秒...")
                        time.sleep(sleep_time)
                    
                    return func(*args, **kwargs)
                    
                except requests.exceptions.HTTPError as e:
                    last_exception = e
                    # 对于某些错误码不进行重试
                    if e.response and e.response.status_code in [400, 401, 403, 404]:
                        raise
                    # 对于500错误，继续重试
                    if attempt < max_retries:
                        logger.warning(f"{func.__name__} 失败 (HTTP {e.response.status_code if e.response else 'N/A'})，准备重试...")
                    else:
                        raise
                        
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"{func.__name__} 请求失败: {e}，准备重试...")
                    else:
                        raise
                        
                except Exception as e:
                    # 对于非请求相关的异常，不重试
                    raise
                    
            # 如果所有重试都失败了
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def _sanitize_for_json(obj: Any) -> Any:
    """递归清洗对象，移除 NaN/Inf，并将 numpy 标量转为原生类型，确保可安全写入 JSONField。
    """
    # 基本类型
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    # 浮点数处理（含 nan/inf）
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    # numpy 标量处理
    if np is not None:
        if isinstance(obj, (np.floating,)):
            val = float(obj)
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
    # 容器类型
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    # 其他不可序列化类型，转字符串以保底
    try:
        return str(obj)
    except Exception:
        return None


class AppStoreConnectClient:
    """Apple App Store Connect API客户端"""
    
    BASE_URL = "https://api.appstoreconnect.apple.com/v1"

    INSTALL_REPORT_NAME = "App Downloads Standard"
    INSTALL_DETAILED_REPORT_NAME = "App Store Installation and Deletion Standard"  # 用于获取删除事件
    SESSION_REPORT_NAME = "App Sessions Standard"
    
    def __init__(self, issuer_id: str, key_id: str, private_key: str):
        self.issuer_id = issuer_id
        self.key_id = key_id
        # 处理以环境变量形式存储的私钥中可能存在的转义换行符
        self.private_key = private_key.replace('\\n', '\n') if private_key else private_key
        self._token = None
        self._token_expires = None
    
    def _generate_jwt_token(self) -> str:
        """生成JWT令牌"""
        now = int(time.time())
        expires = now + 1200  # 20分钟有效期
        
        payload = {
            'iss': self.issuer_id,
            'exp': expires,
            'aud': 'appstoreconnect-v1',
            'iat': now
        }
        
        headers = {
            'kid': self.key_id,
            'typ': 'JWT',
            'alg': 'ES256'
        }
        
        token = jwt.encode(
            payload, 
            self.private_key, 
            algorithm='ES256',
            headers=headers
        )
        logger.info(f"生成JWT令牌: {token}")
        # 兼容PyJWT不同版本的返回类型
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        self._token = token
        self._token_expires = expires
        return token
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        # 检查token是否过期
        if not self._token or (self._token_expires and time.time() >= self._token_expires - 60):
            self._generate_jwt_token()
        
        return {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    @retry_on_failure(max_retries=3, delay_base=1.0, backoff_factor=2.0)
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """发起API请求"""
        base_url = f"{self.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        # 通过PreparedRequest安全拼接查询参数，确保日志中可见最终URL
        prepared = PreparedRequest()
        prepared.prepare_url(base_url, params or {})
        final_url = prepared.url
        
        try:
            logger.debug(f"GET 请求URL: {final_url}")
            response = requests.get(final_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # 更详细的错误日志，便于定位403/401等问题
            status = response.status_code if 'response' in locals() and response is not None else 'N/A'
            body = None
            try:
                body = response.json()
            except Exception:
                body = response.text if 'response' in locals() and response is not None else ''
            logger.error(f"App Store Connect API请求失败: HTTP {status} | URL: {final_url} | 响应: {body}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"App Store Connect API请求失败: {e}")
            raise
    
    def get_app_info(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """根据Bundle ID获取App信息"""
        try:
            params = {
                'filter[bundleId]': bundle_id,
                'fields[apps]': 'name,bundleId,primaryLocale'
            }
            
            response = self._make_request('apps', params)
            apps = response.get('data', [])
            
            if apps:
                return apps[0]
            return None
            
        except Exception as e:
            logger.error(f"获取App信息失败 (Bundle ID: {bundle_id}): {e}")
            return None
    
    def get_analytics_data(self, bundle_id: str, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取Apple App Store Connect分析数据
        
        Args:
            bundle_id: App的Bundle ID
            target_date: 指定获取数据的处理日期(processingDate)，默认为None获取所有可用数据
        
        Apple Analytics API工作流程:
        1. 首先获取App ID
        2. 检查是否已有ONGOING类型的分析报告请求
        3. 如果没有，创建ONGOING类型的分析报告请求 (POST /v1/analyticsReportRequests)
        4. 获取报告并处理数据
        
        注意：ONGOING类型的报告会自动每天生成新数据
        """
        try:
            # 1. 获取App ID
            app_info = self.get_app_info(bundle_id)
            if not app_info:
                raise Exception(f"无法找到Bundle ID为 {bundle_id} 的App")
            
            app_id = app_info['id']
            logger.info(f"找到App ID: {app_id} for Bundle: {bundle_id}")
            
            # 2. 检查现有的分析报告请求
            existing_request = self._get_existing_analytics_request(app_id)
            
            if existing_request:
                logger.info(f"找到现有的分析报告请求: {existing_request['id']}")
                report_request_id = existing_request['id']
            else:
                # 3. 创建新的分析报告请求
                report_request_id = self._create_analytics_report_request(app_id)
                if not report_request_id:
                    raise Exception("创建分析报告请求失败")
            
            # 4. 获取报告信息
            report_data = self._get_analytics_report_info(report_request_id, target_date)
            
            # 5. 构建返回数据，保持向后兼容
            result = _sanitize_for_json({
                'downloads': 0,
                'sessions': 0,
                'raw_data': report_data  # 保留完整的原始数据
            })
            
            # 从处理后的数据中提取下载量和会话数
            if 'install_report' in report_data and 'processed_data' in report_data['install_report']:
                processed = report_data['install_report']['processed_data']
                result['downloads'] = processed.get('total_installs', 0)  # 仅首次下载
                result['updates'] = processed.get('total_updates', 0)      # 更新数量
                result['reinstalls'] = processed.get('total_reinstalls', 0)  # 重装数量
                result['deletions'] = processed.get('total_deletions', 0)
                
                # 提取下载来源分析数据
                logger.debug(f"开始提取source type数据，install_report结构: {list(report_data['install_report'].keys()) if 'install_report' in report_data else 'NO_INSTALL_REPORT'}")
                source_data = self._extract_source_type_data_from_processed(report_data['install_report'])
                logger.info(f"Source type数据提取结果: {source_data}")
                result.update(source_data)
            
            if 'session_report' in report_data and 'processed_data' in report_data['session_report']:
                processed = report_data['session_report']['processed_data']
                result['sessions'] = processed.get('total_sessions', 0)
                result['unique_devices'] = processed.get('total_unique_devices', 0)
            
            return result
            
        except requests.exceptions.HTTPError as http_err:
            # 输出更友好的错误信息
            status = http_err.response.status_code if getattr(http_err, 'response', None) is not None else 'N/A'
            detail = None
            try:
                err_json = http_err.response.json() if http_err.response is not None else None
                # App Store Connect常见错误结构: {'errors': [{ 'status': '403', 'code': 'FORBIDDEN...', 'title': '...', 'detail': '...' }]}
                if err_json and isinstance(err_json, dict) and err_json.get('errors'):
                    first = err_json['errors'][0]
                    title = first.get('title')
                    detail = first.get('detail') or title
                else:
                    detail = http_err.response.text if http_err.response is not None else str(http_err)
            except Exception:
                detail = str(http_err)
            logger.error(f"Apple Analytics调接口HTTP失败: {status} | {detail}")
            return {
                'downloads': 0,
                'sessions': 0,
                'error': f"HTTP {status}: {detail}",
                'status_code': status
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取Apple分析数据失败 (Bundle: {bundle_id}): {error_msg}")
            return {
                'downloads': 0, 
                'sessions': 0, 
                'error': error_msg,
                'raw_response': None
            }

    def _get_existing_analytics_request(self, app_id: str) -> Optional[Dict[str, Any]]:
        """获取现有的分析报告请求"""
        try:
            # 使用 GET /v1/apps/{id}/analyticsReportRequests 获取现有报告请求
            params = {
                'filter[accessType]': 'ONGOING',
                'fields[analyticsReportRequests]': 'accessType,stoppedDueToInactivity',
                # 精简参数，避免不必要的include导致权限问题
                'limit': 1
            }
            
            response = self._make_request(f'apps/{app_id}/analyticsReportRequests', params)
            
            if 'data' in response and response['data']:
                for request in response['data']:
                    # 检查是否为活跃的ONGOING请求
                    if (request.get('attributes', {}).get('accessType') == 'ONGOING' and
                        not request.get('attributes', {}).get('stoppedDueToInactivity', False)):
                        return request
            
            return None
            
        except Exception as e:
            logger.error(f"获取现有分析报告请求失败: {e}")
            return None

    def _create_analytics_report_request(self, app_id: str) -> Optional[str]:
        """创建分析报告请求"""
        try:
            # 根据官方OpenAPI规范构建请求数据
            request_data = {
                "data": {
                    "type": "analyticsReportRequests",
                    "attributes": {
                        # 使用ONGOING类型，苹果会自动每天生成新报告
                        "accessType": "ONGOING"
                    },
                    "relationships": {
                        "app": {
                            "data": {
                                "type": "apps",
                                "id": app_id
                            }
                        }
                    }
                }
            }
            
            # 发送POST请求创建报告
            response = self._make_post_request('analyticsReportRequests', request_data)
            
            if 'data' in response:
                report_request_id = response['data']['id']
                logger.info(f"创建分析报告请求成功: {report_request_id}")
                return report_request_id
            
            return None
            
        except Exception as e:
            logger.error(f"创建分析报告请求失败: {e}")
            return None

    def _get_analytics_report_info(self, report_request_id: str, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取分析报告数据
        
        Args:
            report_request_id: 报告请求ID
            target_date: 指定获取数据的处理日期(processingDate)，用于过滤特定日期的报告
        """
        try:
            # 获取报告请求关联的报告 - 包含两个安装报告和会话报告
            params = {
                'filter[name]': f'{self.INSTALL_REPORT_NAME},{self.INSTALL_DETAILED_REPORT_NAME},{self.SESSION_REPORT_NAME}'
            }
            
            reports_response = self._make_request(f'analyticsReportRequests/{report_request_id}/reports', params)
            logger.debug(f"获取报告请求关联的报告数据: {reports_response}")
            
            if 'data' not in reports_response:
                logger.warning("获取分析报告失败, 数据非法")
                return {}
            
            report_list = reports_response['data']

            # 处理每个报告
            data = {}
            
            # 处理标准安装报告 (主要用于下载统计)
            install_report = next((report for report in report_list if report['attributes']['name'] == self.INSTALL_REPORT_NAME), None)
            install_instances = None
            if install_report:
                install_instances = self._get_report_instances(install_report['id'], target_date)
                if install_instances:
                    data['install_report'] = {
                        'report_id': install_report['id'],
                        'instances': install_instances,
                        'processed_data': self._process_install_report_data(install_instances, target_date, 'standard')
                    }
            
            # 处理详细安装报告 (主要用于删除事件统计)
            install_detailed_report = next((report for report in report_list if report['attributes']['name'] == self.INSTALL_DETAILED_REPORT_NAME), None)
            if install_detailed_report:
                detailed_instances = self._get_report_instances(install_detailed_report['id'], target_date)
                if detailed_instances:
                    data['install_detailed_report'] = {
                        'report_id': install_detailed_report['id'],
                        'instances': detailed_instances,
                        'processed_data': self._process_install_report_data(detailed_instances, target_date, 'detailed')
                    }
                    
                    # 合并删除数据到主安装报告中
                    if 'install_report' in data and 'processed_data' in data['install_report']:
                        detailed_data = data['install_detailed_report']['processed_data']
                        main_data = data['install_report']['processed_data']
                        
                        # 合并删除统计
                        main_data['total_deletions'] = detailed_data.get('total_deletions', 0)
                        
                        # 不再合并source type数据，只使用标准报告的source type数据
                        # 这样确保source type统计逻辑与下载量统计保持一致
                        detailed_source_totals = detailed_data.get('source_type_totals', {})
                        main_source_totals = main_data.get('source_type_totals', {})
                        logger.info(f"标准报告source type: {sum(main_source_totals.values())}, 详细报告source type: {sum(detailed_source_totals.values())} (详细报告数据不使用)")
                        
                        # 合并每日删除数据
                        if 'daily_data' in detailed_data:
                            for date_key, daily_stats in detailed_data['daily_data'].items():
                                if date_key in main_data['daily_data']:
                                    main_data['daily_data'][date_key]['deletions'] = daily_stats.get('deletions', 0)
                                else:
                                    # 如果标准报告中没有这个日期，添加删除数据
                                    main_data['daily_data'][date_key] = {
                                        'installs': 0, 'updates': 0, 'reinstalls': 0,
                                        'deletions': daily_stats.get('deletions', 0),
                                        'records_count': daily_stats.get('records_count', 0)
                                    }
                        
                        logger.info(f"已合并详细报告删除数据 - 总删除数: {main_data['total_deletions']}")
            
            # 处理会话报告
            session_report = next((report for report in report_list if report['attributes']['name'] == self.SESSION_REPORT_NAME), None)
            if session_report:
                instances = self._get_report_instances(session_report['id'], target_date)
                if instances:
                    data['session_report'] = {
                        'report_id': session_report['id'],
                        'instances': instances,
                        'processed_data': self._process_session_report_data(instances, target_date)
                    }
            
            return data
            
        except Exception as e:
            logger.error(f"获取分析报告数据失败: {e}")
            return {}

    def _get_report_instances(self, report_id: str, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """获取报告实例数据
        
        Args:
            report_id: 报告ID
            target_date: 指定获取数据的处理日期(processingDate)
        """
        try:
            # 获取报告相关实例数据：GET /v1/analyticsReports/{id}/instances
            params = {
                'filter[granularity]': 'DAILY'
            }
            
            # 如果指定了目标日期，添加processingDate过滤器
            if target_date:
                # 获取 target_date + 1 天的日期，因为苹果报告是第二天生成的
                target_date_str = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
                params['filter[processingDate]'] = target_date_str
                logger.info(f"在instances端点使用processingDate过滤器: {target_date_str}")
            
            instances_response = self._make_request(f'analyticsReports/{report_id}/instances', params)
            
            if 'data' in instances_response:
                return instances_response['data']
            else:
                return None
            
        except Exception as e:
            logger.error(f"获取报告实例数据失败: {e}")
            return None

    def _extract_source_type_data_from_processed(self, install_report: Dict[str, Any]) -> Dict[str, int]:
        """从已处理的安装报告中提取下载来源类型数据
        
        Args:
            install_report: 安装报告数据，包含instances_with_segments
            
        Returns:
            Dict[str, int]: 包含各种来源类型下载量的字典
        """
        # 初始化所有source type字段为0
        source_type_fields = {
            'downloads_app_store_search': 0,
            'downloads_web_referrer': 0,
            'downloads_app_referrer': 0,
            'downloads_app_store_browse': 0,
            'downloads_institutional': 0,
            'downloads_other': 0,
        }
        
        try:
            # 从processed_data中获取已聚合的source type数据
            processed_data = install_report.get('processed_data', {})
            logger.debug(f"processed_data结构: {list(processed_data.keys()) if processed_data else 'EMPTY'}")
            source_type_totals = processed_data.get('source_type_totals', {})
            logger.debug(f"source_type_totals: {source_type_totals}")
            
            if source_type_totals and sum(source_type_totals.values()) > 0:
                # 直接使用已聚合的数据
                source_type_fields['downloads_app_store_search'] = source_type_totals.get('app_store_search', 0)
                source_type_fields['downloads_web_referrer'] = source_type_totals.get('web_referrer', 0)
                source_type_fields['downloads_app_referrer'] = source_type_totals.get('app_referrer', 0)
                source_type_fields['downloads_app_store_browse'] = source_type_totals.get('app_store_browse', 0)
                source_type_fields['downloads_institutional'] = source_type_totals.get('institutional_purchase', 0)
                source_type_fields['downloads_other'] = source_type_totals.get('other', 0)
                
                logger.debug(f"使用已聚合的source type数据: {source_type_totals}")
            else:
                # 备用方案：从instances_with_segments中提取（保持向后兼容）
                instances_with_segments = processed_data.get('instances_with_segments', [])
                logger.debug(f"备用方案：从 {len(instances_with_segments)} 个实例的segments中提取source type数据")
                
                # 遍历每个实例的segments
                for instance_data in instances_with_segments:
                    segments_data = instance_data.get('segments', {})
                    if 'segments' in segments_data:
                        segments = segments_data['segments']
                        
                        for segment in segments:
                            csv_data = segment.get('csv_data', {})
                            summary = csv_data.get('summary', {})
                            by_source_type = summary.get('by_source_type', {})
                            
                            if by_source_type:
                                # 累加各种来源类型的下载量
                                source_type_fields['downloads_app_store_search'] += by_source_type.get('App Store search', 0)
                                source_type_fields['downloads_web_referrer'] += by_source_type.get('Web referrer', 0)
                                source_type_fields['downloads_app_referrer'] += by_source_type.get('App referrer', 0)
                                source_type_fields['downloads_app_store_browse'] += by_source_type.get('App Store browse', 0)
                                source_type_fields['downloads_institutional'] += by_source_type.get('Institutional purchase', 0)
                                source_type_fields['downloads_other'] += by_source_type.get('Unavailable', 0) + by_source_type.get('other', 0)
                                
                                logger.debug(f"从段提取source type数据: {by_source_type}")
            
            # 记录提取结果
            total_source_downloads = sum(source_type_fields.values())
            if total_source_downloads > 0:
                logger.info(f"成功提取下载来源数据 - App Store搜索: {source_type_fields['downloads_app_store_search']}, "
                          f"网页推荐: {source_type_fields['downloads_web_referrer']}, "
                          f"应用推荐: {source_type_fields['downloads_app_referrer']}, "
                          f"App Store浏览: {source_type_fields['downloads_app_store_browse']}, "
                          f"机构采购: {source_type_fields['downloads_institutional']}, "
                          f"其他: {source_type_fields['downloads_other']}, "
                          f"总计: {total_source_downloads}")
            else:
                logger.warning("未提取到任何source type数据，所有字段将保持为0")
                
        except Exception as e:
            logger.error(f"从处理后的安装报告中提取source type数据失败: {e}")
        
        return source_type_fields
    
    def _get_instance_segments_data(self, instance_id: str, report_type: str) -> Dict[str, Any]:
        """获取实例段数据
        
        Args:
            instance_id: 实例ID
            report_type: 报告类型 ('install' 或 'session')
        """
        try:
            # 使用正确的端点：GET /v1/analyticsReportInstances/{id}/segments
            segments_response = self._make_request(f'analyticsReportInstances/{instance_id}/segments')
            
            segments_data = []
            if 'data' in segments_response:
                for segment in segments_response['data']:
                    segment_info = {
                        'id': segment['id'],
                        'attributes': segment.get('attributes', {}),
                    }
                    
                    # 获取段的下载URL并下载CSV数据
                    if 'attributes' in segment and 'url' in segment['attributes']:
                        segment_url = segment['attributes']['url']
                        # 根据报告类型使用不同的解析方法
                        if report_type == 'install':
                            segment_info['csv_data'] = self._parse_install_csv_data(segment_url)
                        elif report_type == 'session':
                            segment_info['csv_data'] = self._parse_session_csv_data(segment_url)
                        else:
                            segment_info['csv_data'] = self._parse_generic_csv_data(segment_url)
                    
                    segments_data.append(segment_info)
            
            return {
                'instance_id': instance_id,
                'segments': segments_data,
                'segment_count': len(segments_data)
            }
            
        except Exception as e:
            logger.error(f"获取实例段数据失败: {e}")
            return {
                'instance_id': instance_id,
                'segments': [],
                'error': str(e)
            }

    @retry_on_failure(max_retries=3, delay_base=1.0, backoff_factor=2.0)
    def _make_post_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发起POST请求"""
        url = f"{self.BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            logger.debug(f"POST 请求URL: {url} | Body: {data}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            status = response.status_code if 'response' in locals() and response is not None else 'N/A'
            body = None
            try:
                body = response.json()
            except Exception:
                body = response.text if 'response' in locals() and response is not None else ''
            logger.error(f"App Store Connect POST请求失败: HTTP {status} | URL: {url} | 请求体: {data} | 响应: {body}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"App Store Connect POST请求失败: {e}")
            raise
    
    def _download_csv_data(self, url: str) -> str:
        """下载CSV数据"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"下载CSV数据失败: {e}")
            return ""
    
    def _parse_install_csv_data(self, csv_url: str) -> Dict[str, Any]:
        """解析安装报告CSV数据"""
        try:
            if not csv_url:
                return {'error': 'No CSV URL provided'}
            
            import pandas as pd
            
            # 下载并解析CSV数据 - 使用制表符作为分隔符
            df = pd.read_csv(csv_url, compression='gzip', sep='\t')
            
            logger.info(f"安装报告CSV列名: {df.columns.tolist()}")
            logger.info(f"安装报告总行数: {len(df)}")
            logger.info(f"安装报告前3行数据预览: \n{df.head(3).to_string()}")
            
            # 检查是否有Source Type列，以及该列的数据情况
            if 'Source Type' in df.columns:
                source_type_values = df['Source Type'].value_counts()
                logger.info(f"Source Type列数据分布: {source_type_values.to_dict()}")
            else:
                logger.warning(f"⚠️ CSV中缺少'Source Type'列！可用列: {df.columns.tolist()}")
            
            # 保留原始数据结构
            data = {
                'columns': df.columns.tolist(),
                'row_count': len(df),
                'date_range': {
                    'start': df['Date'].min() if 'Date' in df.columns else None,
                    'end': df['Date'].max() if 'Date' in df.columns else None
                },
                'raw_data': df.to_dict('records'),  # 保留所有原始数据以便写入Lark
                'summary': {}
            }
            
            # 计算汇总数据 - 根据Event类型筛选
            if 'Event' in df.columns and 'Counts' in df.columns:
                # 安装数据：Event为'Install'
                install_df = df[df['Event'] == 'Install'] if 'Install' in df['Event'].values else df
                data['summary']['total_installs'] = int(install_df['Counts'].sum())
                data['summary']['daily_average'] = float(install_df.groupby('Date')['Counts'].sum().mean()) if not install_df.empty else 0
                
                # 删除数据：Event为'Delete'
                delete_df = df[df['Event'] == 'Delete'] if 'Delete' in df['Event'].values else pd.DataFrame()
                data['summary']['total_deletions'] = int(delete_df['Counts'].sum()) if not delete_df.empty else 0
                
                # 按设备类型分组统计
                if 'Device' in df.columns:
                    device_stats = install_df.groupby('Device')['Counts'].sum().to_dict()
                    data['summary']['by_device'] = {k: int(v) for k, v in device_stats.items()}
                
                # 按地区分组统计
                if 'Territory' in df.columns:
                    territory_stats = install_df.groupby('Territory')['Counts'].sum().nlargest(10).to_dict()
                    data['summary']['top_territories'] = {k: int(v) for k, v in territory_stats.items()}
                
                # 按来源类型分组统计（仅统计首次下载Install事件）
                if 'Source Type' in df.columns:
                    # 检查首次下载数据中的Source Type情况
                    logger.debug(f"首次下载数据中的Source Type唯一值: {install_df['Source Type'].unique().tolist()}")
                    logger.debug(f"首次下载数据条数: {len(install_df)}")
                    
                    source_type_stats = install_df.groupby('Source Type')['Counts'].sum().to_dict()
                    logger.debug(f"原始source_type_stats: {source_type_stats}")
                    
                    data['summary']['by_source_type'] = {
                        'App Store search': int(source_type_stats.get('App Store search', 0)),
                        'Web referrer': int(source_type_stats.get('Web referrer', 0)),
                        'App referrer': int(source_type_stats.get('App referrer', 0)),
                        'App Store browse': int(source_type_stats.get('App Store browse', 0)),
                        'Institutional purchase': int(source_type_stats.get('Institutional purchase', 0)),
                        'Unavailable': int(source_type_stats.get('Unavailable', 0)),
                        'other': sum(int(v) for k, v in source_type_stats.items() 
                                   if k not in ['App Store search', 'Web referrer', 'App referrer', 
                                              'App Store browse', 'Institutional purchase', 'Unavailable'])
                    }
                    logger.info(f"下载来源分析: {data['summary']['by_source_type']}")
                else:
                    logger.warning(f"CSV数据中没有'Source Type'列，可用列: {df.columns.tolist()}")
                
                logger.info(f"安装报告汇总 - 总安装: {data['summary']['total_installs']}, 总删除: {data['summary']['total_deletions']}")
            
            logger.debug(f"安装报告CSV解析完成 - 行数: {data['row_count']}, 列: {data['columns']}")
            
            # 递归清洗，避免 NaN/Inf 导致 JSON 入库失败
            return _sanitize_for_json(data)
            
        except Exception as e:
            logger.error(f"解析安装报告CSV数据失败: {e}")
            return {'error': str(e)}
    
    def _parse_session_csv_data(self, csv_url: str) -> Dict[str, Any]:
        """解析会话报告CSV数据"""
        try:
            if not csv_url:
                return {'error': 'No CSV URL provided'}
            
            import pandas as pd
            
            # 下载并解析CSV数据 - 使用制表符作为分隔符
            df = pd.read_csv(csv_url, compression='gzip', sep='\t')
            
            logger.info(f"会话报告CSV列名: {df.columns.tolist()}")
            logger.info(f"会话报告前3行数据预览: \n{df.head(3).to_string()}")
            
            # 保留原始数据结构
            data = {
                'columns': df.columns.tolist(),
                'row_count': len(df),
                'date_range': {
                    'start': df['Date'].min() if 'Date' in df.columns else None,
                    'end': df['Date'].max() if 'Date' in df.columns else None
                },
                'raw_data': df.to_dict('records'),  # 保留所有原始数据以便写入Lark
                'summary': {}
            }
            
            # 计算汇总数据
            if 'Sessions' in df.columns:
                data['summary']['total_sessions'] = int(df['Sessions'].sum())
                data['summary']['daily_average'] = float(df.groupby('Date')['Sessions'].sum().mean()) if not df.empty else 0
                
                # 按设备类型分组统计
                if 'Device' in df.columns:
                    device_stats = df.groupby('Device')['Sessions'].sum().to_dict()
                    data['summary']['by_device'] = {k: int(v) for k, v in device_stats.items()}
                
                # 按地区分组统计
                if 'Territory' in df.columns:
                    territory_stats = df.groupby('Territory')['Sessions'].sum().nlargest(10).to_dict()
                    data['summary']['top_territories'] = {k: int(v) for k, v in territory_stats.items()}
            
            if 'Unique Devices' in df.columns:
                # 独立设备数需要特殊处理 - 这里简单使用最大值作为近似
                # 注意：跨日期的真实去重需要更复杂的逻辑
                data['summary']['total_unique_devices'] = int(df['Unique Devices'].sum())
                data['summary']['max_daily_unique_devices'] = int(df['Unique Devices'].max())
                
            logger.info(f"会话报告汇总 - 总会话: {data['summary'].get('total_sessions', 0)}, 独立设备: {data['summary'].get('total_unique_devices', 0)}")
            
            logger.debug(f"会话报告CSV解析完成 - 行数: {data['row_count']}, 列: {data['columns']}")
            
            # 递归清洗，避免 NaN/Inf 导致 JSON 入库失败
            return _sanitize_for_json(data)
            
        except Exception as e:
            logger.error(f"解析会话报告CSV数据失败: {e}")
            return {'error': str(e)}
    
    def _parse_generic_csv_data(self, csv_url: str) -> Dict[str, Any]:
        """通用CSV数据解析（作为后备方案）"""
        try:
            if not csv_url:
                return {'error': 'No CSV URL provided'}
            
            import pandas as pd
            
            # 尝试使用制表符作为分隔符
            df = pd.read_csv(csv_url, compression='gzip', sep='\t')
            
            logger.info(f"通用CSV解析 - 列名: {df.columns.tolist()}")
            logger.info(f"通用CSV解析 - 前3行: \n{df.head(3).to_string()}")
            
            return _sanitize_for_json({
                'columns': df.columns.tolist(),
                'row_count': len(df),
                'raw_data': df.to_dict('records'),
                'head_preview': df.head().to_dict('records')
            })
            
        except Exception as e:
            logger.error(f"解析通用CSV数据失败: {e}")
            return {'error': str(e)}
    
    def _process_install_report_data(self, instances: List[Dict[str, Any]], target_date: Optional[datetime] = None, report_type: str = 'standard') -> Dict[str, Any]:
        """处理安装报告实例数据
        
        Args:
            instances: 报告实例列表
            target_date: 指定目标日期，用于按日期分组聚合数据
            report_type: 报告类型 ('standard'=标准报告重点统计下载, 'detailed'=详细报告重点统计删除)
        """
        try:
            processed_data = {
                'total_installs': 0,  # 仅统计 First-time download
                'total_updates': 0,   # Manual update 事件统计
                'total_reinstalls': 0,  # Auto-download 事件统计
                'total_deletions': 0,
                'daily_data': {},  # 按日期分组的数据
                'instances_with_segments': [],
                'failed_instances': 0,
                'total_instances': len(instances),
                'target_date_filter': target_date.strftime('%Y-%m-%d') if target_date else None,
                # 添加source type汇总数据
                'source_type_totals': {
                    'app_store_search': 0,
                    'web_referrer': 0,
                    'app_referrer': 0,
                    'app_store_browse': 0,
                    'institutional_purchase': 0,
                    'other': 0
                }
            }
            
            for idx, instance in enumerate(instances):
                instance_id = instance.get('id')
                if instance_id:
                    # 在非首次请求时添加延迟，避免过快的API调用
                    if idx > 0:
                        delay = 0.5 + random.uniform(0, 0.2)  # 0.5-0.7秒延迟
                        logger.debug(f"处理下一个实例前等待 {delay:.2f} 秒...")
                        time.sleep(delay)
                    
                    # 获取该实例的段数据
                    segments_data = self._get_instance_segments_data(instance_id, 'install')
                    
                    instance_info = {
                        'instance_id': instance_id,
                        'attributes': instance.get('attributes', {}),
                        'segments': segments_data
                    }
                    
                    # 汇总数据 - 按日期分组
                    if segments_data and 'segments' in segments_data:
                        for segment in segments_data['segments']:
                            if 'csv_data' in segment and 'raw_data' in segment['csv_data']:
                                raw_data = segment['csv_data']['raw_data']
                                
                                # 按日期分组处理原始数据
                                for record in raw_data:
                                    record_date = record.get('Date')
                                    if record_date:
                                        # 初始化日期数据
                                        if record_date not in processed_data['daily_data']:
                                            processed_data['daily_data'][record_date] = {
                                                'installs': 0,      # First-time download
                                                'updates': 0,       # Manual update
                                                'reinstalls': 0,    # Auto-download
                                                'deletions': 0,
                                                'records_count': 0
                                            }
                                        
                                        # 累加数据
                                        event_type = record.get('Event', '')
                                        download_type = record.get('Download Type', '')
                                        counts = record.get('Counts', 0)
                                        
                                        if isinstance(counts, (int, float)) and not math.isnan(counts):
                                            counts_int = int(counts)
                                            
                                            # 根据报告类型采用不同的处理策略
                                            if report_type == 'detailed':
                                                # 详细报告：主要关注删除事件，有Event字段
                                                if event_type == 'Delete':
                                                    processed_data['daily_data'][record_date]['deletions'] += counts_int
                                                elif event_type == 'Install':
                                                    # 详细报告中的安装事件也记录，但权重较低
                                                    if download_type == 'First-time download':
                                                        processed_data['daily_data'][record_date]['installs'] += counts_int
                                                    elif download_type == 'Manual update':
                                                        processed_data['daily_data'][record_date]['updates'] += counts_int
                                                    elif download_type in ['Auto-download', 'Auto-update']:
                                                        processed_data['daily_data'][record_date]['reinstalls'] += counts_int
                                                    elif download_type in ['Restore', 'Redownload']:
                                                        processed_data['daily_data'][record_date]['reinstalls'] += counts_int
                                            else:
                                                # 标准报告：主要关注下载事件，数据更准确
                                                # 兼容两种数据格式：
                                                # 1. 有Event字段的格式 (Event: Install/Delete + Download Type)
                                                # 2. 无Event字段的格式 (直接使用Download Type分类)
                                                
                                                if event_type == 'Delete':
                                                    # 标准报告一般没有删除数据，但有的话也记录
                                                    processed_data['daily_data'][record_date]['deletions'] += counts_int
                                                elif event_type == 'Install' or not event_type:
                                                    # Install事件 或 无Event字段时默认为安装相关事件
                                                    # 根据 Download Type 分类统计
                                                    if download_type == 'First-time download':
                                                        processed_data['daily_data'][record_date]['installs'] += counts_int
                                                    elif download_type == 'Manual update':
                                                        processed_data['daily_data'][record_date]['updates'] += counts_int
                                                    elif download_type in ['Auto-download', 'Auto-update']:
                                                        # Auto-download: 自动下载重装
                                                        # Auto-update: 自动更新(也算重装的一种)
                                                        processed_data['daily_data'][record_date]['reinstalls'] += counts_int
                                                    elif download_type in ['Restore', 'Redownload']:
                                                        # Restore/Redownload: 恢复下载,归类为重装
                                                        processed_data['daily_data'][record_date]['reinstalls'] += counts_int
                                                    elif download_type:
                                                        # 记录其他未分类的下载类型
                                                        logger.debug(f"未分类的下载类型: {download_type}, 计数: {counts_int}")
                                                        # 暂时归类为重装，避免数据丢失
                                                        processed_data['daily_data'][record_date]['reinstalls'] += counts_int
                                        
                                        processed_data['daily_data'][record_date]['records_count'] += 1
                                        
                                        # 只统计首次下载的source type数据，确保与下载量统计逻辑一致
                                        # 仅在标准报告中统计source type，避免重复累加
                                        should_count_source_type = False
                                        
                                        if report_type == 'standard':
                                            # 仅标准报告统计source type
                                            if event_type:
                                                # 有Event字段：只统计Install + First-time download
                                                if event_type == 'Install' and download_type == 'First-time download':
                                                    should_count_source_type = True
                                            else:
                                                # 没有Event字段：只统计First-time download
                                                if download_type == 'First-time download':
                                                    should_count_source_type = True
                                        
                                        # 只有在目标日期筛选生效时才统计对应日期的source type
                                        if should_count_source_type and target_date:
                                            target_date_str = target_date.strftime('%Y-%m-%d')
                                            # 只统计目标日期的source type数据
                                            if record_date == target_date_str:
                                                source_type = record.get('Source Type', '')
                                                if source_type:
                                                    # 根据source type类型累加到对应的分类中
                                                    if source_type == 'App Store search':
                                                        processed_data['source_type_totals']['app_store_search'] += counts_int
                                                    elif source_type == 'Web referrer':
                                                        processed_data['source_type_totals']['web_referrer'] += counts_int
                                                    elif source_type == 'App referrer':
                                                        processed_data['source_type_totals']['app_referrer'] += counts_int
                                                    elif source_type == 'App Store browse':
                                                        processed_data['source_type_totals']['app_store_browse'] += counts_int
                                                    elif source_type == 'Institutional purchase':
                                                        processed_data['source_type_totals']['institutional_purchase'] += counts_int
                                                    elif source_type in ['Unavailable', 'Other']:
                                                        processed_data['source_type_totals']['other'] += counts_int
                                                    else:
                                                        # 其他未知类型归入other
                                                        processed_data['source_type_totals']['other'] += counts_int
                                                        logger.debug(f"未知source type: {source_type}, 计数: {counts_int}")
                                        elif should_count_source_type and not target_date:
                                            # 如果没有指定目标日期，统计所有日期的source type
                                            source_type = record.get('Source Type', '')
                                            if source_type:
                                                # 根据source type类型累加到对应的分类中
                                                if source_type == 'App Store search':
                                                    processed_data['source_type_totals']['app_store_search'] += counts_int
                                                elif source_type == 'Web referrer':
                                                    processed_data['source_type_totals']['web_referrer'] += counts_int
                                                elif source_type == 'App referrer':
                                                    processed_data['source_type_totals']['app_referrer'] += counts_int
                                                elif source_type == 'App Store browse':
                                                    processed_data['source_type_totals']['app_store_browse'] += counts_int
                                                elif source_type == 'Institutional purchase':
                                                    processed_data['source_type_totals']['institutional_purchase'] += counts_int
                                                elif source_type in ['Unavailable', 'Other']:
                                                    processed_data['source_type_totals']['other'] += counts_int
                                                else:
                                                    # 其他未知类型归入other
                                                    processed_data['source_type_totals']['other'] += counts_int
                                                    logger.debug(f"未知source type: {source_type}, 计数: {counts_int}")
                                
                                # 兼容性处理：从summary中获取删除数据（source type数据不再从summary获取）
                                if 'summary' in segment['csv_data']:
                                    summary = segment['csv_data']['summary']
                                    # 注意：这里的 total_installs 包含所有类型的 Install，我们现在分开统计
                                    # processed_data['total_installs'] += summary.get('total_installs', 0)
                                    processed_data['total_deletions'] += summary.get('total_deletions', 0)
                    elif segments_data and 'error' in segments_data:
                        logger.warning(f"实例 {instance_id} 数据获取失败，跳过但继续处理其他实例")
                        processed_data['failed_instances'] += 1
                    
                    processed_data['instances_with_segments'].append(instance_info)
            
            # 如果指定了目标日期，只返回该日期的数据作为总数
            if target_date and processed_data['daily_data']:
                target_date_str = target_date.strftime('%Y-%m-%d')
                if target_date_str in processed_data['daily_data']:
                    daily_stats = processed_data['daily_data'][target_date_str]
                    processed_data['total_installs'] = daily_stats['installs']
                    processed_data['total_updates'] = daily_stats['updates']
                    processed_data['total_reinstalls'] = daily_stats['reinstalls']
                    processed_data['total_deletions'] = daily_stats['deletions']
                    logger.info(f"使用目标日期 {target_date_str} 的数据 - 安装: {daily_stats['installs']}, 更新: {daily_stats['updates']}, 重装: {daily_stats['reinstalls']}, 删除: {daily_stats['deletions']}")
                else:
                    logger.warning(f"目标日期 {target_date_str} 没有找到数据，可用日期: {list(processed_data['daily_data'].keys())}")
                    processed_data['total_installs'] = 0
                    processed_data['total_updates'] = 0
                    processed_data['total_reinstalls'] = 0
                    processed_data['total_deletions'] = 0
            else:
                # 如果没有指定目标日期，汇总所有日期的数据
                for daily_stats in processed_data['daily_data'].values():
                    processed_data['total_installs'] += daily_stats['installs']
                    processed_data['total_updates'] += daily_stats['updates']
                    processed_data['total_reinstalls'] += daily_stats['reinstalls']
                    processed_data['total_deletions'] += daily_stats['deletions']
            
            if processed_data['failed_instances'] > 0:
                logger.warning(f"安装报告有 {processed_data['failed_instances']}/{processed_data['total_instances']} 个实例获取失败")
            
            # 记录source type汇总结果
            source_totals = processed_data['source_type_totals']
            total_source_downloads = sum(source_totals.values())
            if total_source_downloads > 0:
                logger.info(f"Source Type汇总(仅首次下载) - App Store搜索: {source_totals['app_store_search']}, "
                          f"网页推荐: {source_totals['web_referrer']}, "
                          f"应用推荐: {source_totals['app_referrer']}, "
                          f"App Store浏览: {source_totals['app_store_browse']}, "
                          f"机构采购: {source_totals['institutional_purchase']}, "
                          f"其他: {source_totals['other']}, "
                          f"总计: {total_source_downloads}")
                
                # 验证数据一致性：source type总数应该等于首次下载总数
                total_installs = processed_data.get('total_installs', 0)
                if total_source_downloads == total_installs:
                    logger.info(f"✓ Source Type数据一致性检查通过: {total_source_downloads} == {total_installs}")
                else:
                    logger.warning(f"⚠️ Source Type数据不一致: source_total={total_source_downloads}, installs={total_installs}")
            else:
                logger.warning("Source Type数据汇总为0，可能CSV中没有Source Type列或数据为空")
            
            logger.info(f"安装报告({report_type})处理完成 - 总安装(首次): {processed_data['total_installs']}, 总更新: {processed_data['total_updates']}, 总重装: {processed_data['total_reinstalls']}, 总删除: {processed_data['total_deletions']}, 日期分组数: {len(processed_data['daily_data'])}")
            return processed_data
            
        except Exception as e:
            logger.error(f"处理安装报告数据失败: {e}")
            return {'error': str(e)}
    
    def _process_session_report_data(self, instances: List[Dict[str, Any]], target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """处理会话报告实例数据
        
        Args:
            instances: 报告实例列表
            target_date: 指定目标日期，用于按日期分组聚合数据
        """
        try:
            processed_data = {
                'total_sessions': 0,
                'total_unique_devices': 0,
                'daily_data': {},  # 按日期分组的数据
                'instances_with_segments': [],
                'failed_instances': 0,
                'total_instances': len(instances),
                'target_date_filter': target_date.strftime('%Y-%m-%d') if target_date else None
            }
            
            for idx, instance in enumerate(instances):
                instance_id = instance.get('id')
                if instance_id:
                    # 在非首次请求时添加延迟，避免过快的API调用
                    if idx > 0:
                        delay = 0.5 + random.uniform(0, 0.2)  # 0.5-0.7秒延迟
                        logger.debug(f"处理下一个实例前等待 {delay:.2f} 秒...")
                        time.sleep(delay)
                    
                    # 获取该实例的段数据
                    segments_data = self._get_instance_segments_data(instance_id, 'session')
                    
                    instance_info = {
                        'instance_id': instance_id,
                        'attributes': instance.get('attributes', {}),
                        'segments': segments_data
                    }
                    
                    # 汇总数据 - 按日期分组
                    if segments_data and 'segments' in segments_data:
                        for segment in segments_data['segments']:
                            if 'csv_data' in segment and 'raw_data' in segment['csv_data']:
                                raw_data = segment['csv_data']['raw_data']
                                
                                # 按日期分组处理原始数据
                                for record in raw_data:
                                    record_date = record.get('Date')
                                    if record_date:
                                        # 初始化日期数据
                                        if record_date not in processed_data['daily_data']:
                                            processed_data['daily_data'][record_date] = {
                                                'sessions': 0,
                                                'unique_devices': 0,
                                                'records_count': 0
                                            }
                                        
                                        # 累加数据
                                        sessions = record.get('Sessions', 0)
                                        unique_devices = record.get('Unique Devices', 0)
                                        
                                        if isinstance(sessions, (int, float)) and not math.isnan(sessions):
                                            processed_data['daily_data'][record_date]['sessions'] += int(sessions)
                                        
                                        if isinstance(unique_devices, (int, float)) and not math.isnan(unique_devices):
                                            processed_data['daily_data'][record_date]['unique_devices'] += int(unique_devices)
                                        
                                        processed_data['daily_data'][record_date]['records_count'] += 1
                                
                                # 兼容性处理：保持总数统计
                                if 'summary' in segment['csv_data']:
                                    summary = segment['csv_data']['summary']
                                    processed_data['total_sessions'] += summary.get('total_sessions', 0)
                                    processed_data['total_unique_devices'] += summary.get('total_unique_devices', 0)
                    elif segments_data and 'error' in segments_data:
                        logger.warning(f"实例 {instance_id} 数据获取失败，跳过但继续处理其他实例")
                        processed_data['failed_instances'] += 1
                    
                    processed_data['instances_with_segments'].append(instance_info)
            
            # 如果指定了目标日期，只返回该日期的数据作为总数
            if target_date and processed_data['daily_data']:
                target_date_str = target_date.strftime('%Y-%m-%d')
                if target_date_str in processed_data['daily_data']:
                    daily_stats = processed_data['daily_data'][target_date_str]
                    processed_data['total_sessions'] = daily_stats['sessions']
                    processed_data['total_unique_devices'] = daily_stats['unique_devices']
                    logger.info(f"使用目标日期 {target_date_str} 的数据 - 会话: {daily_stats['sessions']}, 独立设备: {daily_stats['unique_devices']}")
                else:
                    logger.warning(f"目标日期 {target_date_str} 没有找到数据，可用日期: {list(processed_data['daily_data'].keys())}")
                    processed_data['total_sessions'] = 0
                    processed_data['total_unique_devices'] = 0
            
            if processed_data['failed_instances'] > 0:
                logger.warning(f"会话报告有 {processed_data['failed_instances']}/{processed_data['total_instances']} 个实例获取失败")
            
            logger.info(f"会话报告处理完成 - 总会话: {processed_data['total_sessions']}, 独立设备: {processed_data['total_unique_devices']}, 日期分组数: {len(processed_data['daily_data'])}")
            return processed_data
            
        except Exception as e:
            logger.error(f"处理会话报告数据失败: {e}")
            return {'error': str(e)}


class GooglePlayConsoleClient:
    """Google Play Console API客户端"""
    
    BASE_URL = "https://www.googleapis.com/androidpublisher/v3"
    
    def __init__(self, service_account_info: Dict[str, Any], bucket_name: Optional[str] = None, project_id: Optional[str] = None):
        self.service_account_info = service_account_info
        self._access_token = None
        self._token_expires = None
        # GCS 相关配置
        self._gcs_bucket_name = bucket_name
        self._gcs_project_id = project_id
        self._gcs_client = None
    
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        if self._access_token and self._token_expires and time.time() < self._token_expires - 60:
            return self._access_token
        
        # 使用Service Account获取访问令牌
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        
        try:
            credentials = service_account.Credentials.from_service_account_info(
                self.service_account_info,
                scopes=['https://www.googleapis.com/auth/androidpublisher']
            )
            
            credentials.refresh(Request())
            
            self._access_token = credentials.token
            self._token_expires = time.time() + 3600  # 1小时有效期
            
            return self._access_token
            
        except Exception as e:
            logger.error(f"获取Google Play访问令牌失败: {e}")
            raise

    def _get_gcs_client(self):
        """获取或初始化 GCS 客户端"""
        if self._gcs_client is not None:
            return self._gcs_client
        try:
            # 使用只读存储权限
            from google.oauth2 import service_account
            from google.cloud import storage
            credentials = service_account.Credentials.from_service_account_info(
                self.service_account_info,
                scopes=['https://www.googleapis.com/auth/devstorage.read_only']
            )
            self._gcs_client = storage.Client(credentials=credentials, project=self._gcs_project_id)
            logger.info("已初始化Google Cloud Storage客户端")
            return self._gcs_client
        except Exception as e:
            logger.error(f"初始化GCS客户端失败: {e}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        token = self._get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """发起API请求"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Play Console API请求失败: {e}")
            raise

    def _find_overview_blob(self, package_name: str, target_date: datetime):
        """在GCS中查找指定月份的 overview CSV blob"""
        if not self._gcs_bucket_name:
            raise Exception("缺少GCS Bucket名称配置(gcs_bucket_name)")
        client = self._get_gcs_client()
        bucket = client.bucket(self._gcs_bucket_name)

        month_str = target_date.strftime('%Y%m')
        prefix = f"stats/installs/installs_{package_name}_{month_str}"
        logger.info(f"在GCS列举前缀: {prefix}")
        try:
            blobs = list(bucket.list_blobs(prefix=prefix))
        except Exception as e:
            logger.error(f"列举GCS对象失败: {e}")
            raise

        # 选择包含 overview 的CSV
        overview_blobs = [b for b in blobs if b.name.endswith('_overview.csv')]
        if not overview_blobs:
            # 兼容大小写或其他后缀
            overview_blobs = [b for b in blobs if 'overview' in b.name and b.name.endswith('.csv')]
        if not overview_blobs:
            names = [b.name for b in blobs]
            raise Exception(f"未找到overview报表，可用对象: {names}")

        # 一般只有一个，若多个则按更新日期取最新
        overview_blobs.sort(key=lambda b: b.updated or datetime.min, reverse=True)
        chosen = overview_blobs[0]
        logger.info(f"选定overview报表: {chosen.name}")
        return chosen

    def _download_blob_text(self, blob) -> str:
        """下载GCS对象并以文本返回，自动处理编码"""
        try:
            raw_bytes = blob.download_as_bytes()
            # 优先尝试UTF-16（Play导出常见编码）
            for enc in ['utf-16', 'utf-16le', 'utf-8-sig', 'utf-8', 'latin1']:
                try:
                    text = raw_bytes.decode(enc)
                    logger.debug(f"CSV编码识别成功: {enc}")
                    return text
                except Exception:
                    continue
            # 最后兜底
            text = raw_bytes.decode(errors='ignore')
            logger.warning("CSV编码无法精确识别，已忽略错误进行解码")
            return text
        except Exception as e:
            logger.error(f"下载overview CSV失败: {e}")
            raise

    def _parse_overview_csv(self, csv_text: str) -> Dict[str, Any]:
        """解析overview CSV，返回DataFrame字典信息"""
        try:
            import pandas as pd
            df = pd.read_csv(StringIO(csv_text))
            logger.info(f"Google安装overview列名: {df.columns.tolist()}")
            return {
                'columns': df.columns.tolist(),
                'row_count': len(df),
                'raw_data': df.to_dict('records')
            }
        except Exception as e:
            logger.error(f"解析overview CSV失败: {e}")
            raise
    
    def get_app_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """获取应用信息"""
        try:
            endpoint = f"applications/{package_name}"
            response = self._make_request(endpoint)
            return response
            
        except Exception as e:
            logger.error(f"获取Google Play应用信息失败 (Package: {package_name}): {e}")
            return None
    
    def get_statistics_data(self, package_name: str, target_date: datetime) -> Dict[str, Any]:
        """获取统计数据（改为从GCS下载overview CSV并解析每日新增下载量）"""
        try:
            # 1) 定位 overview 报表对象
            blob = self._find_overview_blob(package_name, target_date)
            # 2) 下载并解析 CSV
            csv_text = self._download_blob_text(blob)
            parsed = self._parse_overview_csv(csv_text)
    
            # 3) 提取目标日期的数据行
            rows = parsed.get('raw_data', [])
            date_key = target_date.strftime('%Y-%m-%d')
            downloads = 0
            deletions = 0
            matched_row = None
            def _parse_int(val):
                try:
                    if val is None:
                        return 0
                    if isinstance(val, (int, float)):
                        if math.isnan(val):
                            return 0
                        return int(val)
                    if isinstance(val, str):
                        s = val.replace(',', '').strip()
                        if s == '':
                            return 0
                        return int(float(s))
                    return 0
                except Exception:
                    return 0
            # 构建按日期的日度映射，便于回退到最近可用日期
            daily_map: Dict[str, Dict[str, int]] = {}
            for row in rows:
                # 兼容不同标题大小写或空格
                row_date = row.get('Date') or row.get('date')
                if isinstance(row_date, str):
                    d_key = row_date.strip()
                    # 日新增与卸载
                    d_downloads = _parse_int(row.get('Daily User Installs') or row.get('Daily user installs') or row.get('daily user installs'))
                    d_deletions = _parse_int(row.get('Daily User Uninstalls') or row.get('Daily user uninstalls') or row.get('daily user uninstalls'))
                    daily_map[d_key] = {
                        'downloads': d_downloads,
                        'deletions': d_deletions,
                    }
                if isinstance(row_date, str) and row_date.strip() == date_key:
                    matched_row = row
                    break

            if matched_row:
                # 优先使用 Daily User Installs 作为新增下载量
                downloads = _parse_int(matched_row.get('Daily User Installs') or matched_row.get('Daily user installs') or matched_row.get('daily user installs'))
                # 卸载量（可用于监控）
                deletions = _parse_int(matched_row.get('Daily User Uninstalls') or matched_row.get('Daily user uninstalls') or matched_row.get('daily user uninstalls'))
                effective_date = date_key
                logger.info(f"提取到 {effective_date} 的Google下载量: {downloads}，卸载量: {deletions}")
            else:
                # 回退到最近可用的日期（不晚于目标日期）
                logger.warning(f"overview中未找到日期 {date_key} 的数据，尝试回退到最近可用日期")
                # 找到 <= 目标日期的最近日期
                available_dates = []
                try:
                    available_dates = sorted([
                        d for d in daily_map.keys()
                        if d <= date_key
                    ])
                except Exception:
                    available_dates = sorted(list(daily_map.keys()))
                if available_dates:
                    effective_date = available_dates[-1]
                    fallback = daily_map.get(effective_date, {})
                    downloads = int(fallback.get('downloads', 0))
                    deletions = int(fallback.get('deletions', 0))
                    logger.info(f"使用最近可用日期 {effective_date} 的Google下载量: {downloads}，卸载量: {deletions}")
                else:
                    effective_date = None
                    logger.warning("overview中没有任何可用日期数据")

            # 4) 构建返回数据
            return {
                'downloads': downloads,
                'sessions': 0,  # Google Play暂无会话数据
                'sessions_available': False,
                'deletions': deletions,
                'effective_date': effective_date,
                'available_dates': sorted(list(daily_map.keys())),
                'daily_map': daily_map,
                'max_available_date': max(daily_map.keys()) if daily_map else None,
                'raw_response': {
                    'blob_name': getattr(blob, 'name', None),
                    'parsed_overview': parsed
                }
            }
        except Exception as e:
            logger.error(f"获取Google Play统计数据失败: {e}")
            return {'downloads': 0, 'sessions': 0, 'error': str(e)}


class APIClientFactory:
    """API客户端工厂"""
    
    @staticmethod
    def create_apple_client(config_data: Dict[str, Any]) -> AppStoreConnectClient:
        """创建Apple客户端"""
        return AppStoreConnectClient(
            issuer_id=config_data['issuer_id'],
            key_id=config_data['key_id'],
            private_key=config_data['private_key']
        )
    
    @staticmethod
    def create_google_client(config_data: Dict[str, Any]) -> GooglePlayConsoleClient:
        """创建Google客户端"""
        import json
        service_account_info = json.loads(config_data['service_account_key'])
        # 可选从配置中获取 GCS bucket 与 project
        bucket_name = config_data.get('gcs_bucket_name') or config_data.get('bucket_name')
        project_id = config_data.get('gcs_project_id') or config_data.get('project_id')
        return GooglePlayConsoleClient(service_account_info, bucket_name=bucket_name, project_id=project_id)