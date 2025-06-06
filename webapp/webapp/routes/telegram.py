"""
Telegram相关路由
"""
import logging
import hashlib
import hmac
import json
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from ..models import db, TelegramConfig
from ..core.telegram_notifier import get_telegram_notifier
from ..core.download_manager import get_download_manager

logger = logging.getLogger(__name__)

telegram_bp = Blueprint('telegram', __name__)

@telegram_bp.route('/')
@login_required
def telegram_dashboard():
    """Telegram主页面 - 重定向到设置页面"""
    return redirect(url_for('telegram.telegram_settings'))

@telegram_bp.route('/settings')
@login_required
def telegram_settings():
    """Telegram设置页面"""
    is_authenticated = current_user.is_authenticated
    user_data = current_user.username if is_authenticated else None
    is_admin = current_user.is_admin if is_authenticated else False
    
    return render_template('telegram/settings.html',
                         is_authenticated=is_authenticated,
                         current_user=user_data,
                         is_admin=is_admin)

@telegram_bp.route('/api/config', methods=['GET'])
@login_required
def get_telegram_config():
    """获取Telegram配置"""
    try:
        config = TelegramConfig.get_config()
        
        # 隐藏敏感信息
        config_data = {
            'enabled': config.enabled,
            'bot_token_configured': bool(config.bot_token),
            'chat_id_configured': bool(config.chat_id),
            'api_id_configured': bool(config.api_id),
            'api_hash_configured': bool(config.api_hash),
            'webhook_enabled': config.webhook_enabled,
            'push_mode': config.push_mode,
            'auto_download': config.auto_download,
            'file_size_limit_mb': config.file_size_limit_mb,
            'advanced_settings': config.get_advanced_settings()
        }
        
        # 管理员可以看到完整配置
        if current_user.is_admin:
            advanced_settings = config.get_advanced_settings()
            config_data.update({
                'bot_token': config.bot_token,
                'chat_id': config.chat_id,
                'api_id': config.api_id,
                'api_hash': config.api_hash,
                'webhook_secret': config.webhook_secret,
                'webhook_url': advanced_settings.get('webhook_url', '')
            })
        
        return jsonify({
            'success': True,
            'config': config_data
        })
        
    except Exception as e:
        logger.error(f'获取Telegram配置失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@telegram_bp.route('/api/config', methods=['POST'])
@login_required
def update_telegram_config():
    """更新Telegram配置"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.get_json()
        config = TelegramConfig.get_config()

        # 更新基础配置
        if 'bot_token' in data:
            config.bot_token = data['bot_token'].strip() if data['bot_token'] else None
        if 'chat_id' in data:
            config.chat_id = data['chat_id'].strip() if data['chat_id'] else None

        # 验证和更新 API ID/Hash
        if 'api_id' in data or 'api_hash' in data:
            api_id = data.get('api_id', '').strip() if data.get('api_id') else None
            api_hash = data.get('api_hash', '').strip() if data.get('api_hash') else None

            # 如果提供了任一个，就要验证两个都正确
            if api_id or api_hash:
                if not api_id or not api_hash:
                    return jsonify({
                        'success': False,
                        'error': 'API ID 和 API Hash 必须同时提供'
                    }), 400

                # 验证 API ID 格式（纯数字）
                if not api_id.isdigit():
                    return jsonify({
                        'success': False,
                        'error': 'API ID 必须是纯数字'
                    }), 400

                # 验证 API Hash 格式（32位十六进制）
                import re
                if not re.match(r'^[a-f0-9]{32}$', api_hash, re.IGNORECASE):
                    return jsonify({
                        'success': False,
                        'error': 'API Hash 必须是32位十六进制字符串'
                    }), 400

            config.api_id = api_id
            config.api_hash = api_hash
        if 'enabled' in data:
            config.enabled = bool(data['enabled'])
        if 'webhook_enabled' in data:
            config.webhook_enabled = bool(data['webhook_enabled'])
        if 'webhook_secret' in data:
            config.webhook_secret = data['webhook_secret'].strip() if data['webhook_secret'] else None
        # 处理 webhook_url - 保存到 advanced_settings
        if 'webhook_url' in data:
            advanced_settings = config.get_advanced_settings()
            advanced_settings['webhook_url'] = data['webhook_url'].strip() if data['webhook_url'] else None
            config.set_advanced_settings(advanced_settings)
        if 'push_mode' in data:
            config.push_mode = data['push_mode']
        if 'auto_download' in data:
            config.auto_download = bool(data['auto_download'])
        if 'file_size_limit_mb' in data:
            config.file_size_limit_mb = int(data['file_size_limit_mb'])

        # 更新高级设置
        if 'advanced_settings' in data:
            config.set_advanced_settings(data['advanced_settings'])

        db.session.commit()

        # 重新加载通知器配置
        telegram_notifier = get_telegram_notifier()
        telegram_notifier.reload_config()

        return jsonify({
            'success': True,
            'message': '配置已更新'
        })

    except Exception as e:
        logger.error(f'更新Telegram配置失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@telegram_bp.route('/api/test', methods=['POST'])
@login_required
def test_telegram():
    """测试Telegram连接"""
    try:
        # 获取请求数据，支持临时测试
        data = request.get_json() or {}

        # 如果提供了临时配置，使用临时配置进行测试
        if 'bot_token' in data and 'chat_id' in data:
            # 创建临时通知器实例
            from webapp.core.telegram_notifier import TelegramNotifier
            temp_notifier = TelegramNotifier()
            temp_notifier._bot_token = data['bot_token'].strip()
            temp_notifier._chat_id = data['chat_id'].strip()

            result = temp_notifier.test_connection()
        else:
            # 使用保存的配置进行测试
            telegram_notifier = get_telegram_notifier()
            result = telegram_notifier.test_connection()

        return jsonify(result)

    except Exception as e:
        logger.error(f'测试Telegram连接失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@telegram_bp.route('/api/test-message', methods=['POST'])
def test_message():
    """测试消息发送功能"""
    try:
        data = request.get_json()
        bot_token = data.get('bot_token')
        chat_id = data.get('chat_id')

        if not bot_token or not chat_id:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400

        # 创建测试消息
        from datetime import datetime
        test_message = f"""🧪 **YT-DLP 消息测试**

📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Bot Token: {bot_token[:10]}...
💬 Chat ID: {chat_id}

✅ 如果您收到这条消息，说明消息发送功能正常工作！

🔧 测试信息:
- 消息类型: Markdown 格式
- 字符数: {len('测试消息')} 字符

📝 下一步:
1. 测试文件推送功能
2. 测试 Webhook 自动下载
3. 向 Bot 发送视频链接测试完整流程
"""

        try:
            # 使用 TelegramNotifier 发送消息
            from webapp.core.telegram_notifier import TelegramNotifier

            # 创建临时通知器实例并设置临时配置
            notifier = TelegramNotifier()
            notifier._bot_token = bot_token
            notifier._chat_id = chat_id
            notifier._enabled = True

            # 从数据库获取 API ID 和 API Hash
            config = TelegramConfig.get_config()
            if config.api_id:
                notifier._api_id = config.api_id
            if config.api_hash:
                notifier._api_hash = config.api_hash

            print(f"🧪 开始测试消息发送...")
            logger.info(f"🧪 开始测试消息发送...")

            success = notifier.send_message(test_message)

            if success:
                logger.info(f'消息发送测试成功: {chat_id}')
                return jsonify({
                    'success': True,
                    'message': '消息发送测试成功！请检查您的 Telegram'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '消息发送失败，请检查 Bot Token 和 Chat ID'
                })

        except Exception as e:
            logger.error(f'消息发送测试失败: {e}')
            return jsonify({
                'success': False,
                'error': f'消息发送失败: {str(e)}'
            })

    except Exception as e:
        logger.error(f'消息发送测试失败: {e}')
        return jsonify({
            'success': False,
            'error': f'测试失败: {str(e)}'
        }), 500


@telegram_bp.route('/api/webhook-status', methods=['GET'])
def webhook_status():
    """检查Webhook状态"""
    try:
        config = TelegramConfig.get_config()

        if not config.is_configured():
            return jsonify({
                'success': False,
                'error': '请先配置 Bot Token 和 Chat ID'
            }), 400

        telegram_notifier = get_telegram_notifier()
        clean_token = telegram_notifier._get_clean_bot_token()

        # 获取Webhook信息
        import requests
        api_url = f"https://api.telegram.org/bot{clean_token}/getWebhookInfo"

        response = requests.get(api_url, timeout=30)
        result = response.json()

        if result.get('ok'):
            webhook_info = result.get('result', {})

            # 分析状态
            status_analysis = {
                'webhook_url': webhook_info.get('url', ''),
                'has_custom_certificate': webhook_info.get('has_custom_certificate', False),
                'pending_update_count': webhook_info.get('pending_update_count', 0),
                'last_error_date': webhook_info.get('last_error_date'),
                'last_error_message': webhook_info.get('last_error_message'),
                'max_connections': webhook_info.get('max_connections', 40),
                'allowed_updates': webhook_info.get('allowed_updates', []),
                'ip_address': webhook_info.get('ip_address'),
                'last_synchronization_error_date': webhook_info.get('last_synchronization_error_date')
            }

            # 配置状态
            config_status = {
                'webhook_enabled': config.webhook_enabled,
                'auto_download': config.auto_download,
                'push_mode': config.push_mode,
                'chat_id': config.chat_id,
                'has_webhook_secret': bool(config.webhook_secret)
            }

            # 问题诊断
            issues = []
            if not webhook_info.get('url'):
                issues.append('❌ Webhook URL 未设置')
            elif not config.webhook_enabled:
                issues.append('⚠️ Webhook 在配置中被禁用')

            if webhook_info.get('pending_update_count', 0) > 0:
                issues.append(f'⚠️ 有 {webhook_info.get("pending_update_count")} 个待处理的更新')

            if webhook_info.get('last_error_message'):
                issues.append(f'❌ 最近错误: {webhook_info.get("last_error_message")}')

            return jsonify({
                'success': True,
                'webhook_info': status_analysis,
                'config_status': config_status,
                'issues': issues,
                'recommendations': _get_webhook_recommendations(status_analysis, config_status)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'获取Webhook信息失败: {result.get("description", "未知错误")}'
            }), 400

    except Exception as e:
        logger.error(f'检查Webhook状态失败: {e}')
        return jsonify({
            'success': False,
            'error': f'检查失败: {str(e)}'
        }), 500

def _get_webhook_recommendations(webhook_info, config_status):
    """获取Webhook配置建议"""
    recommendations = []

    if not webhook_info['webhook_url']:
        recommendations.append('🔧 请先设置 Webhook URL')
    elif not config_status['webhook_enabled']:
        recommendations.append('🔧 请在配置中启用 Webhook')

    if webhook_info['pending_update_count'] > 10:
        recommendations.append('🔧 考虑清除待处理的更新')

    if webhook_info['last_error_message']:
        if 'timeout' in webhook_info['last_error_message'].lower():
            recommendations.append('🔧 服务器响应超时，检查服务器性能')
        elif 'connection' in webhook_info['last_error_message'].lower():
            recommendations.append('🔧 连接问题，检查网络和防火墙设置')
        elif 'certificate' in webhook_info['last_error_message'].lower():
            recommendations.append('🔧 SSL证书问题，确保使用有效的HTTPS证书')

    if not config_status['auto_download']:
        recommendations.append('💡 启用自动下载以获得完整体验')

    return recommendations


@telegram_bp.route('/api/test-file-push', methods=['POST'])
def test_file_push():
    """测试文件推送功能"""
    try:
        data = request.get_json()
        bot_token = data.get('bot_token')
        chat_id = data.get('chat_id')

        if not bot_token or not chat_id:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400

        # 创建测试文件
        import tempfile
        import os

        from datetime import datetime

        test_content = f"""🎬 YT-DLP Telegram 推送测试

📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🤖 Bot Token: {bot_token[:10]}...
💬 Chat ID: {chat_id}

✅ 如果您收到这个文件，说明文件推送功能正常工作！

🔧 测试信息:
- 文件类型: 文本文件
- 编码: UTF-8
- 大小: 约 {len('测试内容')} 字节

📝 下一步:
1. 确保启用了 Telegram 通知
2. 确保启用了 Webhook 和自动下载
3. 向 Bot 发送视频链接测试完整流程
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            test_file_path = f.name

        try:
            # 使用 TelegramNotifier 发送文件
            from webapp.core.telegram_notifier import TelegramNotifier

            # 创建临时通知器实例并设置临时配置
            notifier = TelegramNotifier()
            notifier._bot_token = bot_token
            notifier._chat_id = chat_id
            notifier._enabled = True

            # 从数据库获取 API ID 和 API Hash
            config = TelegramConfig.get_config()
            if config.api_id:
                notifier._api_id = config.api_id
            if config.api_hash:
                notifier._api_hash = config.api_hash

            caption = "🧪 **YT-DLP 文件推送测试**\n\n✅ 如果您收到这个文件，说明推送功能正常工作！"

            success = notifier.send_document(test_file_path, caption)

            if success:
                logger.info(f'文件推送测试成功: {chat_id}')
                return jsonify({
                    'success': True,
                    'message': '文件推送测试成功！请检查您的 Telegram'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '文件发送失败，请检查 Bot Token 和 Chat ID'
                })

        finally:
            # 清理测试文件
            try:
                os.unlink(test_file_path)
            except:
                pass

    except Exception as e:
        logger.error(f'文件推送测试失败: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@telegram_bp.route('/api/check-push-config', methods=['GET'])
def check_push_config():
    """检查推送配置状态"""
    try:
        config = TelegramConfig.get_config()
        telegram_notifier = get_telegram_notifier()

        # 收集配置信息
        config_info = {
            'telegram_enabled': config.enabled,
            'bot_token_configured': bool(config.bot_token),
            'chat_id_configured': bool(config.chat_id),
            'webhook_enabled': config.webhook_enabled,
            'auto_download': config.auto_download,
            'push_mode': config.push_mode,
            'notifier_enabled': telegram_notifier.is_enabled(),
            'file_size_limit_mb': config.file_size_limit_mb
        }

        # 添加详细诊断信息
        issues = []
        if not config.enabled:
            issues.append('Telegram 通知未启用')
        if not config.bot_token:
            issues.append('Bot Token 未配置')
        if not config.chat_id:
            issues.append('Chat ID 未配置')
        if not config.webhook_enabled:
            issues.append('Webhook 未启用')
        if not config.auto_download:
            issues.append('自动下载未启用')

        telegram_notifier = get_telegram_notifier()
        if not telegram_notifier.is_enabled():
            issues.append('通知器未启用')

        config_info['issues'] = issues
        config_info['all_good'] = len(issues) == 0

        return jsonify({
            'success': True,
            'config': config_info
        })

    except Exception as e:
        logger.error(f'检查推送配置失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@telegram_bp.route('/api/setup-webhook', methods=['POST'])
@login_required
def setup_webhook():
    """设置Telegram Webhook"""
    try:
        config = TelegramConfig.get_config()

        if not config.is_configured():
            return jsonify({
                'success': False,
                'error': '请先配置 Bot Token 和 Chat ID'
            }), 400

        telegram_notifier = get_telegram_notifier()
        clean_token = telegram_notifier._get_clean_bot_token()

        # 获取请求数据
        request_data = request.get_json() or {}
        custom_webhook_url = request_data.get('webhook_url')

        # 构建 Webhook URL
        if custom_webhook_url:
            webhook_url = custom_webhook_url
            logger.info(f'使用自定义 Webhook URL: {webhook_url}')
        else:
            webhook_url = request.url_root.rstrip('/') + '/telegram/webhook'
            logger.info(f'使用默认 Webhook URL: {webhook_url}')

        # 检查端口是否被 Telegram 支持
        import re
        from urllib.parse import urlparse

        parsed_url = urlparse(webhook_url)
        current_port = parsed_url.port
        allowed_ports = [80, 88, 443, 8443]

        if current_port and current_port not in allowed_ports:
            # 建议使用允许的端口
            suggested_port = 8443 if webhook_url.startswith('https://') else 80
            suggested_url = webhook_url.replace(f':{current_port}', f':{suggested_port}')

            return jsonify({
                'success': False,
                'error': f'端口 {current_port} 不被 Telegram 支持',
                'port_issue': {
                    'current_port': current_port,
                    'allowed_ports': allowed_ports,
                    'suggested_url': suggested_url,
                    'solution': f'请将服务端口改为 {suggested_port} 或使用反向代理'
                }
            }), 400

        # 检查 URL 是否为 HTTPS（生产环境要求）
        if not webhook_url.startswith('https://') and not webhook_url.startswith('http://localhost'):
            logger.warning(f'Webhook URL 不是 HTTPS: {webhook_url}')
            # 对于非本地环境，尝试使用 HTTPS
            if not webhook_url.startswith('http://localhost') and not webhook_url.startswith('http://127.0.0.1'):
                webhook_url = webhook_url.replace('http://', 'https://')
                logger.info(f'自动转换为 HTTPS: {webhook_url}')

        logger.info(f'设置 Webhook URL: {webhook_url}')

        # 测试 Webhook URL 是否可访问（可选）
        try:
            test_response = requests.get(webhook_url, timeout=5)
            logger.info(f'Webhook URL 测试: {test_response.status_code}')
        except Exception as e:
            logger.warning(f'Webhook URL 可能不可访问: {e}')

        # 调用 Telegram API 设置 Webhook
        import requests
        api_url = f"https://api.telegram.org/bot{clean_token}/setWebhook"

        data = {
            'url': webhook_url,
            'allowed_updates': ['message'],
            'drop_pending_updates': True  # 清除待处理的更新
        }

        # 如果有 webhook 密钥，添加到请求中
        if config.webhook_secret:
            data['secret_token'] = config.webhook_secret

        response = requests.post(api_url, data=data, timeout=30)

        # 获取响应内容
        try:
            result = response.json()
        except:
            result = {'ok': False, 'description': f'HTTP {response.status_code}: {response.text}'}

        if response.status_code == 200 and result.get('ok'):
            return jsonify({
                'success': True,
                'message': f'Webhook 设置成功！URL: {webhook_url}',
                'webhook_url': webhook_url
            })
        else:
            error_msg = result.get('description', f'HTTP {response.status_code}')
            logger.error(f'Telegram API 错误: {error_msg}')
            logger.error(f'请求数据: {data}')
            logger.error(f'响应: {response.text}')

            # 提供手动设置的指导
            manual_url = f"https://api.telegram.org/bot{clean_token}/setWebhook?url={webhook_url}"

            return jsonify({
                'success': False,
                'error': f'Telegram API 错误: {error_msg}',
                'manual_setup': {
                    'description': '您可以手动设置 Webhook',
                    'method1': f'在浏览器中访问: {manual_url}',
                    'method2': f'或使用 curl: curl -X POST "{api_url}" -d "url={webhook_url}"',
                    'webhook_url': webhook_url
                }
            }), 400

    except Exception as e:
        logger.error(f'设置Webhook失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@telegram_bp.route('/webhook', methods=['GET'])
def telegram_webhook_info():
    """Telegram Webhook信息页面"""
    try:
        config = TelegramConfig.get_config()

        webhook_info = {
            'webhook_url': request.url,
            'webhook_enabled': config.webhook_enabled,
            'auto_download': config.auto_download,
            'push_mode': config.push_mode,
            'status': 'active' if config.webhook_enabled else 'disabled'
        }

        return jsonify({
            'success': True,
            'message': 'Telegram Webhook端点',
            'info': webhook_info,
            'usage': {
                'method': 'POST',
                'content_type': 'application/json',
                'description': '此端点用于接收Telegram Bot的webhook消息'
            }
        })

    except Exception as e:
        logger.error(f'获取webhook信息失败: {e}')
        return jsonify({'error': '获取信息失败'}), 500

@telegram_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Telegram Webhook接收端点"""
    try:
        print("🔔🔔🔔 收到 Telegram Webhook 请求 🔔🔔🔔")
        logger.info("=== 收到 Telegram Webhook 请求 ===")
        logger.info(f"请求头: {dict(request.headers)}")
        logger.info(f"请求来源: {request.remote_addr}")

        print(f"📋 请求头: {dict(request.headers)}")
        print(f"🌐 请求来源: {request.remote_addr}")

        # 获取配置
        config = TelegramConfig.get_config()
        print(f"⚙️ Webhook 配置状态: enabled={config.webhook_enabled}, auto_download={config.auto_download}")
        logger.info(f"Webhook 配置状态: enabled={config.webhook_enabled}, auto_download={config.auto_download}")

        if not config.webhook_enabled:
            print("❌ Webhook 未启用，拒绝请求")
            logger.warning("Webhook 未启用，拒绝请求")
            return jsonify({'error': 'Webhook未启用'}), 403

        # 验证webhook密钥
        if config.webhook_secret:
            signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
            print(f"🔐 验证Webhook密钥: 配置={bool(config.webhook_secret)}, 收到={bool(signature)}")
            if signature != config.webhook_secret:
                print("❌ Telegram webhook签名验证失败")
                logger.warning('Telegram webhook签名验证失败')
                return jsonify({'error': '签名验证失败'}), 403

        # 解析消息
        update = request.get_json()
        print(f"📨 收到的更新数据: {update}")
        logger.info(f"收到的更新数据: {update}")

        if not update:
            print("❌ 无效的消息格式")
            logger.error("无效的消息格式")
            return jsonify({'error': '无效的消息格式'}), 400

        # 处理消息
        print(f"🔄 开始处理消息...")
        result = _process_telegram_message(update, config)
        print(f"✅ 消息处理结果: {result}")
        logger.info(f"消息处理结果: {result}")

        return jsonify({'success': True, 'result': result})

    except Exception as e:
        logger.error(f'处理Telegram webhook失败: {e}', exc_info=True)
        return jsonify({'error': '处理失败'}), 500

def _process_telegram_message(update, config):
    """处理Telegram消息"""
    try:
        print(f"🔍 分析更新数据...")
        message = update.get('message')
        if not message:
            print(f"⚠️ 非消息更新，忽略")
            return {'action': 'ignored', 'reason': '非消息更新'}

        # 检查是否来自配置的chat_id
        chat_id = str(message.get('chat', {}).get('id', ''))
        print(f"🆔 Chat ID 检查: 收到={chat_id}, 配置={config.chat_id}")
        if chat_id != config.chat_id:
            print(f"❌ Chat ID不匹配: 收到{chat_id}, 期望{config.chat_id}")
            logger.warning(f'收到来自未授权chat_id的消息: {chat_id}')
            return {'action': 'ignored', 'reason': '未授权的chat_id'}

        # 获取用户信息
        user = message.get('from', {})
        username = user.get('username', user.get('first_name', '未知用户'))
        print(f"👤 消息来自: {username} (ID: {user.get('id')})")

        # 获取消息文本
        text = message.get('text', '').strip()
        print(f"📝 消息内容: '{text}'")
        if not text:
            print(f"⚠️ 空消息，忽略")
            return {'action': 'ignored', 'reason': '空消息'}
        
        # 检查是否为URL
        if not _is_valid_url(text):
            # 发送帮助信息
            from ..core.telegram_notifier import get_telegram_notifier
            telegram_notifier = get_telegram_notifier()
            help_text = "🤖 *使用说明*\n\n请发送视频链接，我会自动下载并发送给您！\n\n支持的网站：YouTube、Bilibili、Twitter等"
            telegram_notifier.send_message(help_text)
            return {'action': 'help_sent', 'message': '已发送帮助信息'}
        
        # 如果启用了自动下载，开始下载
        if config.auto_download:
            from flask import current_app
            from ..core.download_manager import get_download_manager
            download_manager = get_download_manager(current_app)

            # 构建下载选项
            download_options = {
                'telegram_push': True,
                'telegram_push_mode': config.push_mode,
                'source': 'telegram_webhook'
            }

            # 创建下载任务
            download_id = download_manager.create_download(text, download_options)

            # 发送确认消息
            from ..core.telegram_notifier import get_telegram_notifier
            telegram_notifier = get_telegram_notifier()
            confirm_text = f"✅ *下载已开始*\n\n🔗 链接: {text}\n📋 任务ID: `{download_id}`\n\n⏳ 下载完成后会自动发送文件给您！"
            telegram_notifier.send_message(confirm_text)
            
            return {
                'action': 'download_started',
                'download_id': download_id,
                'url': text
            }
        else:
            # 仅发送确认消息
            from ..core.telegram_notifier import get_telegram_notifier
            telegram_notifier = get_telegram_notifier()
            confirm_text = f"📥 *收到下载链接*\n\n🔗 {text}\n\n⚠️ 自动下载已禁用，请手动在网页端开始下载。"
            telegram_notifier.send_message(confirm_text)
            
            return {
                'action': 'url_received',
                'url': text
            }
            
    except Exception as e:
        logger.error(f'处理Telegram消息失败: {e}')
        return {'action': 'error', 'error': str(e)}

def _is_valid_url(text):
    """检查是否为有效的URL"""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(text) is not None
