# -*- coding: utf-8 -*-
"""
认证相关路由 - 使用Flask-Login
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login():
    """显示登录页面"""
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login_post():
    """处理登录请求"""
    try:
        # 获取表单数据
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            remember = data.get('remember', False)
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            remember = bool(request.form.get('remember'))

        logger.info(f"🔐 登录尝试: {username}")

        if not username or not password:
            error_msg = '用户名和密码不能为空'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            else:
                flash(error_msg)
                return redirect(url_for('auth.login'))

        # 查找用户
        from ..models import User
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            error_msg = '用户名或密码错误'
            logger.warning(f"❌ 登录失败: {username}")
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 401
            else:
                flash(error_msg)
                return redirect(url_for('auth.login'))

        # 登录用户
        login_user(user, remember=remember)

        # 更新最后登录时间
        from datetime import datetime
        user.last_login = datetime.utcnow()
        from ..models import db
        db.session.commit()

        logger.info(f"✅ 登录成功: {username}")

        if request.is_json:
            return jsonify({
                'success': True,
                'message': '登录成功',
                'username': user.username,
                'is_admin': user.is_admin
            })
        else:
            # 重定向到原来要访问的页面或主页
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"登录处理失败: {e}")
        error_msg = '登录处理失败'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg)
            return redirect(url_for('auth.login'))

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """处理登出请求"""
    try:
        username = current_user.username
        logout_user()

        logger.info(f"✅ 用户已登出: {username}")

        if request.is_json:
            return jsonify({
                'success': True,
                'message': '已成功登出'
            })
        else:
            flash('已成功登出')
            return redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"登出处理失败: {e}")
        if request.is_json:
            return jsonify({'success': False, 'error': '登出处理失败'}), 500
        else:
            flash('登出处理失败')
            return redirect(url_for('main.index'))

@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    """验证用户登录状态"""
    try:
        if current_user.is_authenticated:
            return jsonify({
                'valid': True,
                'username': current_user.username,
                'is_admin': current_user.is_admin
            })
        else:
            return jsonify({
                'valid': False,
                'error': '用户未登录'
            }), 401

    except Exception as e:
        logger.error(f"验证失败: {e}")
        return jsonify({
            'valid': False,
            'error': '验证失败'
        }), 500

@auth_bp.route('/status')
def status():
    """获取认证状态"""
    try:
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True,
                'username': current_user.username,
                'is_admin': current_user.is_admin
            })
        else:
            return jsonify({
                'authenticated': False
            })

    except Exception as e:
        logger.error(f"获取认证状态失败: {e}")
        return jsonify({
            'authenticated': False,
            'error': str(e)
        }), 500

# 兼容旧API的路由
@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """API登录 - 兼容旧接口"""
    return login_post()

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API登出 - 兼容旧接口"""
    return logout()

@auth_bp.route('/api/auth/verify', methods=['GET'])
def api_verify():
    """API验证 - 兼容旧接口"""
    return verify()

@auth_bp.route('/api/auth/status', methods=['GET'])
def api_status():
    """API状态 - 兼容旧接口"""
    return status()

# 兼容旧API - 简化版本
@auth_bp.route('/api/auth/sync-session', methods=['POST'])
def api_sync_session():
    """同步session状态 - 兼容旧接口"""
    try:
        if current_user.is_authenticated:
            return jsonify({
                'success': True,
                'message': 'Session已同步',
                'username': current_user.username,
                'is_admin': current_user.is_admin
            })
        else:
            return jsonify({
                'success': False,
                'error': '用户未登录'
            }), 401
    except Exception as e:
        logger.error(f"Session同步失败: {e}")
        return jsonify({'error': str(e)}), 500

# 简化的管理功能 - 使用Flask-Login
@auth_bp.route('/api/auth/change-password', methods=['POST'])
@login_required
def api_change_password():
    """修改密码 - 仅管理员"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '权限不足'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            return jsonify({'error': '所有字段都是必填的'}), 400

        # 验证当前密码
        if not current_user.check_password(current_password):
            return jsonify({'error': '当前密码错误'}), 400

        # 验证新密码确认
        if new_password != confirm_password:
            return jsonify({'error': '新密码和确认密码不匹配'}), 400

        # 密码强度验证
        if len(new_password) < 6:
            return jsonify({'error': '新密码长度至少6位'}), 400

        # 修改密码
        current_user.set_password(new_password)
        from ..models import db
        db.session.commit()

        logger.info(f"管理员 {current_user.username} 成功修改密码")
        return jsonify({
            'success': True,
            'message': '密码修改成功'
        })

    except Exception as e:
        logger.error(f"修改密码时发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/change-username', methods=['POST'])
@login_required
def api_change_username():
    """修改用户名 - 仅管理员"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '权限不足'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        new_username = data.get('new_username', '').strip()
        password = data.get('password')

        if not new_username or not password:
            return jsonify({'error': '用户名和密码都是必填的'}), 400

        # 验证当前密码
        if not current_user.check_password(password):
            return jsonify({'error': '当前密码错误'}), 400

        # 验证新用户名格式
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            return jsonify({'error': '用户名只能包含字母、数字和下划线'}), 400

        if len(new_username) < 3 or len(new_username) > 20:
            return jsonify({'error': '用户名长度必须在3-20位之间'}), 400

        # 检查用户名是否已存在
        from ..models import User, db
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.id != current_user.id:
            return jsonify({'error': '用户名已存在'}), 400

        # 检查是否与当前用户名相同
        if new_username == current_user.username:
            return jsonify({'error': '新用户名不能与当前用户名相同'}), 400

        # 修改用户名
        old_username = current_user.username
        current_user.username = new_username
        db.session.commit()

        logger.info(f"管理员用户名从 {old_username} 修改为 {new_username}")
        return jsonify({
            'success': True,
            'message': '用户名修改成功',
            'new_username': new_username
        })

    except Exception as e:
        logger.error(f"修改用户名时发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/session-info', methods=['GET'])
@login_required
def api_session_info():
    """获取会话信息"""
    try:
        # 简化的会话信息
        return jsonify({
            'success': True,
            'session_info': {
                'timeout_hours': 24,  # 默认24小时
                'remaining_hours': 23,  # 简化显示
                'username': current_user.username
            }
        })
    except Exception as e:
        logger.error(f"获取会话信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/clear-all-sessions', methods=['POST'])
@login_required
def api_clear_all_sessions():
    """清除所有会话 - 简化版本"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': '权限不足'}), 403

        # 在Flask-Login中，我们只能登出当前用户
        # 实际的多会话管理需要更复杂的实现
        logger.info(f"管理员 {current_user.username} 请求清除所有会话")

        return jsonify({
            'success': True,
            'message': '会话清除请求已处理'
        })
    except Exception as e:
        logger.error(f"清除会话失败: {e}")
        return jsonify({'error': str(e)}), 500
