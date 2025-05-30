#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的健康检查端点测试脚本
"""

import sys
import requests
import time
import json

def test_health_endpoint_external():
    """从外部测试健康检查端点"""
    print("🔍 测试健康检查端点（外部访问）...")
    
    base_url = "http://localhost:8080"
    health_url = f"{base_url}/health"
    
    max_retries = 12
    retry_interval = 10
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"📡 尝试 {attempt}/{max_retries}: 访问 {health_url}")
            
            response = requests.get(health_url, timeout=10)
            
            print(f"📊 状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("✅ 健康检查成功!")
                    print(f"📋 响应内容:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    return True
                except json.JSONDecodeError:
                    print(f"⚠️ 响应不是有效的 JSON: {response.text}")
            else:
                print(f"❌ 健康检查失败，状态码: {response.status_code}")
                print(f"📄 响应内容: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"🔌 连接失败，服务可能还未启动")
        except requests.exceptions.Timeout:
            print(f"⏰ 请求超时")
        except Exception as e:
            print(f"❌ 请求异常: {e}")
        
        if attempt < max_retries:
            print(f"⏳ 等待 {retry_interval} 秒后重试...")
            time.sleep(retry_interval)
    
    print("❌ 所有重试都失败了")
    return False

def test_health_endpoint_internal():
    """从内部测试健康检查端点"""
    print("🔍 测试健康检查端点（内部测试）...")
    
    try:
        sys.path.insert(0, '/app')
        from webapp.app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            print("📡 发送内部测试请求...")
            response = client.get('/health')
            
            print(f"📊 状态码: {response.status_code}")
            
            if response.status_code in [200, 503]:  # 200 = healthy, 503 = unhealthy but responding
                try:
                    data = response.get_json()
                    print("✅ 健康检查端点响应正常!")
                    print(f"📋 响应内容:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    return True
                except Exception as e:
                    print(f"⚠️ 响应解析失败: {e}")
                    print(f"📄 原始响应: {response.data}")
            else:
                print(f"❌ 健康检查端点返回异常状态码: {response.status_code}")
                print(f"📄 响应内容: {response.data}")
                
    except Exception as e:
        print(f"❌ 内部测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    return False

def test_other_endpoints():
    """测试其他端点是否正常"""
    print("🔍 测试其他端点...")
    
    endpoints = [
        "/",
        "/login",
        "/api/auth/status"
    ]
    
    base_url = "http://localhost:8080"
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"📡 测试端点: {url}")
            
            response = requests.get(url, timeout=5, allow_redirects=False)
            print(f"📊 {endpoint}: 状态码 {response.status_code}")
            
        except Exception as e:
            print(f"❌ {endpoint}: 请求失败 - {e}")

def main():
    """主函数"""
    print("🚀 开始健康检查端点测试...")
    print("="*60)
    
    # 首先尝试内部测试
    print("\n🏠 内部测试:")
    print("-"*40)
    internal_success = test_health_endpoint_internal()
    
    # 然后尝试外部测试
    print("\n🌐 外部测试:")
    print("-"*40)
    external_success = test_health_endpoint_external()
    
    # 测试其他端点
    print("\n🔗 其他端点测试:")
    print("-"*40)
    test_other_endpoints()
    
    # 总结
    print("\n📊 测试结果总结:")
    print("="*60)
    print(f"内部测试: {'✅ 通过' if internal_success else '❌ 失败'}")
    print(f"外部测试: {'✅ 通过' if external_success else '❌ 失败'}")
    
    if internal_success or external_success:
        print("🎉 健康检查端点工作正常!")
        return 0
    else:
        print("⚠️ 健康检查端点存在问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())
