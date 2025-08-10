#!/usr/bin/env python3
"""
Quick System Check - NGX Voice Sales Agent

Verificación rápida del sistema antes de ejecutar tests completos.
"""

import asyncio
import aiohttp
import os
import time
import psutil
import redis
from datetime import datetime

API_URL = os.getenv("API_URL", "http://localhost:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


async def check_api_health():
    """Check if API is running and healthy."""
    print("🔍 Checking API...")
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.get(f"{API_URL}/health", timeout=aiohttp.ClientTimeout(total=5))
            if response.status == 200:
                data = await response.json()
                print(f"   ✅ API is healthy: {data}")
                return True
            else:
                print(f"   ❌ API returned status {response.status}")
                return False
    except Exception as e:
        print(f"   ❌ API check failed: {e}")
        return False


def check_redis():
    """Check if Redis is running."""
    print("\n🔍 Checking Redis...")
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("   ✅ Redis is running")
        
        # Check some cache stats
        info = r.info()
        print(f"   📊 Used memory: {info.get('used_memory_human', 'N/A')}")
        print(f"   📊 Connected clients: {info.get('connected_clients', 'N/A')}")
        return True
    except Exception as e:
        print(f"   ❌ Redis check failed: {e}")
        print("   💡 Start Redis with: redis-server")
        return False


def check_environment():
    """Check environment variables."""
    print("\n🔍 Checking environment...")
    required_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
    missing = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"   ✅ {var} is set")
        else:
            print(f"   ❌ {var} is missing")
            missing.append(var)
    
    if missing:
        print("\n   💡 Load environment with: export $(cat .env | xargs)")
        return False
    return True


def check_system_resources():
    """Check system resources."""
    print("\n🔍 Checking system resources...")
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"   💻 CPU Usage: {cpu_percent}%")
    if cpu_percent > 80:
        print("      ⚠️  High CPU usage detected")
    
    # Memory
    memory = psutil.virtual_memory()
    print(f"   🧠 Memory Usage: {memory.percent}% ({memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB)")
    if memory.percent > 80:
        print("      ⚠️  High memory usage detected")
    
    # Disk
    disk = psutil.disk_usage('/')
    print(f"   💾 Disk Usage: {disk.percent}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)")
    
    return True


async def test_basic_conversation():
    """Test a basic conversation flow."""
    print("\n🔍 Testing basic conversation...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Start conversation
            start_time = time.time()
            response = await session.post(
                f"{API_URL}/conversations/start",
                json={
                    "customer_data": {
                        "name": "Test User",
                        "email": "test@example.com",
                        "age": 30,
                        "occupation": "Engineer"
                    }
                },
                timeout=aiohttp.ClientTimeout(total=10)
            )
            start_time_taken = time.time() - start_time
            
            if response.status != 200:
                print(f"   ❌ Failed to start conversation: {response.status}")
                return False
            
            data = await response.json()
            conversation_id = data.get("conversation_id")
            print(f"   ✅ Conversation started (ID: {conversation_id[:8]}...)")
            print(f"   ⏱️  Start time: {start_time_taken:.2f}s")
            
            # Send a message
            msg_time = time.time()
            msg_response = await session.post(
                f"{API_URL}/conversations/{conversation_id}/message",
                json={"message": "¿Cuál es el precio?"},
                timeout=aiohttp.ClientTimeout(total=10)
            )
            msg_time_taken = time.time() - msg_time
            
            if msg_response.status != 200:
                print(f"   ❌ Failed to send message: {msg_response.status}")
                return False
            
            print(f"   ✅ Message sent successfully")
            print(f"   ⏱️  Response time: {msg_time_taken:.2f}s")
            
            # Check performance
            if msg_time_taken < 0.5:
                print(f"   🚀 Performance: EXCELLENT (<0.5s)")
            elif msg_time_taken < 1.0:
                print(f"   ⚡ Performance: GOOD (<1s)")
            else:
                print(f"   🐌 Performance: NEEDS IMPROVEMENT (>1s)")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False


async def main():
    """Run all system checks."""
    print("🏥 NGX Voice Sales Agent - System Health Check")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API URL: {API_URL}")
    print("=" * 50)
    
    checks = {
        "API Health": await check_api_health(),
        "Redis": check_redis(),
        "Environment": check_environment(),
        "Resources": check_system_resources(),
        "Basic Conversation": await test_basic_conversation()
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    passed = sum(checks.values())
    total = len(checks)
    
    for check, result in checks.items():
        print(f"{'✅' if result else '❌'} {check}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 SYSTEM IS READY FOR TESTING!")
        return 0
    else:
        print("\n⚠️  SYSTEM NEEDS ATTENTION")
        print("Fix the issues above before running full tests.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)