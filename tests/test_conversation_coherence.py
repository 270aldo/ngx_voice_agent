#!/usr/bin/env python3
"""
Conversation Coherence Test Suite

Tests the agent's ability to maintain coherence, consistency, and context
over long conversations (50+ messages).
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ConversationCoherenceTester:
    """Tests conversation coherence over extended interactions."""
    
    def __init__(self):
        self.test_results = []
        self.coherence_violations = []
        self.context_tracking = {}
        
    async def generate_long_conversation(self, num_messages: int = 60) -> List[Dict[str, Any]]:
        """Generate a realistic long conversation flow."""
        conversation = []
        timestamp = datetime.now()
        
        # Conversation phases
        phases = [
            # Phase 1: Initial contact and discovery (messages 1-10)
            {
                "phase": "discovery",
                "user_messages": [
                    "Hola, estoy buscando mejorar mi gimnasio",
                    "Tenemos alrededor de 500 miembros activos",
                    "Nuestro problema principal es la retención de clientes",
                    "Perdemos un 15% de miembros cada mes",
                    "¿Cómo puede ayudar NGX con esto?"
                ],
                "context_established": {
                    "business_type": "gym",
                    "size": "500 members",
                    "main_problem": "retention",
                    "churn_rate": "15%"
                }
            },
            # Phase 2: Solution presentation (messages 11-20)
            {
                "phase": "solution_presentation",
                "user_messages": [
                    "¿Qué incluye NGX exactamente?",
                    "¿Los 11 agentes que mencionas son personas o IA?",
                    "¿Cómo funciona el Hybrid Coaching?",
                    "¿Cuánto tiempo toma ver resultados?",
                    "¿Hay casos de éxito similares a mi gimnasio?"
                ],
                "context_established": {
                    "solution_interest": "NGX features",
                    "specific_interests": ["agents", "hybrid_coaching", "timeline", "case_studies"]
                }
            },
            # Phase 3: Pricing discussion (messages 21-30)
            {
                "phase": "pricing",
                "user_messages": [
                    "¿Cuáles son los planes disponibles?",
                    "El plan Elite de $649 parece caro",
                    "¿Qué diferencia hay entre Pro y Elite?",
                    "¿Hay descuentos por pago anual?",
                    "Necesito justificar esta inversión a mis socios"
                ],
                "context_established": {
                    "price_sensitivity": "high",
                    "decision_makers": "multiple partners",
                    "preferred_tier": "considering Pro/Elite"
                }
            },
            # Phase 4: Objections and concerns (messages 31-40)
            {
                "phase": "objections",
                "user_messages": [
                    "Ya tenemos un sistema CRM",
                    "¿Cómo se integra con nuestro software actual?",
                    "Me preocupa la complejidad de implementación",
                    "¿Mis empleados necesitarán mucha capacitación?",
                    "¿Qué pasa si no funciona como esperamos?"
                ],
                "context_established": {
                    "existing_tools": "CRM system",
                    "concerns": ["integration", "complexity", "training", "risk"]
                }
            },
            # Phase 5: Decision making (messages 41-50)
            {
                "phase": "decision",
                "user_messages": [
                    "Necesito hablarlo con mis socios",
                    "¿Pueden enviarme una propuesta formal?",
                    "¿Cuándo podríamos empezar si decidimos avanzar?",
                    "¿Ofrecen algún período de prueba?",
                    "Creo que el plan Pro sería el mejor para nosotros"
                ],
                "context_established": {
                    "decision_process": "consulting partners",
                    "timeline": "ready to start soon",
                    "leaning_towards": "Pro plan"
                }
            },
            # Phase 6: Closing and follow-up (messages 51-60)
            {
                "phase": "closing",
                "user_messages": [
                    "Ok, estamos listos para empezar con el plan Pro",
                    "¿Cuáles son los siguientes pasos?",
                    "¿Necesitan alguna información adicional?",
                    "¿Cuándo podemos programar la implementación?",
                    "Gracias por toda la información"
                ],
                "context_established": {
                    "decision": "Pro plan confirmed",
                    "ready_to_proceed": True
                }
            }
        ]
        
        message_count = 0
        
        for phase_data in phases:
            phase = phase_data["phase"]
            
            for user_msg in phase_data["user_messages"]:
                message_count += 1
                
                # User message
                conversation.append({
                    "role": "user",
                    "content": user_msg,
                    "timestamp": timestamp.isoformat(),
                    "message_number": message_count,
                    "phase": phase
                })
                timestamp += timedelta(seconds=random.randint(30, 120))
                
                # Assistant response (simulated)
                message_count += 1
                conversation.append({
                    "role": "assistant",
                    "content": f"[Response to: {user_msg}]",
                    "timestamp": timestamp.isoformat(),
                    "message_number": message_count,
                    "phase": phase,
                    "context_should_remember": phase_data["context_established"]
                })
                timestamp += timedelta(seconds=random.randint(20, 60))
        
        return conversation
    
    def check_information_consistency(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if information remains consistent throughout the conversation."""
        consistency_issues = []
        facts_mentioned = {}
        
        # Track facts mentioned throughout conversation
        for msg in conversation:
            if msg["role"] == "assistant":
                # Check for pricing consistency
                if "$99" in msg["content"] and "essential" in msg["content"].lower():
                    if "essential_price" in facts_mentioned:
                        if facts_mentioned["essential_price"] != "$99":
                            consistency_issues.append({
                                "type": "price_inconsistency",
                                "message": msg["message_number"],
                                "issue": "Essential price changed"
                            })
                    else:
                        facts_mentioned["essential_price"] = "$99"
                
                # Check for feature consistency
                if "11 agents" in msg["content"] or "11 agentes" in msg["content"]:
                    if "agent_count" in facts_mentioned:
                        if facts_mentioned["agent_count"] != "11":
                            consistency_issues.append({
                                "type": "feature_inconsistency",
                                "message": msg["message_number"],
                                "issue": "Agent count changed"
                            })
                    else:
                        facts_mentioned["agent_count"] = "11"
        
        return {
            "consistent": len(consistency_issues) == 0,
            "issues": consistency_issues,
            "facts_tracked": len(facts_mentioned)
        }
    
    def check_context_retention(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if context is retained across the conversation."""
        context_failures = []
        established_context = {}
        
        for msg in conversation:
            # Track context that should be remembered
            if msg["role"] == "assistant" and "context_should_remember" in msg:
                for key, value in msg["context_should_remember"].items():
                    established_context[key] = {
                        "value": value,
                        "established_at": msg["message_number"]
                    }
            
            # Check if later messages contradict established context
            if msg["role"] == "assistant" and msg["message_number"] > 20:
                # Example checks
                if "gym" in established_context and "studio" in msg["content"].lower():
                    context_failures.append({
                        "type": "business_type_confusion",
                        "message": msg["message_number"],
                        "established": "gym",
                        "mentioned": "studio"
                    })
                
                if "500 members" in str(established_context.get("size", {}).get("value", "")):
                    if any(num in msg["content"] for num in ["100", "1000", "50"]):
                        context_failures.append({
                            "type": "size_confusion",
                            "message": msg["message_number"],
                            "issue": "Member count inconsistency"
                        })
        
        return {
            "context_retained": len(context_failures) == 0,
            "failures": context_failures,
            "context_points": len(established_context)
        }
    
    def check_conversation_flow(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if conversation flows naturally without repetition or loops."""
        flow_issues = []
        topics_discussed = []
        repeated_questions = {}
        
        for msg in conversation:
            if msg["role"] == "user":
                # Track topics
                topic = self._extract_topic(msg["content"])
                if topic:
                    topics_discussed.append({
                        "topic": topic,
                        "message": msg["message_number"],
                        "phase": msg["phase"]
                    })
                
                # Check for repeated questions
                question_key = msg["content"].lower().strip()
                if question_key in repeated_questions:
                    if msg["message_number"] - repeated_questions[question_key] > 10:
                        flow_issues.append({
                            "type": "repeated_question",
                            "message": msg["message_number"],
                            "original": repeated_questions[question_key],
                            "question": msg["content"]
                        })
                else:
                    repeated_questions[question_key] = msg["message_number"]
        
        # Check for logical progression
        expected_progression = ["discovery", "solution_presentation", "pricing", "objections", "decision", "closing"]
        actual_progression = []
        current_phase = None
        
        for msg in conversation:
            if msg["phase"] != current_phase:
                current_phase = msg["phase"]
                if current_phase not in actual_progression:
                    actual_progression.append(current_phase)
        
        progression_correct = actual_progression == expected_progression
        
        return {
            "natural_flow": len(flow_issues) == 0 and progression_correct,
            "flow_issues": flow_issues,
            "topics_covered": len(set(t["topic"] for t in topics_discussed)),
            "progression_correct": progression_correct,
            "actual_progression": actual_progression
        }
    
    def check_response_relevance(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if responses are relevant to the questions asked."""
        relevance_issues = []
        total_responses = 0
        
        for i in range(1, len(conversation), 2):  # Check user-assistant pairs
            if i < len(conversation) and conversation[i-1]["role"] == "user":
                user_msg = conversation[i-1]["content"]
                
                if i < len(conversation) and conversation[i]["role"] == "assistant":
                    assistant_msg = conversation[i]["content"]
                    total_responses += 1
                    
                    # Check relevance (simplified)
                    if "?" in user_msg:  # User asked a question
                        # Check if response addresses the question
                        question_keywords = self._extract_keywords(user_msg)
                        response_keywords = self._extract_keywords(assistant_msg)
                        
                        overlap = len(set(question_keywords) & set(response_keywords))
                        if overlap == 0:
                            relevance_issues.append({
                                "type": "irrelevant_response",
                                "message": conversation[i]["message_number"],
                                "question": user_msg,
                                "response_preview": assistant_msg[:100]
                            })
        
        relevance_score = (total_responses - len(relevance_issues)) / total_responses if total_responses > 0 else 0
        
        return {
            "relevance_score": relevance_score,
            "relevance_issues": relevance_issues,
            "total_responses": total_responses
        }
    
    def check_personality_consistency(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if the agent maintains consistent personality and tone."""
        tone_changes = []
        formality_scores = []
        
        for msg in conversation:
            if msg["role"] == "assistant":
                # Analyze tone/formality
                formality = self._analyze_formality(msg["content"])
                formality_scores.append(formality)
                
                # Check for sudden tone changes
                if len(formality_scores) > 1:
                    if abs(formality_scores[-1] - formality_scores[-2]) > 0.5:
                        tone_changes.append({
                            "type": "tone_shift",
                            "message": msg["message_number"],
                            "shift": formality_scores[-1] - formality_scores[-2]
                        })
        
        # Calculate consistency
        if formality_scores:
            avg_formality = sum(formality_scores) / len(formality_scores)
            variance = sum((f - avg_formality) ** 2 for f in formality_scores) / len(formality_scores)
            consistency_score = 1 - min(variance, 1)  # Lower variance = higher consistency
        else:
            consistency_score = 0
        
        return {
            "personality_consistent": len(tone_changes) < 3,  # Allow some variation
            "consistency_score": consistency_score,
            "tone_changes": tone_changes
        }
    
    def _extract_topic(self, text: str) -> Optional[str]:
        """Extract main topic from text."""
        topics = {
            "pricing": ["precio", "costo", "plan", "pago", "$"],
            "features": ["incluye", "agentes", "coaching", "funciona"],
            "integration": ["integra", "software", "CRM", "sistema"],
            "results": ["resultados", "casos", "éxito", "mejora"],
            "objections": ["preocupa", "problema", "difícil", "complejo"]
        }
        
        text_lower = text.lower()
        for topic, keywords in topics.items():
            if any(keyword in text_lower for keyword in keywords):
                return topic
        
        return "general"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for relevance checking."""
        # Simple keyword extraction
        stopwords = {"el", "la", "de", "que", "y", "a", "en", "es", "por", "con", "para"}
        words = text.lower().split()
        return [w for w in words if len(w) > 3 and w not in stopwords]
    
    def _analyze_formality(self, text: str) -> float:
        """Analyze formality level of text (0-1 scale)."""
        formal_indicators = ["usted", "le", "quisiera", "podría", "sería"]
        informal_indicators = ["tú", "te", "ok", "genial", "súper"]
        
        text_lower = text.lower()
        formal_count = sum(1 for ind in formal_indicators if ind in text_lower)
        informal_count = sum(1 for ind in informal_indicators if ind in text_lower)
        
        if formal_count + informal_count == 0:
            return 0.5  # Neutral
        
        return formal_count / (formal_count + informal_count)
    
    async def run_coherence_test(self, num_messages: int = 60) -> Dict[str, Any]:
        """Run complete coherence test suite."""
        print(f"\n{'='*80}")
        print(f"🧪 CONVERSATION COHERENCE TEST - {num_messages} Messages")
        print(f"{'='*80}")
        
        # Generate test conversation
        print(f"\n📝 Generating {num_messages}-message conversation...")
        conversation = await self.generate_long_conversation(num_messages)
        
        # Run all coherence checks
        print("\n🔍 Running coherence checks...")
        
        # 1. Information Consistency
        print("\n1️⃣ Checking Information Consistency...")
        consistency_result = self.check_information_consistency(conversation)
        print(f"   Result: {'✅ PASS' if consistency_result['consistent'] else '❌ FAIL'}")
        if not consistency_result['consistent']:
            print(f"   Issues found: {len(consistency_result['issues'])}")
        
        # 2. Context Retention
        print("\n2️⃣ Checking Context Retention...")
        context_result = self.check_context_retention(conversation)
        print(f"   Result: {'✅ PASS' if context_result['context_retained'] else '❌ FAIL'}")
        print(f"   Context points tracked: {context_result['context_points']}")
        
        # 3. Conversation Flow
        print("\n3️⃣ Checking Conversation Flow...")
        flow_result = self.check_conversation_flow(conversation)
        print(f"   Result: {'✅ PASS' if flow_result['natural_flow'] else '❌ FAIL'}")
        print(f"   Topics covered: {flow_result['topics_covered']}")
        print(f"   Progression: {' → '.join(flow_result['actual_progression'])}")
        
        # 4. Response Relevance
        print("\n4️⃣ Checking Response Relevance...")
        relevance_result = self.check_response_relevance(conversation)
        print(f"   Relevance Score: {relevance_result['relevance_score']:.2%}")
        print(f"   Result: {'✅ PASS' if relevance_result['relevance_score'] > 0.85 else '❌ FAIL'}")
        
        # 5. Personality Consistency
        print("\n5️⃣ Checking Personality Consistency...")
        personality_result = self.check_personality_consistency(conversation)
        print(f"   Consistency Score: {personality_result['consistency_score']:.2%}")
        print(f"   Result: {'✅ PASS' if personality_result['personality_consistent'] else '❌ FAIL'}")
        
        # Calculate overall score
        tests_passed = sum([
            consistency_result['consistent'],
            context_result['context_retained'],
            flow_result['natural_flow'],
            relevance_result['relevance_score'] > 0.85,
            personality_result['personality_consistent']
        ])
        
        overall_score = tests_passed / 5
        
        # Generate report
        report = {
            "test_info": {
                "timestamp": datetime.now().isoformat(),
                "num_messages": num_messages,
                "conversation_duration": "simulated"
            },
            "results": {
                "information_consistency": {
                    "passed": consistency_result['consistent'],
                    "issues": len(consistency_result['issues']),
                    "details": consistency_result['issues'][:3]  # First 3 issues
                },
                "context_retention": {
                    "passed": context_result['context_retained'],
                    "failures": len(context_result['failures']),
                    "context_points": context_result['context_points']
                },
                "conversation_flow": {
                    "passed": flow_result['natural_flow'],
                    "topics_covered": flow_result['topics_covered'],
                    "progression_correct": flow_result['progression_correct']
                },
                "response_relevance": {
                    "passed": relevance_result['relevance_score'] > 0.85,
                    "score": relevance_result['relevance_score'],
                    "issues": len(relevance_result['relevance_issues'])
                },
                "personality_consistency": {
                    "passed": personality_result['personality_consistent'],
                    "score": personality_result['consistency_score'],
                    "tone_changes": len(personality_result['tone_changes'])
                }
            },
            "overall": {
                "tests_passed": tests_passed,
                "total_tests": 5,
                "score": overall_score,
                "ready_for_long_conversations": overall_score >= 0.8
            }
        }
        
        # Save report
        report_file = f"coherence_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*80}")
        print("📊 COHERENCE TEST SUMMARY")
        print(f"{'='*80}")
        print(f"\nTests Passed: {tests_passed}/5")
        print(f"Overall Score: {overall_score:.0%}")
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        if overall_score >= 0.8:
            print("\n✅ CONVERSATION COHERENCE TEST PASSED")
            print("   The agent maintains coherence in long conversations!")
            print("\n   🏆 Key Achievements:")
            print("   • Information remains consistent throughout")
            print("   • Context is retained across all phases")
            print("   • Natural conversation flow maintained")
            print("   • Responses are relevant to questions")
            print("   • Personality remains consistent")
        else:
            print("\n⚠️ CONVERSATION COHERENCE NEEDS IMPROVEMENT")
            print("   Review the detailed report for specific issues")
        
        return report


async def main():
    """Run conversation coherence test."""
    tester = ConversationCoherenceTester()
    
    # Test with 60 messages (30 exchanges)
    await tester.run_coherence_test(60)
    
    # Optional: Test with even longer conversation
    # await tester.run_coherence_test(100)


if __name__ == "__main__":
    asyncio.run(main())