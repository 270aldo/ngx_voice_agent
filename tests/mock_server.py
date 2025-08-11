#!/usr/bin/env python3
"""
Mock API Server for Testing
Creates a lightweight mock server that mimics the real API for tests.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import asyncio
from datetime import datetime
import uuid

# Mock data models
class ConversationStart(BaseModel):
    customer_data: Dict[str, Any]
    program_type: Optional[str] = "starter"
    platform_info: Optional[Dict[str, Any]] = None

class MessageRequest(BaseModel):
    message: str

class MockAPIServer:
    """Mock server for tests that require API endpoints"""
    
    def __init__(self, port: int = 8001):
        self.app = FastAPI(title="NGX Mock API Server")
        self.port = port
        self.conversations = {}
        self.setup_routes()
    
    def setup_routes(self):
        """Setup all mock routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        @self.app.get("/api/v1/health")
        async def api_health():
            return {
                "status": "ok",
                "version": "1.0.0-mock",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.post("/conversations/start")
        async def start_conversation(request: ConversationStart):
            conversation_id = f"mock-{uuid.uuid4()}"
            self.conversations[conversation_id] = {
                "id": conversation_id,
                "customer_data": request.customer_data,
                "messages": [],
                "started_at": datetime.now().isoformat()
            }
            return {
                "conversation_id": conversation_id,
                "status": "active",
                "greeting": "¡Hola! Soy tu asistente de ventas NGX."
            }
        
        @self.app.post("/conversations/{conversation_id}/message")
        async def send_message(conversation_id: str, request: MessageRequest):
            if conversation_id not in self.conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Store message
            self.conversations[conversation_id]["messages"].append({
                "role": "user",
                "content": request.message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Generate mock response
            response = self._generate_mock_response(request.message)
            self.conversations[conversation_id]["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "response": response,
                "conversation_id": conversation_id,
                "ml_insights": {
                    "objection_probability": 0.2,
                    "conversion_probability": 0.75,
                    "detected_needs": ["automation", "growth"]
                }
            }
        
        @self.app.get("/conversations/{conversation_id}")
        async def get_conversation(conversation_id: str):
            if conversation_id not in self.conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return self.conversations[conversation_id]
        
        @self.app.post("/api/v1/auth/login")
        async def login(credentials: Dict[str, str]):
            """Mock login endpoint"""
            return {
                "access_token": "mock-jwt-token",
                "refresh_token": "mock-refresh-token",
                "user": {
                    "id": "mock-user-1",
                    "email": credentials.get("email", "test@example.com"),
                    "full_name": "Test User",
                    "role": "admin"
                }
            }
        
        @self.app.get("/api/v1/auth/csrf")
        async def get_csrf_token():
            """Mock CSRF token endpoint"""
            return {
                "csrf_token": f"mock-csrf-{uuid.uuid4()}"
            }
        
        @self.app.get("/metrics/prometheus")
        async def prometheus_metrics():
            """Mock Prometheus metrics"""
            return "# HELP api_requests_total Total API requests\n# TYPE api_requests_total counter\napi_requests_total 100"
        
    def _generate_mock_response(self, message: str) -> str:
        """Generate a contextual mock response"""
        message_lower = message.lower()
        
        if "precio" in message_lower or "costo" in message_lower:
            return "Nuestros planes comienzan desde $47/mes. ¿Te gustaría conocer el ROI específico para tu negocio?"
        elif "funciona" in message_lower or "cómo" in message_lower:
            return "NGX utiliza IA avanzada para automatizar y optimizar tus procesos. ¿Qué área te gustaría mejorar primero?"
        elif "empezar" in message_lower or "comenzar" in message_lower:
            return "¡Excelente decisión! Podemos comenzar con una prueba gratuita de 14 días. ¿Te gustaría programar una demo?"
        else:
            return "Entiendo tu interés. NGX puede ayudarte a escalar tu negocio. ¿Cuáles son tus principales desafíos actualmente?"
    
    async def start(self):
        """Start the mock server"""
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="error"  # Quiet for tests
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def run_in_background(self):
        """Run server in background thread"""
        import threading
        def run():
            asyncio.run(self.start())
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        # Give server time to start
        import time
        time.sleep(1)
        return thread


def create_mock_app():
    """Create and return the FastAPI app for testing"""
    server = MockAPIServer()
    return server.app


if __name__ == "__main__":
    # Run standalone mock server
    server = MockAPIServer(port=8001)
    print("🚀 Mock API Server running on http://localhost:8001")
    print("📝 Available endpoints:")
    print("  - GET  /health")
    print("  - GET  /api/v1/health")
    print("  - POST /conversations/start")
    print("  - POST /conversations/{id}/message")
    print("  - GET  /conversations/{id}")
    print("  - POST /api/v1/auth/login")
    print("  - GET  /api/v1/auth/csrf")
    print("  - GET  /metrics/prometheus")
    asyncio.run(server.start())