#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 API 响应格式的脚本
"""

import sys
import requests
import json

def test_api_response_format():
    """测试 API 响应格式"""
    print("🔍 测试 API 响应格式...")
    
    base_url = "http://localhost:8080"
    
    # 1. 测试登录 API
    print("\n1️⃣ 测试登录 API 响应格式...")
    login_url = f"{base_url}/api/auth/login"
    login_data = {"username": "admin", "password": "admin123"}
    
    try:
        response = requests.post(login_url, json=login_data, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("登录 API 响应格式:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 检查是否有 success 字段
            if 'success' in data:
                print("✅ 登录 API 包含 'success' 字段")
                token = data.get('token')
                if token:
                    print("✅ 成功获取 token")
                    
                    # 2. 测试视频信息 API
                    print("\n2️⃣ 测试视频信息 API 响应格式...")
                    info_url = f"{base_url}/api/info"
                    headers = {"Authorization": f"Bearer {token}"}
                    params = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
                    
                    try:
                        info_response = requests.get(info_url, headers=headers, params=params, timeout=30)
                        print(f"状态码: {info_response.status_code}")
                        
                        if info_response.status_code == 200:
                            info_data = info_response.json()
                            print("视频信息 API 响应格式:")
                            print(json.dumps(info_data, indent=2, ensure_ascii=False))
                            
                            # 检查响应格式
                            if 'success' in info_data:
                                print("ℹ️ 视频信息 API 包含 'success' 字段")
                            else:
                                print("ℹ️ 视频信息 API 不包含 'success' 字段（直接返回数据）")
                            
                            if 'title' in info_data:
                                print("✅ 视频信息 API 包含 'title' 字段")
                                print(f"📋 视频标题: {info_data['title']}")
                            else:
                                print("❌ 视频信息 API 不包含 'title' 字段")
                            
                            # 分析响应结构
                            print("\n📊 响应结构分析:")
                            for key in info_data.keys():
                                value_type = type(info_data[key]).__name__
                                print(f"  - {key}: {value_type}")
                                
                        else:
                            print(f"❌ 视频信息 API 返回错误状态码: {info_response.status_code}")
                            print(f"响应内容: {info_response.text}")
                            
                    except Exception as e:
                        print(f"❌ 视频信息 API 请求失败: {e}")
                        
                else:
                    print("❌ 登录响应中没有 token")
            else:
                print("❌ 登录 API 不包含 'success' 字段")
                
        else:
            print(f"❌ 登录失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")

def test_health_endpoint():
    """测试健康检查端点"""
    print("\n3️⃣ 测试健康检查端点响应格式...")
    
    health_url = "http://localhost:8080/health"
    
    try:
        response = requests.get(health_url, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("健康检查 API 响应格式:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if 'status' in data:
                print(f"✅ 健康状态: {data['status']}")
            else:
                print("❌ 健康检查响应中没有 'status' 字段")
                
        else:
            print(f"❌ 健康检查失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"❌ 健康检查请求失败: {e}")

def main():
    """主函数"""
    print("🚀 开始测试 API 响应格式...")
    print("="*60)
    
    test_api_response_format()
    test_health_endpoint()
    
    print("\n" + "="*60)
    print("📊 测试总结:")
    print("- 登录 API 应该包含 'success' 字段")
    print("- 视频信息 API 直接返回视频数据，不包含 'success' 字段")
    print("- 健康检查 API 包含 'status' 字段")
    print("\n💡 建议:")
    print("- 测试脚本应该检查 'title' 字段而不是 'success' 字段")
    print("- 或者修改 API 返回格式以包含 'success' 字段")

if __name__ == "__main__":
    main()
