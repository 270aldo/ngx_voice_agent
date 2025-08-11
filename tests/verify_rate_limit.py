#!/usr/bin/env python3
"""
Test para verificar que el rate limiting está funcionando correctamente
"""

import asyncio
import aiohttp
import time
from datetime import datetime

async def test_rate_limit():
    """Prueba el rate limiting con requests rápidos"""
    print("🔒 Testing Rate Limiting Implementation")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Los límites configurados son:
    # - 60 requests por minuto
    # - 1000 requests por hora
    
    print("\n📊 Current Rate Limits:")
    print("  - Per minute: 60 requests")
    print("  - Per hour: 1000 requests")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Verificar que funciona normalmente
        print("\n🔍 Test 1: Normal requests (should pass)")
        successful = 0
        for i in range(10):
            try:
                async with session.get(f"{base_url}/health") as resp:
                    if resp.status == 200:
                        successful += 1
                    await asyncio.sleep(0.1)  # 100ms entre requests
            except Exception as e:
                print(f"  Error: {e}")
        
        print(f"  ✅ {successful}/10 requests successful")
        
        # Test 2: Bombardear con requests para activar rate limit
        print("\n🔍 Test 2: Rapid fire requests (should trigger rate limit)")
        start_time = time.time()
        responses = {"200": 0, "429": 0, "other": 0}
        
        # Enviar 100 requests lo más rápido posible
        tasks = []
        for i in range(100):
            async def make_request(idx):
                try:
                    async with session.get(f"{base_url}/api/v1/conversations") as resp:
                        if resp.status == 200:
                            responses["200"] += 1
                        elif resp.status == 429:
                            responses["429"] += 1
                            # Obtener headers de rate limit
                            if responses["429"] == 1:  # Solo imprimir una vez
                                print("\n  Rate limit headers detected:")
                                for header, value in resp.headers.items():
                                    if "rate" in header.lower() or "limit" in header.lower():
                                        print(f"    {header}: {value}")
                        else:
                            responses["other"] += 1
                        return resp.status
                except aiohttp.ClientResponseError as e:
                    if e.status == 429:
                        responses["429"] += 1
                        if responses["429"] == 1:
                            print("\n  ✅ Rate limiting triggered! (HTTP 429)")
                    else:
                        responses["other"] += 1
                    return e.status
                except Exception as e:
                    responses["other"] += 1
                    return None
            
            tasks.append(make_request(i))
        
        # Ejecutar todos los requests concurrentemente
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        print(f"\n  Results after {elapsed:.2f} seconds:")
        print(f"    - 200 OK: {responses['200']}")
        print(f"    - 429 Too Many Requests: {responses['429']}")
        print(f"    - Other/Errors: {responses['other']}")
        
        # Test 3: Verificar recuperación después de esperar
        print("\n🔍 Test 3: Recovery after waiting")
        print("  Waiting 2 seconds...")
        await asyncio.sleep(2)
        
        recovery_successful = 0
        for i in range(5):
            try:
                async with session.get(f"{base_url}/health") as resp:
                    if resp.status == 200:
                        recovery_successful += 1
                    await asyncio.sleep(0.2)
            except Exception as e:
                print(f"  Error: {e}")
        
        print(f"  ✅ {recovery_successful}/5 requests successful after cooldown")
        
        # Resumen
        print("\n" + "=" * 60)
        print("📊 RATE LIMITING TEST SUMMARY")
        print("=" * 60)
        
        if responses["429"] > 0:
            print("✅ Rate limiting is ACTIVE and WORKING!")
            print(f"   - Blocked {responses['429']} requests out of 100")
            print(f"   - Allowed {responses['200']} requests (within limits)")
        else:
            print("❌ Rate limiting is NOT working!")
            print("   - All 100 requests were allowed")
            print("   - This is a security vulnerability!")
        
        # Verificar si los límites son razonables
        if responses["200"] > 60:
            print("\n⚠️  WARNING: More than 60 requests passed in rapid succession")
            print("   The per-minute limit might not be enforced correctly")

if __name__ == "__main__":
    asyncio.run(test_rate_limit())