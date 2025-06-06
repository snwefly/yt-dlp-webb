"""
统一错误处理模块
"""

import logging
import traceback
from functools import wraps
from flask import jsonify, request, current_app
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class AppError(Exception):
    """应用自定义异常基类"""
    
    def __init__(self, message: str, code: int = 500, details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(AppError):
    """验证错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 400, details)

class NotFoundError(AppError):
    """资源未找到错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 404, details)

class AuthenticationError(AppError):
    """认证错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 401, details)

class PermissionError(AppError):
    """权限错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 403, details)

class ExternalServiceError(AppError):
    """外部服务错误"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, 502, details)

def format_error_response(error: Union[Exception, AppError], include_traceback: bool = False) -> Dict[str, Any]:
    """格式化错误响应"""
    
    if isinstance(error, AppError):
        response = {
            'success': False,
            'error': {
                'message': error.message,
                'code': error.code,
                'type': error.__class__.__name__
            }
        }
        
        if error.details:
            response['error']['details'] = error.details
            
    else:
        # 处理其他异常
        response = {
            'success': False,
            'error': {
                'message': str(error),
                'code': 500,
                'type': error.__class__.__name__
            }
        }
    
    # 在开发模式下包含堆栈跟踪
    if include_traceback and current_app and current_app.debug:
        response['error']['traceback'] = traceback.format_exc()
    
    return response

def handle_api_error(func):
    """API 错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError as e:
            logger.warning(f"API错误 [{e.code}]: {e.message}", extra={'details': e.details})
            return jsonify(format_error_response(e)), e.code
        except Exception as e:
            logger.error(f"未处理的API错误: {str(e)}", exc_info=True)
            error_response = format_error_response(e, include_traceback=True)
            return jsonify(error_response), 500
    
    return wrapper

def handle_service_error(func):
    """服务层错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError:
            # 重新抛出应用错误
            raise
        except Exception as e:
            logger.error(f"服务层错误: {str(e)}", exc_info=True)
            # 将未知错误包装为应用错误
            raise AppError(f"服务处理失败: {str(e)}", 500, {'original_error': str(e)})
    
    return wrapper

def log_and_return_error(message: str, code: int = 500, details: Optional[Dict] = None, 
                        log_level: str = 'error') -> Dict[str, Any]:
    """记录日志并返回错误响应（用于不抛出异常的场景）"""
    
    error_data = {
        'message': message,
        'code': code,
        'details': details or {}
    }
    
    # 记录日志
    log_func = getattr(logger, log_level.lower(), logger.error)
    log_func(f"错误 [{code}]: {message}", extra={'details': details})
    
    return {
        'success': False,
        'error': error_data
    }

def register_error_handlers(app):
    """注册全局错误处理器"""
    
    @app.errorhandler(AppError)
    def handle_app_error(error):
        """处理应用自定义错误"""
        logger.warning(f"应用错误 [{error.code}]: {error.message}", extra={'details': error.details})
        return jsonify(format_error_response(error)), error.code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """处理404错误"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': {
                    'message': '请求的资源不存在',
                    'code': 404,
                    'type': 'NotFound'
                }
            }), 404
        # 对于非API请求，返回HTML页面
        return error
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理500错误"""
        logger.error(f"内部服务器错误: {str(error)}", exc_info=True)
        
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': {
                    'message': '内部服务器错误',
                    'code': 500,
                    'type': 'InternalServerError'
                }
            }), 500
        # 对于非API请求，返回HTML页面
        return error
    
    logger.info("✅ 全局错误处理器已注册")

# 便捷函数
def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功响应"""
    response = {
        'success': True,
        'message': message
    }
    
    if data is not None:
        response['data'] = data
    
    return response

def paginated_response(items: list, total: int, page: int, per_page: int, 
                      message: str = "获取成功") -> Dict[str, Any]:
    """创建分页响应"""
    return {
        'success': True,
        'message': message,
        'data': {
            'items': items,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
        }
    }
