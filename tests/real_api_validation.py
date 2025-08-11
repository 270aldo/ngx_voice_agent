#!/usr/bin/env python3
"""
Test de Validación de API Real - NGX Voice Sales Agent

Este test verifica que todos los endpoints funcionen correctamente
con la API real, sin mocks.
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, Any, List

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class APIRealValidator:
    """Validador de API real sin mocks."""
    
    def __init__(self):
        self.api_url = API_URL
        self.results = {
            "endpoints_tested": 0,
            "endpoints_passed": 0,
            "endpoints_failed": 0,
            "errors": [],
            "response_times": []
        }
    
    async def test_health_endpoint(self) -> bool:
        """Test /health endpoint."""
        print("\n🔍 Testing /health endpoint...")
        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                response = await session.get(f"{self.api_url}/health")
                response_time = (datetime.now() - start_time).total_seconds()
                
                self.results["response_times"].append(response_time)
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data}")
                    return True
                else:
                    self.results["errors"].append(f"Health check failed: {response.status}")
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            self.results["errors"].append(f"Health check error: {str(e)}")
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_conversation_start(self) -> Dict[str, Any]:
        """Test POST /conversations/start endpoint."""
        print("\n🔍 Testing /conversations/start endpoint...")
        
        customer_data = {
            "name": "Test User",
            "email": "test@example.com",
            "age": 35,
            "occupation": "Software Engineer",
            "goals": {
                "primary": "performance",
                "timeline": "3_months"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                response = await session.post(
                    f"{self.api_url}/conversations/start",
                    json={"customer_data": customer_data},
                    headers={"Content-Type": "application/json"}
                )
                response_time = (datetime.now() - start_time).total_seconds()
                
                self.results["response_times"].append(response_time)
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Conversation started: ID={data.get('conversation_id')}")
                    print(f"   Response time: {response_time:.2f}s")
                    print(f"   Initial message: {data.get('message', '')[:100]}...")
                    return data
                else:
                    error_text = await response.text()
                    self.results["errors"].append(f"Start conversation failed: {response.status} - {error_text}")
                    print(f"❌ Start conversation failed: {response.status}")
                    print(f"   Error: {error_text}")
                    return {}
        except Exception as e:
            self.results["errors"].append(f"Start conversation error: {str(e)}")
            print(f"❌ Start conversation error: {e}")
            return {}
    
    async def test_conversation_message(self, conversation_id: str) -> Dict[str, Any]:
        """Test POST /conversations/{id}/message endpoint."""
        print(f"\n🔍 Testing /conversations/{conversation_id}/message endpoint...")
        
        test_messages = [
            "Hola, me gustaría saber más sobre NGX",
            "¿Cuál es el precio de sus programas?",
            "¿Cómo funciona el sistema HIE que mencionan?",
            "Me preocupa no tener tiempo suficiente",
            "¿Qué garantías ofrecen?"
        ]
        
        results = []
        
        for message in test_messages:
            try:
                async with aiohttp.ClientSession() as session:
                    start_time = datetime.now()
                    response = await session.post(
                        f"{self.api_url}/conversations/{conversation_id}/message",
                        json={"message": message},
                        headers={"Content-Type": "application/json"}
                    )
                    response_time = (datetime.now() - start_time).total_seconds()
                    
                    self.results["response_times"].append(response_time)
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Message sent successfully")
                        print(f"   User: {message}")
                        print(f"   Agent: {data.get('message', '')[:100]}...")
                        print(f"   Response time: {response_time:.2f}s")
                        
                        results.append({
                            "user_message": message,
                            "agent_response": data.get('message', ''),
                            "response_time": response_time,
                            "success": True
                        })
                    else:
                        error_text = await response.text()
                        self.results["errors"].append(f"Send message failed: {response.status} - {error_text}")
                        print(f"❌ Send message failed: {response.status}")
                        print(f"   Error: {error_text}")
                        
                        results.append({
                            "user_message": message,
                            "error": error_text,
                            "response_time": response_time,
                            "success": False
                        })
                    
                    # Small delay between messages
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.results["errors"].append(f"Send message error: {str(e)}")
                print(f"❌ Send message error: {e}")
                results.append({
                    "user_message": message,
                    "error": str(e),
                    "success": False
                })
        
        return {"messages": results}
    
    async def test_conversation_get(self, conversation_id: str) -> bool:
        """Test GET /conversations/{id} endpoint."""
        print(f"\n🔍 Testing GET /conversations/{conversation_id} endpoint...")
        
        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                response = await session.get(f"{self.api_url}/conversations/{conversation_id}")
                response_time = (datetime.now() - start_time).total_seconds()
                
                self.results["response_times"].append(response_time)
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Retrieved conversation successfully")
                    print(f"   Messages count: {len(data.get('messages', []))}")
                    print(f"   Response time: {response_time:.2f}s")
                    return True
                else:
                    self.results["errors"].append(f"Get conversation failed: {response.status}")
                    print(f"❌ Get conversation failed: {response.status}")
                    return False
        except Exception as e:
            self.results["errors"].append(f"Get conversation error: {str(e)}")
            print(f"❌ Get conversation error: {e}")
            return False
    
    async def test_analytics_endpoint(self, conversation_id: str) -> bool:
        """Test GET /analytics/conversations/{id} endpoint."""
        print(f"\n🔍 Testing /analytics/conversations/{conversation_id} endpoint...")
        
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.get(f"{self.api_url}/analytics/conversations/{conversation_id}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Analytics retrieved successfully")
                    print(f"   Metrics: {list(data.keys())}")
                    return True
                else:
                    print(f"❌ Analytics failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Analytics error: {e}")
            return False
    
    async def run_validation_suite(self):
        """Run complete validation suite."""
        print("🚀 NGX Voice Sales Agent - Real API Validation Suite")
        print("=" * 60)
        print(f"API URL: {self.api_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Test 1: Health Check
        self.results["endpoints_tested"] += 1
        if await self.test_health_endpoint():
            self.results["endpoints_passed"] += 1
        else:
            self.results["endpoints_failed"] += 1
        
        # Test 2: Start Conversation
        self.results["endpoints_tested"] += 1
        conversation_data = await self.test_conversation_start()
        if conversation_data.get("conversation_id"):
            self.results["endpoints_passed"] += 1
            conversation_id = conversation_data["conversation_id"]
            
            # Test 3: Send Messages
            self.results["endpoints_tested"] += 1
            message_results = await self.test_conversation_message(conversation_id)
            successful_messages = sum(1 for m in message_results["messages"] if m["success"])
            if successful_messages > 0:
                self.results["endpoints_passed"] += 1
            else:
                self.results["endpoints_failed"] += 1
            
            # Test 4: Get Conversation
            self.results["endpoints_tested"] += 1
            if await self.test_conversation_get(conversation_id):
                self.results["endpoints_passed"] += 1
            else:
                self.results["endpoints_failed"] += 1
            
            # Test 5: Analytics
            self.results["endpoints_tested"] += 1
            if await self.test_analytics_endpoint(conversation_id):
                self.results["endpoints_passed"] += 1
            else:
                self.results["endpoints_failed"] += 1
        else:
            self.results["endpoints_failed"] += 1
        
        # Generate Report
        self._generate_report()
    
    def _generate_report(self):
        """Generate validation report."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION REPORT")
        print("=" * 60)
        
        # Overall Results
        success_rate = (self.results["endpoints_passed"] / self.results["endpoints_tested"] * 100) if self.results["endpoints_tested"] > 0 else 0
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
        print(f"   Endpoints Tested: {self.results['endpoints_tested']}")
        print(f"   ✅ Passed: {self.results['endpoints_passed']}")
        print(f"   ❌ Failed: {self.results['endpoints_failed']}")
        
        # Response Times
        if self.results["response_times"]:
            avg_response_time = sum(self.results["response_times"]) / len(self.results["response_times"])
            max_response_time = max(self.results["response_times"])
            min_response_time = min(self.results["response_times"])
            
            print(f"\n⚡ Performance Metrics:")
            print(f"   Average Response Time: {avg_response_time:.2f}s")
            print(f"   Fastest Response: {min_response_time:.2f}s")
            print(f"   Slowest Response: {max_response_time:.2f}s")
            
            # Check against target
            if avg_response_time < 0.5:
                print(f"   ✅ MEETS TARGET (<0.5s)")
            else:
                print(f"   ❌ MISSES TARGET (target: <0.5s)")
        
        # Errors
        if self.results["errors"]:
            print(f"\n❌ Errors Found ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"   - {error}")
        
        # Final Verdict
        print("\n" + "=" * 60)
        if success_rate >= 80 and avg_response_time < 0.5:
            print("✅ SYSTEM READY FOR BETA")
        else:
            print("❌ SYSTEM NOT READY - NEEDS FIXES")
        print("=" * 60)
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/results/real_api_validation_{timestamp}.json"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "api_url": self.api_url,
                "results": self.results,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time if self.results["response_times"] else None
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")


async def main():
    """Run the real API validation."""
    validator = APIRealValidator()
    
    try:
        await validator.run_validation_suite()
    except KeyboardInterrupt:
        print("\n\n⚠️ Validation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check for required environment variables
    if not OPENAI_API_KEY:
        print("⚠️ Warning: OPENAI_API_KEY not set. Some features may not work.")
    
    print("Starting API validation in 3 seconds...")
    print("Make sure the API is running at: " + API_URL)
    print("Press Ctrl+C to cancel\n")
    
    import time
    time.sleep(3)
    
    asyncio.run(main())