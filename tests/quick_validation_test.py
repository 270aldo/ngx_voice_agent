#!/usr/bin/env python3
"""
Quick Validation Test for NGX Voice Sales Agent.
Runs a subset of tests to quickly validate system functionality.
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime


async def test_api_health():
    """Test if API is healthy."""
    print("🔍 Testing API Health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API is healthy: {data}")
                    return True
                else:
                    print(f"❌ API returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False


async def test_conversation_flow():
    """Test basic conversation flow."""
    print("\n🔍 Testing Conversation Flow...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Start conversation
            start_data = {
                "customer_data": {
                    "id": "quick-test-1",
                    "name": "Quick Test User",
                    "email": "quick@test.com",
                    "age": 35,
                    "profession": "Entrepreneur"
                }
            }
            
            print("  Starting conversation...")
            async with session.post(
                "http://localhost:8000/conversations/start",
                json=start_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    print(f"  ❌ Failed to start conversation: {response.status}")
                    return False
                
                data = await response.json()
                conversation_id = data.get("conversation_id")
                print(f"  ✅ Conversation started: {conversation_id}")
                print(f"  Agent: {data.get('message', '')[:100]}...")
            
            # Send a message
            print("\n  Sending test message...")
            async with session.post(
                f"http://localhost:8000/conversations/{conversation_id}/message",
                json={"message": "Hola, ¿qué incluye el programa PRIME?"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    print(f"  ❌ Failed to send message: {response.status}")
                    return False
                
                data = await response.json()
                print(f"  ✅ Response received")
                print(f"  Agent: {data.get('response', '')[:100]}...")
            
            # End conversation
            print("\n  Ending conversation...")
            async with session.post(
                f"http://localhost:8000/conversations/{conversation_id}/end",
                json={"reason": "test_completed"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    print(f"  ❌ Failed to end conversation: {response.status}")
                    return False
                
                print(f"  ✅ Conversation ended successfully")
            
            return True
            
    except Exception as e:
        print(f"❌ Conversation test failed: {e}")
        return False


async def test_concurrent_requests():
    """Test handling of concurrent requests."""
    print("\n🔍 Testing Concurrent Requests...")
    
    async def make_request(session, user_id):
        try:
            async with session.get(
                "http://localhost:8000/health",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
        except:
            return False
    
    try:
        async with aiohttp.ClientSession() as session:
            # Send 10 concurrent requests
            tasks = [make_request(session, i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            successful = sum(results)
            print(f"  Concurrent requests: {successful}/10 successful")
            
            if successful == 10:
                print("  ✅ All concurrent requests handled successfully")
                return True
            else:
                print(f"  ⚠️  Some requests failed: {10 - successful} failures")
                return successful >= 8  # Allow up to 2 failures
                
    except Exception as e:
        print(f"❌ Concurrent request test failed: {e}")
        return False


async def test_monitoring_endpoints():
    """Test if monitoring endpoints are accessible."""
    print("\n🔍 Testing Monitoring Endpoints...")
    
    endpoints = [
        ("Prometheus", "http://localhost:9090"),
        ("Grafana", "http://localhost:3000"),
        ("API Metrics", "http://localhost:8000/metrics")
    ]
    
    results = []
    
    for name, url in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        print(f"  ✅ {name} is accessible")
                        results.append(True)
                    else:
                        print(f"  ⚠️  {name} returned status {response.status}")
                        results.append(False)
        except:
            print(f"  ⚠️  {name} is not accessible (might not be running)")
            results.append(False)
    
    # Monitoring is optional, so we just inform
    return True  # Don't fail the test for monitoring


async def main():
    """Run quick validation tests."""
    print("🚀 NGX Voice Sales Agent - Quick Validation Test")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("API Health", test_api_health),
        ("Conversation Flow", test_conversation_flow),
        ("Concurrent Requests", test_concurrent_requests),
        ("Monitoring Endpoints", test_monitoring_endpoints)
    ]
    
    results = {}
    all_passed = True
    
    for test_name, test_func in tests:
        result = await test_func()
        results[test_name] = result
        if not result and test_name != "Monitoring Endpoints":
            all_passed = False
        await asyncio.sleep(2)  # Small delay between tests
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    if all_passed:
        print("\n🎉 All validation tests passed!")
        print("The system is ready for advanced testing.")
        print("\nTo run full test suite:")
        print("  python tests/run_all_advanced_tests.py")
    else:
        print("\n⚠️  Some tests failed.")
        print("Please ensure:")
        print("  1. API is running: python run.py")
        print("  2. Docker services are up: docker-compose up -d")
        print("  3. All dependencies are installed")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tests/results/quick_validation_{timestamp}.json"
    
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, "w") as f:
        json.dump({
            "test_type": "quick_validation",
            "timestamp": timestamp,
            "all_passed": all_passed,
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())