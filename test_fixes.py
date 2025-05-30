#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_yt_dlp_import():
    """测试 yt-dlp 导入"""
    print("🔍 测试 yt-dlp 导入...")
    try:
        from yt_dlp import YoutubeDL
        print("✅ YoutubeDL 导入成功")
        
        # 测试基础 extractors
        from yt_dlp.extractor.youtube import YoutubeIE
        from yt_dlp.extractor.generic import GenericIE
        print("✅ 基础 extractors 导入成功")
        
        # 测试创建实例（使用安全选项）
        ydl = YoutubeDL({
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'extract_flat': True
        })
        print("✅ YoutubeDL 实例创建成功")
        
        return True
    except Exception as e:
        print(f"❌ yt-dlp 测试失败: {e}")
        return False

def test_webapp_import():
    """测试 webapp 导入"""
    print("🔍 测试 webapp 导入...")
    try:
        from webapp.app import create_app
        print("✅ webapp.app 导入成功")
        
        from webapp.core.ytdlp_manager import get_ytdlp_manager
        print("✅ ytdlp_manager 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ webapp 测试失败: {e}")
        return False

def test_flask_routes():
    """测试 Flask 路由"""
    print("🔍 测试 Flask 路由...")
    try:
        from webapp.app import create_app
        app = create_app()
        
        with app.app_context():
            from flask import url_for
            # 测试路由是否正确注册
            login_url = url_for('auth.login')
            print(f"✅ 登录路由: {login_url}")
            
        return True
    except Exception as e:
        print(f"❌ Flask 路由测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试修复后的功能...\n")
    
    tests = [
        ("yt-dlp 导入", test_yt_dlp_import),
        ("webapp 导入", test_webapp_import),
        ("Flask 路由", test_flask_routes),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 {test_name} 出现异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print(f"\n{'='*50}")
    print("测试总结")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！修复成功！")
        return 0
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    sys.exit(main())
