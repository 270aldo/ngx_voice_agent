#!/usr/bin/env python3
"""
Endpoint Validation Script for NGX Voice Sales Agent
Validates all API endpoints are working before running performance tests.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys


class EndpointValidator:
    """Validates all API endpoints are functioning correctly."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.auth_token = None
        
    def validate_endpoint(self, method: str, path: str, 
                         data: Dict = None, headers: Dict = None,
                         expected_status: int = 200) -> Tuple[bool, float, str]:
        """Test a single endpoint."""
        url = f"{self.base_url}{path}"
        headers = headers or {}
        
        if self.auth_token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                return False, 0, f"Unknown method: {method}"
                
            elapsed_ms = (time.time() - start_time) * 1000
            
            if response.status_code == expected_status:
                return True, elapsed_ms, "OK"
            else:
                return False, elapsed_ms, f"Status {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, 0, str(e)
    
    def run_validation(self):
        """Run validation for all endpoints."""
        print("=" * 60)
        print(f"NGX API Endpoint Validation - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test data
        test_user = {
            "username": f"test_{int(time.time())}@example.com",
            "password": "TestPass123!"
        }
        
        customer_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "age": 35,
            "profession": "Personal Trainer",
            "location": "Miami, FL",
            "pain_points": ["client retention", "scaling business"],
            "goals": ["automate operations", "increase revenue"]
        }
        
        # Endpoint tests
        tests = [
            # Health check
            ("GET", "/health", None, None, 200, "Health Check"),
            
            # Authentication
            ("POST", "/auth/register", test_user, None, 200, "User Registration"),
            ("POST", "/auth/login", {
                "username": test_user["username"],
                "password": test_user["password"]
            }, None, 200, "User Login"),
            
            # Conversations
            ("POST", "/conversations/start", {
                "customer_data": customer_data
            }, None, 200, "Start Conversation"),
            
            # Analytics
            ("GET", "/analytics/aggregate", None, None, 200, "Get Analytics"),
            
            # Predictive
            ("GET", "/predictive/models", None, None, 200, "List Predictive Models"),
            
            # Metrics
            ("GET", "/metrics", None, None, 200, "Prometheus Metrics"),
            
            # Cache
            ("GET", "/api/v1/cache/health", None, None, 200, "Cache Health"),
        ]
        
        all_passed = True
        
        for method, path, data, headers, expected_status, description in tests:
            success, elapsed_ms, message = self.validate_endpoint(
                method, path, data, headers, expected_status
            )
            
            # Extract auth token if login successful
            if path == "/auth/login" and success:
                try:
                    response = requests.post(f"{self.base_url}{path}", 
                                           json=data, headers=headers)
                    self.auth_token = response.json().get("access_token")
                except:
                    pass
            
            # Extract conversation_id for subsequent tests
            if path == "/conversations/start" and success:
                try:
                    response = requests.post(f"{self.base_url}{path}", 
                                           json=data, headers={"Authorization": f"Bearer {self.auth_token}"})
                    conversation_id = response.json().get("conversation_id")
                    
                    # Add dynamic conversation tests
                    tests.extend([
                        ("POST", f"/conversations/{conversation_id}/message", {
                            "message": "¿Cuál es el precio de sus servicios?"
                        }, None, 200, "Send Message"),
                        ("GET", f"/conversations/{conversation_id}", None, None, 200, "Get Conversation"),
                        ("POST", f"/conversations/{conversation_id}/end", None, None, 200, "End Conversation"),
                    ])
                except:
                    pass
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} | {method:6} | {path:40} | {elapsed_ms:7.1f}ms | {description:20} | {message}")
            
            self.results.append({
                "timestamp": datetime.now().isoformat(),
                "method": method,
                "path": path,
                "description": description,
                "success": success,
                "elapsed_ms": elapsed_ms,
                "message": message
            })
            
            if not success:
                all_passed = False
        
        # Summary
        print("=" * 60)
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        avg_response_time = sum(r["elapsed_ms"] for r in self.results if r["success"]) / max(passed_tests, 1)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"Failed: {failed_tests}")
        print(f"Average Response Time: {avg_response_time:.1f}ms")
        print("=" * 60)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"results/endpoint_validation_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump({
                "test_type": "endpoint_validation",
                "timestamp": timestamp,
                "base_url": self.base_url,
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "average_response_time_ms": avg_response_time,
                "all_passed": all_passed,
                "results": self.results
            }, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        return all_passed


if __name__ == "__main__":
    validator = EndpointValidator()
    success = validator.run_validation()
    
    if not success:
        print("\n⚠️  Some endpoints failed validation!")
        print("Please fix the issues before running performance tests.")
        sys.exit(1)
    else:
        print("\n✅ All endpoints validated successfully!")
        print("Ready to run performance tests.")