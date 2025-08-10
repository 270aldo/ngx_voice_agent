#!/usr/bin/env python3
"""
Production Load Test with Rate Limits

Tests the system under production-like conditions with rate limiting enabled.
Simulates real-world usage patterns and verifies rate limit enforcement.
"""

import asyncio
import aiohttp
import time
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics
import random
from dataclasses import dataclass
from collections import defaultdict
import jwt

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class TestUser:
    """Represents a test user for load testing."""
    id: str
    email: str
    token: Optional[str] = None
    role: str = "user"  # user, admin, premium
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000


@dataclass
class TestResult:
    """Result of a single request."""
    user_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: datetime
    rate_limited: bool = False
    error: Optional[str] = None
    headers: Dict[str, str] = None


class ProductionLoadTester:
    """Production load tester with rate limit validation."""
    
    def __init__(self, base_url: str = "http://localhost:8000/v1"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.rate_limit_hits = defaultdict(int)
        self.users: List[TestUser] = []
        self.start_time = None
        self.end_time = None
    
    def create_test_users(self, count: int) -> List[TestUser]:
        """Create test users with different roles."""
        users = []
        
        # User distribution
        # 70% regular users, 20% premium users, 10% admin users
        for i in range(count):
            if i < int(count * 0.1):  # 10% admin
                role = "admin"
                rate_limit_per_minute = 0  # No limit for admins
                rate_limit_per_hour = 0
            elif i < int(count * 0.3):  # 20% premium
                role = "premium"
                rate_limit_per_minute = 120  # Double regular limit
                rate_limit_per_hour = 2000
            else:  # 70% regular
                role = "user"
                rate_limit_per_minute = 60
                rate_limit_per_hour = 1000
            
            user = TestUser(
                id=f"user_{i:04d}",
                email=f"test_{i}@example.com",
                role=role,
                rate_limit_per_minute=rate_limit_per_minute,
                rate_limit_per_hour=rate_limit_per_hour
            )
            users.append(user)
        
        return users
    
    async def authenticate_user(self, session: aiohttp.ClientSession, user: TestUser) -> bool:
        """Authenticate a test user and get JWT token."""
        # In production, this would actually authenticate
        # For testing, we'll generate a mock JWT
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Mock token generation (in production, get from /auth/login)
        user.token = jwt.encode(payload, "test_secret", algorithm="HS256")
        return True
    
    async def make_request(
        self, 
        session: aiohttp.ClientSession, 
        user: TestUser,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None
    ) -> TestResult:
        """Make a single request and record results."""
        start_time = time.time()
        headers = {}
        
        if user.token:
            headers["Authorization"] = f"Bearer {user.token}"
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time_ms = (time.time() - start_time) * 1000
                
                # Extract rate limit headers
                rate_limit_headers = {
                    "limit": response.headers.get("X-Rate-Limit-Limit"),
                    "remaining": response.headers.get("X-Rate-Limit-Remaining"),
                    "reset": response.headers.get("X-Rate-Limit-Reset")
                }
                
                # Check if rate limited
                rate_limited = response.status == 429
                if rate_limited:
                    self.rate_limit_hits[user.id] += 1
                
                result = TestResult(
                    user_id=user.id,
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status,
                    response_time_ms=response_time_ms,
                    timestamp=datetime.now(),
                    rate_limited=rate_limited,
                    headers=rate_limit_headers
                )
                
                return result
                
        except asyncio.TimeoutError:
            return TestResult(
                user_id=user.id,
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error="Timeout"
            )
        except Exception as e:
            return TestResult(
                user_id=user.id,
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def simulate_user_behavior(
        self, 
        session: aiohttp.ClientSession,
        user: TestUser,
        duration_seconds: int
    ):
        """Simulate realistic user behavior patterns."""
        start_time = time.time()
        
        # Authenticate user
        await self.authenticate_user(session, user)
        
        # Define typical user flow
        user_flows = [
            # Flow 1: Browse and start conversation
            [
                ("/health", "GET", None),
                ("/conversation/start", "POST", {
                    "customer_info": {
                        "name": f"User {user.id}",
                        "email": user.email,
                        "business_type": "gym"
                    }
                }),
                ("/conversation/{conv_id}/message", "POST", {
                    "message": "¿Cuánto cuesta el servicio?"
                }),
                ("/conversation/{conv_id}/message", "POST", {
                    "message": "¿Qué incluye?"
                }),
                ("/analytics/conversation/{conv_id}", "GET", None)
            ],
            # Flow 2: Quick price check
            [
                ("/predictive/needs/predict", "POST", {
                    "conversation_id": "test",
                    "messages": [{"role": "user", "content": "Need pricing"}]
                }),
                ("/qualification/score", "POST", {
                    "customer_info": {"name": "Test", "business_type": "studio"}
                })
            ],
            # Flow 3: Heavy usage (premium users)
            [
                ("/conversation/start", "POST", {
                    "customer_info": {"name": "Premium User", "business_type": "trainer"}
                }),
                ("/predictive/objection/predict", "POST", {
                    "conversation_id": "test",
                    "messages": []
                }),
                ("/predictive/conversion/predict", "POST", {
                    "conversation_id": "test",
                    "messages": []
                }),
                ("/analytics/aggregate", "GET", None)
            ]
        ]
        
        # Select flow based on user role
        if user.role == "admin":
            flow = user_flows[2]  # Heavy usage
        elif user.role == "premium":
            flow = random.choice(user_flows)
        else:
            flow = random.choice(user_flows[:2])  # Regular users
        
        conv_id = None
        requests_made = 0
        
        while time.time() - start_time < duration_seconds:
            for endpoint, method, data in flow:
                # Replace conv_id placeholder
                if conv_id and "{conv_id}" in endpoint:
                    endpoint = endpoint.replace("{conv_id}", conv_id)
                
                # Make request
                result = await self.make_request(session, user, endpoint, method, data)
                self.results.append(result)
                requests_made += 1
                
                # Extract conversation ID if starting new conversation
                if endpoint == "/conversation/start" and result.status_code == 200:
                    # In real test, would parse response
                    conv_id = f"conv_{user.id}_{requests_made}"
                
                # Simulate thinking time between requests
                if not result.rate_limited:
                    think_time = random.uniform(0.5, 3.0)
                else:
                    # If rate limited, wait longer
                    think_time = random.uniform(5.0, 10.0)
                
                await asyncio.sleep(think_time)
                
                # Check if we should stop
                if time.time() - start_time >= duration_seconds:
                    break
        
        print(f"User {user.id} ({user.role}) completed {requests_made} requests")
    
    async def run_load_test(
        self,
        num_users: int = 50,
        duration_seconds: int = 300,  # 5 minutes
        ramp_up_seconds: int = 30
    ):
        """Run the production load test."""
        print("\n" + "="*80)
        print("🚀 PRODUCTION LOAD TEST WITH RATE LIMITS")
        print("="*80)
        print(f"Users: {num_users}")
        print(f"Duration: {duration_seconds}s")
        print(f"Ramp-up: {ramp_up_seconds}s")
        print(f"Base URL: {self.base_url}")
        print("="*80)
        
        self.start_time = datetime.now()
        
        # Create test users
        print("\n📋 Creating test users...")
        self.users = self.create_test_users(num_users)
        
        # Count by role
        role_counts = defaultdict(int)
        for user in self.users:
            role_counts[user.role] += 1
        
        print(f"User distribution:")
        for role, count in role_counts.items():
            print(f"  - {role}: {count} users")
        
        # Create session with connection pooling
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Start users with ramp-up
            print(f"\n🚦 Starting users with {ramp_up_seconds}s ramp-up...")
            
            tasks = []
            for i, user in enumerate(self.users):
                # Calculate delay for this user
                delay = (i / num_users) * ramp_up_seconds
                
                # Create task with delay
                task = self._start_user_with_delay(
                    session, user, duration_seconds, delay
                )
                tasks.append(task)
            
            # Wait for all users to complete
            print("\n⏳ Load test in progress...")
            await asyncio.gather(*tasks)
        
        self.end_time = datetime.now()
        
        # Analyze results
        print("\n📊 Analyzing results...")
        self._analyze_results()
    
    async def _start_user_with_delay(
        self,
        session: aiohttp.ClientSession,
        user: TestUser,
        duration: int,
        delay: float
    ):
        """Start a user simulation after a delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        
        await self.simulate_user_behavior(session, user, duration)
    
    def _analyze_results(self):
        """Analyze test results and generate report."""
        if not self.results:
            print("❌ No results to analyze")
            return
        
        # Overall statistics
        total_requests = len(self.results)
        successful_requests = len([r for r in self.results if 200 <= r.status_code < 300])
        rate_limited_requests = len([r for r in self.results if r.rate_limited])
        failed_requests = len([r for r in self.results if r.status_code == 0 or r.status_code >= 500])
        
        # Response times (excluding failed requests)
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms > 0 and not r.rate_limited]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p50_response_time = statistics.median(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        else:
            avg_response_time = p50_response_time = p95_response_time = p99_response_time = 0
        
        # Rate limit analysis by user role
        rate_limit_by_role = defaultdict(lambda: {"users": 0, "hits": 0})
        for user in self.users:
            role = user.role
            rate_limit_by_role[role]["users"] += 1
            rate_limit_by_role[role]["hits"] += self.rate_limit_hits.get(user.id, 0)
        
        # Requests per second
        test_duration = (self.end_time - self.start_time).total_seconds()
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        # Status code distribution
        status_distribution = defaultdict(int)
        for result in self.results:
            status_distribution[result.status_code] += 1
        
        # Endpoint performance
        endpoint_stats = defaultdict(lambda: {"count": 0, "total_time": 0, "errors": 0})
        for result in self.results:
            stats = endpoint_stats[result.endpoint]
            stats["count"] += 1
            stats["total_time"] += result.response_time_ms
            if result.status_code >= 400:
                stats["errors"] += 1
        
        # Generate report
        print("\n" + "="*80)
        print("📊 LOAD TEST RESULTS")
        print("="*80)
        
        print(f"\n⏱️  Test Duration: {test_duration:.1f} seconds")
        print(f"👥 Total Users: {len(self.users)}")
        print(f"📨 Total Requests: {total_requests:,}")
        print(f"📈 Requests/Second: {requests_per_second:.2f}")
        
        print(f"\n✅ Success Rate: {(successful_requests/total_requests*100):.2f}%")
        print(f"🚫 Rate Limited: {rate_limited_requests} ({(rate_limited_requests/total_requests*100):.2f}%)")
        print(f"❌ Failed: {failed_requests} ({(failed_requests/total_requests*100):.2f}%)")
        
        print(f"\n⚡ Response Times:")
        print(f"  Average: {avg_response_time:.2f} ms")
        print(f"  Median (P50): {p50_response_time:.2f} ms")
        print(f"  P95: {p95_response_time:.2f} ms")
        print(f"  P99: {p99_response_time:.2f} ms")
        
        print(f"\n🚦 Rate Limiting by Role:")
        for role, data in rate_limit_by_role.items():
            hits_per_user = data["hits"] / data["users"] if data["users"] > 0 else 0
            print(f"  {role}: {data['hits']} hits across {data['users']} users ({hits_per_user:.1f} per user)")
        
        print(f"\n📋 Status Code Distribution:")
        for status, count in sorted(status_distribution.items()):
            percentage = (count / total_requests) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        
        print(f"\n🎯 Top Endpoints by Volume:")
        sorted_endpoints = sorted(
            endpoint_stats.items(), 
            key=lambda x: x[1]["count"], 
            reverse=True
        )[:5]
        
        for endpoint, stats in sorted_endpoints:
            avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
            error_rate = (stats["errors"] / stats["count"] * 100) if stats["count"] > 0 else 0
            print(f"  {endpoint}:")
            print(f"    Requests: {stats['count']}")
            print(f"    Avg Time: {avg_time:.2f} ms")
            print(f"    Error Rate: {error_rate:.1f}%")
        
        # Validation checks
        print(f"\n✅ VALIDATION CHECKS:")
        
        # Check 1: Rate limiting is working
        rate_limit_working = rate_limited_requests > 0 if total_requests > 1000 else True
        print(f"  Rate limiting active: {'✅ PASS' if rate_limit_working else '❌ FAIL'}")
        
        # Check 2: Admin users not rate limited
        admin_rate_limited = any(
            self.rate_limit_hits.get(user.id, 0) > 0 
            for user in self.users if user.role == "admin"
        )
        print(f"  Admin bypass working: {'❌ FAIL' if admin_rate_limited else '✅ PASS'}")
        
        # Check 3: Response times acceptable
        response_times_ok = p95_response_time < 1000  # Under 1 second
        print(f"  P95 < 1s: {'✅ PASS' if response_times_ok else '❌ FAIL'} ({p95_response_time:.0f}ms)")
        
        # Check 4: Error rate acceptable
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        error_rate_ok = error_rate < 1.0
        print(f"  Error rate < 1%: {'✅ PASS' if error_rate_ok else '❌ FAIL'} ({error_rate:.2f}%)")
        
        # Save detailed report
        report = {
            "test_info": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": test_duration,
                "total_users": len(self.users),
                "total_requests": total_requests
            },
            "performance": {
                "requests_per_second": requests_per_second,
                "response_times": {
                    "average": avg_response_time,
                    "p50": p50_response_time,
                    "p95": p95_response_time,
                    "p99": p99_response_time
                }
            },
            "rate_limiting": {
                "total_rate_limited": rate_limited_requests,
                "by_role": dict(rate_limit_by_role)
            },
            "errors": {
                "total_failed": failed_requests,
                "error_rate_percent": error_rate
            },
            "validation": {
                "rate_limiting_active": rate_limit_working,
                "admin_bypass_working": not admin_rate_limited,
                "response_times_acceptable": response_times_ok,
                "error_rate_acceptable": error_rate_ok
            }
        }
        
        report_file = f"production_load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        # Overall verdict
        all_checks_passed = all([
            rate_limit_working,
            not admin_rate_limited,
            response_times_ok,
            error_rate_ok
        ])
        
        if all_checks_passed:
            print("\n✅ PRODUCTION LOAD TEST PASSED")
            print("   System is ready for production traffic with rate limits enabled")
        else:
            print("\n⚠️  PRODUCTION LOAD TEST FAILED")
            print("   Review the failures above before deploying to production")


async def main():
    """Run production load test."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Production Load Test with Rate Limits')
    parser.add_argument('--users', type=int, default=50, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--ramp-up', type=int, default=30, help='Ramp-up time in seconds')
    parser.add_argument('--url', type=str, default='http://localhost:8000/v1', help='Base API URL')
    
    args = parser.parse_args()
    
    # Create tester
    tester = ProductionLoadTester(base_url=args.url)
    
    # Run test
    await tester.run_load_test(
        num_users=args.users,
        duration_seconds=args.duration,
        ramp_up_seconds=args.ramp_up
    )


if __name__ == "__main__":
    asyncio.run(main())