#!/usr/bin/env python3
"""
Simple test to verify rate limiting
"""
import requests
import time

print("Testing rate limiting...")
print("Configured limits: 60/min, 1000/hour")
print("-" * 40)

base_url = "http://localhost:8000"

# Send 70 requests rapidly (more than 60/min limit)
success = 0
rate_limited = 0
errors = 0

print("\nSending 70 rapid requests...")
for i in range(70):
    try:
        # Use a non-whitelisted endpoint
        resp = requests.post(f"{base_url}/api/v1/conversations/start", 
                           json={"customer_data": {"name": "Test"}})
        if resp.status_code == 200:
            success += 1
        elif resp.status_code == 429:
            rate_limited += 1
            if rate_limited == 1:
                print(f"\n✅ Rate limit triggered at request #{i+1}")
                print(f"   Response: {resp.text}")
                if "Retry-After" in resp.headers:
                    print(f"   Retry-After: {resp.headers['Retry-After']}s")
        else:
            errors += 1
    except Exception as e:
        errors += 1
        print(f"Error: {e}")

print(f"\nResults:")
print(f"  Success: {success}")
print(f"  Rate Limited (429): {rate_limited}")
print(f"  Errors: {errors}")

if rate_limited > 0:
    print("\n✅ RATE LIMITING IS WORKING!")
else:
    print("\n❌ RATE LIMITING IS NOT WORKING!")