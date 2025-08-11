#!/usr/bin/env python3
"""
Real-World Scenario Testing for NGX Voice Sales Agent
Simulates realistic usage patterns including peak hours, geographic distribution, and user behavior.
"""

import asyncio
import aiohttp
import time
import random
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class TimeOfDay(Enum):
    """Time periods with different load characteristics."""
    EARLY_MORNING = "early_morning"  # 5-7 AM
    MORNING_PEAK = "morning_peak"    # 7-9 AM
    MID_MORNING = "mid_morning"      # 9-11 AM
    LUNCH = "lunch"                  # 11 AM-1 PM
    AFTERNOON = "afternoon"          # 1-4 PM
    EVENING_PEAK = "evening_peak"    # 4-7 PM
    EVENING = "evening"              # 7-10 PM
    NIGHT = "night"                  # 10 PM-5 AM


@dataclass
class UserProfile:
    """Realistic user profile for testing."""
    id: str
    name: str
    profession: str
    timezone: str
    typical_session_length: int  # minutes
    message_frequency: float  # messages per minute
    conversion_probability: float
    price_sensitivity: str  # low, medium, high
    technical_level: str  # basic, intermediate, advanced


class RealWorldScenarioTester:
    """Simulates real-world usage patterns."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.user_profiles = self._generate_user_profiles()
        self.time_patterns = self._define_time_patterns()
        
    def _generate_user_profiles(self) -> List[UserProfile]:
        """Generate diverse user profiles based on real data."""
        profiles = []
        
        # Define profession distributions
        professions = [
            ("Personal Trainer", 0.35),
            ("Gym Owner", 0.20),
            ("Fitness Coach", 0.15),
            ("Nutritionist", 0.10),
            ("Physical Therapist", 0.08),
            ("Wellness Coach", 0.07),
            ("Studio Owner", 0.05)
        ]
        
        # Generate 1000 user profiles
        for i in range(1000):
            # Select profession based on distribution
            prof_roll = random.random()
            cumulative = 0
            profession = "Personal Trainer"
            for prof, prob in professions:
                cumulative += prob
                if prof_roll <= cumulative:
                    profession = prof
                    break
            
            # Assign characteristics based on profession
            if profession in ["Gym Owner", "Studio Owner"]:
                session_length = random.randint(15, 30)
                conversion_prob = 0.25
                price_sensitivity = random.choice(["low", "medium"])
                technical_level = "advanced"
            elif profession == "Personal Trainer":
                session_length = random.randint(8, 20)
                conversion_prob = 0.15
                price_sensitivity = random.choice(["medium", "high"])
                technical_level = random.choice(["basic", "intermediate"])
            else:
                session_length = random.randint(10, 25)
                conversion_prob = 0.18
                price_sensitivity = "medium"
                technical_level = "intermediate"
            
            profiles.append(UserProfile(
                id=f"user_{i:04d}",
                name=f"Test {profession} {i}",
                profession=profession,
                timezone=random.choice(["PST", "MST", "CST", "EST"]),
                typical_session_length=session_length,
                message_frequency=random.uniform(0.3, 0.8),
                conversion_probability=conversion_prob,
                price_sensitivity=price_sensitivity,
                technical_level=technical_level
            ))
        
        return profiles
    
    def _define_time_patterns(self) -> Dict[TimeOfDay, Dict[str, Any]]:
        """Define load patterns for different times of day."""
        return {
            TimeOfDay.EARLY_MORNING: {
                "user_percentage": 0.05,
                "avg_session_multiplier": 0.8,
                "conversion_multiplier": 0.9
            },
            TimeOfDay.MORNING_PEAK: {
                "user_percentage": 0.20,
                "avg_session_multiplier": 1.2,
                "conversion_multiplier": 1.1
            },
            TimeOfDay.MID_MORNING: {
                "user_percentage": 0.15,
                "avg_session_multiplier": 1.0,
                "conversion_multiplier": 1.0
            },
            TimeOfDay.LUNCH: {
                "user_percentage": 0.10,
                "avg_session_multiplier": 0.7,
                "conversion_multiplier": 0.8
            },
            TimeOfDay.AFTERNOON: {
                "user_percentage": 0.15,
                "avg_session_multiplier": 1.0,
                "conversion_multiplier": 1.0
            },
            TimeOfDay.EVENING_PEAK: {
                "user_percentage": 0.25,
                "avg_session_multiplier": 1.3,
                "conversion_multiplier": 1.2
            },
            TimeOfDay.EVENING: {
                "user_percentage": 0.08,
                "avg_session_multiplier": 0.9,
                "conversion_multiplier": 1.0
            },
            TimeOfDay.NIGHT: {
                "user_percentage": 0.02,
                "avg_session_multiplier": 0.6,
                "conversion_multiplier": 0.7
            }
        }
    
    async def simulate_user_journey(self, profile: UserProfile, time_period: TimeOfDay,
                                  session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Simulate a complete user journey based on profile."""
        journey = {
            "user_id": profile.id,
            "profile": profile.__dict__,
            "time_period": time_period.value,
            "start_time": datetime.now().isoformat(),
            "events": [],
            "metrics": {}
        }
        
        try:
            # Adjust behavior based on time of day
            time_pattern = self.time_patterns[time_period]
            session_length = profile.typical_session_length * time_pattern["avg_session_multiplier"]
            conversion_prob = profile.conversion_probability * time_pattern["conversion_multiplier"]
            
            # 1. Initial landing
            event = await self._simulate_event(
                "landing",
                {"source": random.choice(["google", "facebook", "direct", "referral"])},
                session, journey
            )
            
            # 2. Start conversation
            conversation_id = await self._start_conversation(profile, session, journey)
            
            if not conversation_id:
                journey["events"].append({"type": "early_exit", "reason": "failed_to_start"})
                return journey
            
            # 3. Conversation flow
            messages_sent = 0
            start_time = time.time()
            
            while (time.time() - start_time) < (session_length * 60):
                # Determine next action
                action_roll = random.random()
                
                if action_roll < 0.7:  # Send message
                    message = self._generate_contextual_message(profile, messages_sent)
                    await self._send_message(conversation_id, message, session, journey)
                    messages_sent += 1
                    
                elif action_roll < 0.85:  # Check recommendations
                    await self._check_recommendations(conversation_id, session, journey)
                    
                elif action_roll < 0.95:  # Calculate ROI
                    await self._calculate_roi(profile, session, journey)
                    
                else:  # Request demo
                    await self._request_demo(conversation_id, session, journey)
                
                # Wait based on message frequency
                wait_time = 60 / profile.message_frequency
                await asyncio.sleep(wait_time + random.uniform(-5, 5))
            
            # 4. Conversion decision
            if random.random() < conversion_prob:
                await self._simulate_conversion(conversation_id, profile, session, journey)
            else:
                await self._simulate_exit(conversation_id, profile, session, journey)
            
            # Calculate journey metrics
            journey["end_time"] = datetime.now().isoformat()
            journey["metrics"] = self._calculate_journey_metrics(journey)
            
        except Exception as e:
            journey["events"].append({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        return journey
    
    async def _simulate_event(self, event_type: str, data: Dict, 
                            session: aiohttp.ClientSession, journey: Dict) -> Dict:
        """Simulate a generic event."""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "duration_ms": 0
        }
        
        journey["events"].append(event)
        return event
    
    async def _start_conversation(self, profile: UserProfile, 
                                session: aiohttp.ClientSession, journey: Dict) -> str:
        """Start a conversation and return conversation ID."""
        start_time = time.time()
        
        try:
            data = {
                "customer_data": {
                    "name": profile.name,
                    "email": f"{profile.id}@test.ngx.com",
                    "profession": profile.profession,
                    "timezone": profile.timezone,
                    "technical_level": profile.technical_level,
                    "price_sensitivity": profile.price_sensitivity
                }
            }
            
            async with session.post(
                f"{self.base_url}/api/v1/conversations/start",
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                duration = (time.time() - start_time) * 1000
                
                event = {
                    "type": "start_conversation",
                    "timestamp": datetime.now().isoformat(),
                    "status": resp.status,
                    "duration_ms": duration
                }
                
                if resp.status == 200:
                    result = await resp.json()
                    conversation_id = result.get("conversation_id")
                    event["conversation_id"] = conversation_id
                    journey["conversation_id"] = conversation_id
                else:
                    conversation_id = None
                    event["error"] = f"Status {resp.status}"
                
                journey["events"].append(event)
                return conversation_id
                
        except Exception as e:
            journey["events"].append({
                "type": "start_conversation_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return None
    
    def _generate_contextual_message(self, profile: UserProfile, messages_sent: int) -> str:
        """Generate realistic message based on profile and conversation stage."""
        if messages_sent == 0:  # Opening
            if profile.price_sensitivity == "high":
                return random.choice([
                    "Hola, busco una solución económica para crecer mi negocio",
                    "¿Cuál es la opción más accesible que tienen?",
                    "Necesito algo que no sea muy caro para empezar"
                ])
            elif profile.technical_level == "advanced":
                return random.choice([
                    "Hola, ¿cómo se integra NGX con mis sistemas actuales?",
                    "¿Qué API ofrecen para integración personalizada?",
                    "Necesito detalles técnicos sobre la implementación"
                ])
            else:
                return random.choice([
                    "Hola, me interesa saber más sobre NGX",
                    "¿Pueden explicarme cómo funciona?",
                    "Escuché buenas referencias y quiero información"
                ])
        
        elif messages_sent < 3:  # Discovery
            topics = []
            if profile.profession == "Gym Owner":
                topics = [
                    "¿Cómo puede ayudarme a gestionar múltiples entrenadores?",
                    "¿Qué métricas de negocio puedo trackear?",
                    "¿Incluye gestión de membresías?"
                ]
            elif profile.profession == "Personal Trainer":
                topics = [
                    "¿Cómo me ayuda a conseguir más clientes?",
                    "¿Puedo gestionar mis horarios con esto?",
                    "¿Qué pasa con mis clientes actuales?"
                ]
            else:
                topics = [
                    "¿Qué beneficios específicos ofrece para mi profesión?",
                    "¿Cuánto tiempo toma ver resultados?",
                    "¿Qué tipo de soporte ofrecen?"
                ]
            return random.choice(topics)
        
        else:  # Consideration/Decision
            if profile.price_sensitivity == "high":
                return random.choice([
                    "¿Hay planes de pago flexibles?",
                    "¿Ofrecen descuentos o promociones?",
                    "¿Cuál es el ROI típico?"
                ])
            else:
                return random.choice([
                    "¿Cuándo podría empezar?",
                    "¿Qué incluye exactamente el plan?",
                    "¿Puedo ver una demo primero?"
                ])
    
    async def _send_message(self, conversation_id: str, message: str,
                          session: aiohttp.ClientSession, journey: Dict):
        """Send a message in the conversation."""
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.base_url}/api/v1/conversations/{conversation_id}/message",
                json={"message": message},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                duration = (time.time() - start_time) * 1000
                
                journey["events"].append({
                    "type": "send_message",
                    "message": message[:50] + "..." if len(message) > 50 else message,
                    "status": resp.status,
                    "duration_ms": duration,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            journey["events"].append({
                "type": "message_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _check_recommendations(self, conversation_id: str,
                                   session: aiohttp.ClientSession, journey: Dict):
        """Check product recommendations."""
        start_time = time.time()
        
        try:
            async with session.get(
                f"{self.base_url}/api/v1/conversations/{conversation_id}/recommendations",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                duration = (time.time() - start_time) * 1000
                
                journey["events"].append({
                    "type": "check_recommendations",
                    "status": resp.status,
                    "duration_ms": duration,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            journey["events"].append({
                "type": "recommendations_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _calculate_roi(self, profile: UserProfile,
                           session: aiohttp.ClientSession, journey: Dict):
        """Calculate ROI based on profile."""
        start_time = time.time()
        
        try:
            # Generate realistic business metrics
            if profile.profession == "Gym Owner":
                clients = random.randint(200, 1000)
                avg_ticket = random.randint(30, 80)
            elif profile.profession == "Personal Trainer":
                clients = random.randint(10, 50)
                avg_ticket = random.randint(50, 150)
            else:
                clients = random.randint(20, 100)
                avg_ticket = random.randint(40, 100)
            
            data = {
                "profession": profile.profession,
                "current_clients": clients,
                "average_ticket": avg_ticket,
                "work_hours_per_week": random.randint(30, 60)
            }
            
            async with session.post(
                f"{self.base_url}/api/v1/analytics/roi/calculate",
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                duration = (time.time() - start_time) * 1000
                
                journey["events"].append({
                    "type": "calculate_roi",
                    "status": resp.status,
                    "duration_ms": duration,
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                })
                
        except Exception as e:
            journey["events"].append({
                "type": "roi_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _request_demo(self, conversation_id: str,
                          session: aiohttp.ClientSession, journey: Dict):
        """Request a product demo."""
        journey["events"].append({
            "type": "request_demo",
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id
        })
    
    async def _simulate_conversion(self, conversation_id: str, profile: UserProfile,
                                 session: aiohttp.ClientSession, journey: Dict):
        """Simulate a successful conversion."""
        # Determine plan based on profile
        if profile.profession in ["Gym Owner", "Studio Owner"]:
            plan = "hybrid_coaching"
        elif profile.price_sensitivity == "high":
            plan = "agents_access"
        else:
            plan = random.choice(["agents_access", "hybrid_coaching"])
        
        journey["events"].append({
            "type": "conversion",
            "plan": plan,
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id
        })
        
        journey["converted"] = True
        journey["conversion_plan"] = plan
    
    async def _simulate_exit(self, conversation_id: str, profile: UserProfile,
                           session: aiohttp.ClientSession, journey: Dict):
        """Simulate user exit without conversion."""
        reasons = []
        
        if profile.price_sensitivity == "high":
            reasons.extend(["price_too_high", "need_to_think", "comparing_options"])
        if profile.technical_level == "basic":
            reasons.extend(["too_complex", "need_more_info"])
        reasons.extend(["not_ready", "just_browsing", "will_come_back"])
        
        journey["events"].append({
            "type": "exit_without_conversion",
            "reason": random.choice(reasons),
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id
        })
        
        journey["converted"] = False
    
    def _calculate_journey_metrics(self, journey: Dict) -> Dict[str, Any]:
        """Calculate metrics for a user journey."""
        events = journey.get("events", [])
        
        # Time metrics
        if journey.get("start_time") and journey.get("end_time"):
            start = datetime.fromisoformat(journey["start_time"])
            end = datetime.fromisoformat(journey["end_time"])
            session_duration = (end - start).total_seconds()
        else:
            session_duration = 0
        
        # Event counts
        message_count = sum(1 for e in events if e.get("type") == "send_message")
        error_count = sum(1 for e in events if "error" in e.get("type", ""))
        
        # Response times
        response_times = [e.get("duration_ms", 0) for e in events if "duration_ms" in e]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "session_duration_seconds": session_duration,
            "message_count": message_count,
            "error_count": error_count,
            "avg_response_time_ms": avg_response,
            "converted": journey.get("converted", False),
            "events_count": len(events)
        }
    
    async def run_time_based_scenario(self, time_period: TimeOfDay, duration_minutes: int = 30):
        """Run scenario for a specific time period."""
        print(f"\n{'='*60}")
        print(f"🕐 Running {time_period.value} scenario")
        print(f"Duration: {duration_minutes} minutes")
        print(f"{'='*60}")
        
        pattern = self.time_patterns[time_period]
        num_users = int(len(self.user_profiles) * pattern["user_percentage"])
        
        print(f"Active users for this period: {num_users}")
        
        # Select random users
        active_users = random.sample(self.user_profiles, num_users)
        
        # Distribute users over time period
        users_per_minute = num_users / duration_minutes
        
        results = []
        start_time = time.time()
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=1000)
        ) as session:
            for minute in range(duration_minutes):
                minute_start = time.time()
                
                # Users for this minute
                minute_users = int(users_per_minute)
                if minute == duration_minutes - 1:  # Last minute, include remainder
                    minute_users = num_users - (minute * int(users_per_minute))
                
                # Start user journeys
                tasks = []
                for i in range(minute_users):
                    user_idx = minute * int(users_per_minute) + i
                    if user_idx < len(active_users):
                        user = active_users[user_idx]
                        task = self.simulate_user_journey(user, time_period, session)
                        tasks.append(task)
                
                # Execute concurrent journeys
                if tasks:
                    journeys = await asyncio.gather(*tasks, return_exceptions=True)
                    results.extend([j for j in journeys if isinstance(j, dict)])
                
                # Progress update
                print(f"Minute {minute + 1}/{duration_minutes}: "
                      f"{len(tasks)} users started, "
                      f"{len(results)} total journeys")
                
                # Wait for next minute
                elapsed = time.time() - minute_start
                if elapsed < 60 and minute < duration_minutes - 1:
                    await asyncio.sleep(60 - elapsed)
        
        # Analyze results
        self._analyze_scenario_results(time_period, results)
        return results
    
    def _analyze_scenario_results(self, time_period: TimeOfDay, results: List[Dict]):
        """Analyze and print scenario results."""
        print(f"\n📊 {time_period.value} Scenario Results:")
        print("-" * 60)
        
        total_journeys = len(results)
        conversions = sum(1 for r in results if r.get("converted", False))
        errors = sum(r.get("metrics", {}).get("error_count", 0) for r in results)
        
        # Response time analysis
        all_response_times = []
        for r in results:
            for event in r.get("events", []):
                if "duration_ms" in event:
                    all_response_times.append(event["duration_ms"])
        
        if all_response_times:
            avg_response = sum(all_response_times) / len(all_response_times)
            p95_response = sorted(all_response_times)[int(len(all_response_times) * 0.95)]
        else:
            avg_response = p95_response = 0
        
        # Message analysis
        total_messages = sum(r.get("metrics", {}).get("message_count", 0) for r in results)
        avg_messages = total_messages / total_journeys if total_journeys > 0 else 0
        
        print(f"Total User Journeys: {total_journeys}")
        print(f"Conversions: {conversions} ({conversions/total_journeys*100:.1f}%)")
        print(f"Total Errors: {errors}")
        print(f"Average Response Time: {avg_response:.0f} ms")
        print(f"p95 Response Time: {p95_response:.0f} ms")
        print(f"Average Messages per Journey: {avg_messages:.1f}")
        
        # Profession breakdown
        profession_stats = {}
        for r in results:
            prof = r.get("profile", {}).get("profession", "Unknown")
            if prof not in profession_stats:
                profession_stats[prof] = {"total": 0, "converted": 0}
            profession_stats[prof]["total"] += 1
            if r.get("converted", False):
                profession_stats[prof]["converted"] += 1
        
        print("\nConversion by Profession:")
        for prof, stats in sorted(profession_stats.items()):
            conv_rate = stats["converted"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {prof}: {stats['converted']}/{stats['total']} ({conv_rate:.1f}%)")
    
    async def run_full_day_simulation(self):
        """Run a complete day simulation."""
        print("🌅 NGX Voice Sales Agent - Full Day Simulation")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        all_results = {}
        
        # Run scenarios for each time period
        time_periods = [
            (TimeOfDay.EARLY_MORNING, 20),
            (TimeOfDay.MORNING_PEAK, 30),
            (TimeOfDay.MID_MORNING, 20),
            (TimeOfDay.LUNCH, 20),
            (TimeOfDay.AFTERNOON, 30),
            (TimeOfDay.EVENING_PEAK, 30),
            (TimeOfDay.EVENING, 20),
        ]
        
        for period, duration in time_periods:
            results = await self.run_time_based_scenario(period, duration)
            all_results[period.value] = results
            
            # Cool down between periods
            print(f"\n⏸️  Transitioning to next time period...")
            await asyncio.sleep(10)
        
        # Generate comprehensive report
        self._generate_daily_report(all_results)
    
    def _generate_daily_report(self, all_results: Dict[str, List[Dict]]):
        """Generate comprehensive daily simulation report."""
        print("\n" + "=" * 80)
        print("📊 FULL DAY SIMULATION - FINAL REPORT")
        print("=" * 80)
        
        # Overall statistics
        total_journeys = sum(len(results) for results in all_results.values())
        total_conversions = sum(
            sum(1 for r in results if r.get("converted", False))
            for results in all_results.values()
        )
        
        print(f"\nTotal User Journeys: {total_journeys}")
        print(f"Total Conversions: {total_conversions} ({total_conversions/total_journeys*100:.1f}%)")
        
        # Time period analysis
        print("\n📈 Performance by Time Period:")
        print(f"{'Period':<20} {'Users':<10} {'Conv %':<10} {'Avg Response':<15} {'Errors':<10}")
        print("-" * 75)
        
        for period, results in all_results.items():
            users = len(results)
            conversions = sum(1 for r in results if r.get("converted", False))
            conv_rate = conversions / users * 100 if users > 0 else 0
            
            response_times = []
            errors = 0
            for r in results:
                for event in r.get("events", []):
                    if "duration_ms" in event:
                        response_times.append(event["duration_ms"])
                errors += r.get("metrics", {}).get("error_count", 0)
            
            avg_response = sum(response_times) / len(response_times) if response_times else 0
            
            print(f"{period:<20} {users:<10} {conv_rate:<10.1f} {avg_response:<15.0f} {errors:<10}")
        
        # Peak load analysis
        print("\n🔥 Peak Load Analysis:")
        peak_periods = ["morning_peak", "evening_peak"]
        for period in peak_periods:
            if period in all_results:
                results = all_results[period]
                print(f"\n{period.replace('_', ' ').title()}:")
                print(f"  Concurrent Users: {len(results)}")
                
                # Calculate concurrent operations
                events_by_minute = {}
                for r in results:
                    for event in r.get("events", []):
                        if "timestamp" in event:
                            minute = event["timestamp"][:16]  # YYYY-MM-DDTHH:MM
                            if minute not in events_by_minute:
                                events_by_minute[minute] = 0
                            events_by_minute[minute] += 1
                
                if events_by_minute:
                    max_concurrent = max(events_by_minute.values())
                    print(f"  Max Operations/Minute: {max_concurrent}")
        
        # Save detailed report
        self._save_daily_report(all_results)
    
    def _save_daily_report(self, all_results: Dict[str, List[Dict]]):
        """Save detailed daily simulation report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tests/performance/results/real_world_simulation_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Prepare summary data
        summary = {
            "test_name": "Real World Full Day Simulation",
            "timestamp": timestamp,
            "total_journeys": sum(len(results) for results in all_results.values()),
            "periods": {}
        }
        
        for period, results in all_results.items():
            # Calculate period summary
            conversions = sum(1 for r in results if r.get("converted", False))
            
            summary["periods"][period] = {
                "total_users": len(results),
                "conversions": conversions,
                "conversion_rate": conversions / len(results) * 100 if results else 0,
                "avg_session_duration": sum(
                    r.get("metrics", {}).get("session_duration_seconds", 0) 
                    for r in results
                ) / len(results) if results else 0
            }
        
        # Save summary
        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {filename}")
        
        # Save detailed journeys (sampled to avoid huge files)
        detailed_filename = filename.replace(".json", "_detailed.json")
        sampled_results = {}
        for period, results in all_results.items():
            # Sample up to 10 journeys per period
            sampled_results[period] = random.sample(results, min(10, len(results)))
        
        with open(detailed_filename, "w") as f:
            json.dump(sampled_results, f, indent=2)
        
        print(f"💾 Detailed journey samples saved to: {detailed_filename}")


async def main():
    """Run real-world scenario tests."""
    print("🌍 NGX Voice Sales Agent - Real World Scenario Testing")
    print("Choose a test scenario:")
    print("1. Morning Peak (30 min)")
    print("2. Evening Peak (30 min)")
    print("3. Full Day Simulation (3 hours)")
    print("4. Weekend Pattern (1 hour)")
    
    # For automated testing, run morning peak
    tester = RealWorldScenarioTester()
    
    # Option 1: Run specific time period
    await tester.run_time_based_scenario(TimeOfDay.MORNING_PEAK, duration_minutes=30)
    
    # Option 2: Run full day (commented out due to length)
    # await tester.run_full_day_simulation()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")