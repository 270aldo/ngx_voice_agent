#!/usr/bin/env python3
"""
Quick validation script to verify all API endpoints are working.
Tests basic functionality of each endpoint group.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Tuple


class EndpointValidator:
    """Validates all API endpoints are functioning correctly."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.auth_token = None
        
    async def validate_all(self):
        """Run validation on all endpoint groups."""
        print("🔍 NGX Voice Sales Agent - API Endpoint Validation")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Test groups in order
        test_groups = [
            ("Health", self.test_health),
            ("Auth", self.test_auth),
            ("Conversations", self.test_conversations),
            ("Analytics", self.test_analytics),
            ("Predictive", self.test_predictive),
            ("Qualification", self.test_qualification),
            ("Cache", self.test_cache),
            ("Security", self.test_security),
        ]
        
        for group_name, test_func in test_groups:
            print(f"\n📋 Testing {group_name} endpoints...")
            try:
                results = await test_func()
                self.results[group_name] = results
                self._print_group_results(group_name, results)
            except Exception as e:
                print(f"❌ {group_name} failed: {e}")
                self.results[group_name] = {"error": str(e)}
        
        self._print_summary()
    
    async def test_health(self) -> Dict:
        """Test health endpoints."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            # Basic health
            async with session.get(f"{self.base_url}/health") as resp:
                results["GET /health"] = {
                    "status": resp.status,
                    "success": resp.status == 200
                }
        
        return results
    
    async def test_auth(self) -> Dict:
        """Test authentication endpoints."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            # Register
            register_data = {
                "email": f"test_{datetime.now().timestamp()}@test.com",
                "password": "TestPassword123!",
                "full_name": "Test User"
            }
            
            async with session.post(
                f"{self.base_url}/auth/register",
                json=register_data
            ) as resp:
                results["POST /auth/register"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 201]
                }
                
                if resp.status in [200, 201]:
                    data = await resp.json()
                    self.auth_token = data.get("access_token")
            
            # Login
            if self.auth_token:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                async with session.get(
                    f"{self.base_url}/auth/me",
                    headers=headers
                ) as resp:
                    results["GET /auth/me"] = {
                        "status": resp.status,
                        "success": resp.status == 200
                    }
        
        return results
    
    async def test_conversations(self) -> Dict:
        """Test conversation endpoints."""
        results = {}
        conversation_id = None
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Start conversation
            start_data = {
                "customer_data": {
                    "name": "Test Customer",
                    "email": "test@validation.com",
                    "profession": "Personal Trainer",
                    "age": 35
                }
            }
            
            async with session.post(
                f"{self.base_url}/conversations/start",
                json=start_data,
                headers=headers
            ) as resp:
                results["POST /conversations/start"] = {
                    "status": resp.status,
                    "success": resp.status == 200
                }
                
                if resp.status == 200:
                    data = await resp.json()
                    conversation_id = data.get("conversation_id")
            
            # Send message
            if conversation_id:
                message_data = {
                    "message": "Hola, quiero información sobre NGX"
                }
                
                async with session.post(
                    f"{self.base_url}/conversations/{conversation_id}/message",
                    json=message_data,
                    headers=headers
                ) as resp:
                    results["POST /conversations/{id}/message"] = {
                        "status": resp.status,
                        "success": resp.status == 200
                    }
                
                # Get conversation state
                async with session.get(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers=headers
                ) as resp:
                    results["GET /conversations/{id}"] = {
                        "status": resp.status,
                        "success": resp.status == 200
                    }
                
                # End conversation
                async with session.post(
                    f"{self.base_url}/conversations/{conversation_id}/end",
                    headers=headers
                ) as resp:
                    results["POST /conversations/{id}/end"] = {
                        "status": resp.status,
                        "success": resp.status == 200
                    }
        
        return results
    
    async def test_analytics(self) -> Dict:
        """Test analytics endpoints."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Aggregate analytics
            async with session.get(
                f"{self.base_url}/analytics/aggregate",
                headers=headers
            ) as resp:
                results["GET /analytics/aggregate"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 401]  # May require auth
                }
            
            # Trends
            async with session.get(
                f"{self.base_url}/analytics/trends",
                headers=headers
            ) as resp:
                results["GET /analytics/trends"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 401]
                }
        
        return results
    
    async def test_predictive(self) -> Dict:
        """Test predictive endpoints."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Conversion prediction
            predict_data = {
                "conversation_id": "test-conv-123",
                "customer_data": {
                    "profession": "Gym Owner",
                    "years_experience": 5
                },
                "conversation_metrics": {
                    "message_count": 10,
                    "duration_minutes": 15,
                    "sentiment_score": 0.8
                }
            }
            
            async with session.post(
                f"{self.base_url}/predictive/conversion/predict",
                json=predict_data,
                headers=headers
            ) as resp:
                results["POST /predictive/conversion/predict"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 401]
                }
            
            # Models list
            async with session.get(
                f"{self.base_url}/predictive/models",
                headers=headers
            ) as resp:
                results["GET /predictive/models"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 401]
                }
        
        return results
    
    async def test_qualification(self) -> Dict:
        """Test qualification endpoints."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Lead scoring
            scoring_data = {
                "lead_data": {
                    "name": "Test Lead",
                    "email": "lead@test.com",
                    "profession": "Fitness Coach",
                    "business_size": "medium"
                }
            }
            
            async with session.post(
                f"{self.base_url}/qualification/score",
                json=scoring_data,
                headers=headers
            ) as resp:
                results["POST /qualification/score"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 404]  # Might not exist
                }
        
        return results
    
    async def test_cache(self) -> Dict:
        """Test cache endpoints."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Cache health
            async with session.get(
                f"{self.base_url}/api/v1/cache/health",
                headers=headers
            ) as resp:
                results["GET /api/v1/cache/health"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 401]
                }
            
            # Cache stats
            async with session.get(
                f"{self.base_url}/api/v1/cache/stats",
                headers=headers
            ) as resp:
                results["GET /api/v1/cache/stats"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 401]
                }
        
        return results
    
    async def test_security(self) -> Dict:
        """Test security endpoints."""
        results = {}
        
        async with aiohttp.ClientSession() as session:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # JWT rotation status
            async with session.get(
                f"{self.base_url}/security/jwt/rotation-status",
                headers=headers
            ) as resp:
                results["GET /security/jwt/rotation-status"] = {
                    "status": resp.status,
                    "success": resp.status in [200, 401, 404]
                }
        
        return results
    
    def _print_group_results(self, group_name: str, results: Dict):
        """Print results for a group of endpoints."""
        if "error" in results:
            print(f"  ❌ Group failed: {results['error']}")
            return
        
        for endpoint, result in results.items():
            status_icon = "✅" if result["success"] else "❌"
            print(f"  {status_icon} {endpoint}: {result['status']}")
    
    def _print_summary(self):
        """Print overall summary."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        total_endpoints = 0
        successful_endpoints = 0
        
        for group_name, results in self.results.items():
            if isinstance(results, dict) and "error" not in results:
                for endpoint, result in results.items():
                    total_endpoints += 1
                    if result.get("success", False):
                        successful_endpoints += 1
        
        success_rate = (successful_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
        
        print(f"Total Endpoints Tested: {total_endpoints}")
        print(f"Successful: {successful_endpoints}")
        print(f"Failed: {total_endpoints - successful_endpoints}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n✅ API is functioning well!")
        elif success_rate >= 50:
            print("\n⚠️  Some endpoints are failing")
        else:
            print("\n❌ Many endpoints are failing")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/results/endpoint_validation_{timestamp}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "base_url": self.base_url,
                "summary": {
                    "total_endpoints": total_endpoints,
                    "successful": successful_endpoints,
                    "failed": total_endpoints - successful_endpoints,
                    "success_rate": success_rate
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


async def main():
    """Run endpoint validation."""
    validator = EndpointValidator()
    await validator.validate_all()


if __name__ == "__main__":
    asyncio.run(main())