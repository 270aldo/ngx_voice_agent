#!/usr/bin/env python3
"""
Mock Production Server with Rate Limiting

Simulates a production-like API server with rate limiting enabled
for testing purposes.
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
import jwt
import uuid
from typing import Dict, Optional, Tuple
import uvicorn

# Create FastAPI app
app = FastAPI(title="NGX Mock Production API", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Rate limit storage
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(lambda: {"minute": deque(), "hour": deque()})
        self.limits = {
            "user": {"minute": 60, "hour": 1000},
            "premium": {"minute": 120, "hour": 2000},
            "admin": {"minute": 0, "hour": 0}  # No limits for admin
        }
    
    def check_rate_limit(self, user_id: str, role: str = "user") -> Tuple[bool, Dict[str, int]]:
        """Check if request is within rate limits."""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Clean old requests
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Remove old entries
        while user_requests["minute"] and user_requests["minute"][0] < minute_ago:
            user_requests["minute"].popleft()
        
        while user_requests["hour"] and user_requests["hour"][0] < hour_ago:
            user_requests["hour"].popleft()
        
        # Get limits for role
        limits = self.limits.get(role, self.limits["user"])
        
        # Check if admin (no limits)
        if limits["minute"] == 0 and limits["hour"] == 0:
            return True, {"minute": 0, "hour": 0, "minute_remaining": 999, "hour_remaining": 999}
        
        # Check limits
        minute_count = len(user_requests["minute"])
        hour_count = len(user_requests["hour"])
        
        if minute_count >= limits["minute"] or hour_count >= limits["hour"]:
            return False, {
                "minute": minute_count,
                "hour": hour_count,
                "minute_remaining": max(0, limits["minute"] - minute_count),
                "hour_remaining": max(0, limits["hour"] - hour_count),
                "reset": int(min(
                    user_requests["minute"][0] + 60 if user_requests["minute"] else now + 60,
                    user_requests["hour"][0] + 3600 if user_requests["hour"] else now + 3600
                ))
            }
        
        # Add request
        user_requests["minute"].append(now)
        user_requests["hour"].append(now)
        
        return True, {
            "minute": minute_count + 1,
            "hour": hour_count + 1,
            "minute_remaining": limits["minute"] - minute_count - 1,
            "hour_remaining": limits["hour"] - hour_count - 1,
            "reset": int(now + 60)
        }

# Initialize rate limiter
rate_limiter = RateLimiter()

# Conversation storage (in-memory for testing)
conversations = {}

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Decode and validate JWT token."""
    token = credentials.credentials
    
    try:
        # Decode token (using test secret)
        payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
        return {
            "id": payload.get("sub", "unknown"),
            "email": payload.get("email", ""),
            "role": payload.get("role", "user")
        }
    except:
        # For testing, create user from token
        return {
            "id": token[:8],  # Use first 8 chars as ID
            "email": f"{token[:8]}@test.com",
            "role": "user"
        }

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to requests."""
    # Skip rate limiting for health check and auth endpoints
    if request.url.path in ["/health", "/v1/health", "/v1/auth/login", "/v1/auth/register"]:
        return await call_next(request)
    
    # Extract user info from authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
            user_id = payload.get("sub", token[:8])
            role = payload.get("role", "user")
        except:
            user_id = token[:8]
            role = "user"
    else:
        user_id = request.client.host if request.client else "anonymous"
        role = "user"
    
    # Check rate limit
    allowed, limits = rate_limiter.check_rate_limit(user_id, role)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {limits.get('minute_remaining', 0)}/min",
                "retry_after": limits.get("reset", 60)
            },
            headers={
                "X-Rate-Limit-Limit": str(60),  # Default minute limit
                "X-Rate-Limit-Remaining": str(limits.get("minute_remaining", 0)),
                "X-Rate-Limit-Reset": str(limits.get("reset", int(time.time() + 60))),
                "Retry-After": str(limits.get("reset", 60) - int(time.time()))
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-Rate-Limit-Limit"] = str(60)
    response.headers["X-Rate-Limit-Remaining"] = str(limits.get("minute_remaining", 0))
    response.headers["X-Rate-Limit-Reset"] = str(limits.get("reset", int(time.time() + 60)))
    
    return response

# Routes
@app.get("/health")
@app.get("/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ngx-mock-production"
    }

@app.post("/v1/auth/login")
async def login(username: str, password: str):
    """Mock login endpoint."""
    # Determine role from username
    role = "user"
    if "admin" in username:
        role = "admin"
    elif "premium" in username:
        role = "premium"
    
    # Generate mock token
    payload = {
        "sub": username,
        "email": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, "test_secret", algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600
    }

@app.post("/v1/conversation/start")
async def start_conversation(
    customer_info: Dict,
    user: Dict = Depends(get_current_user)
):
    """Start a new conversation."""
    # Simulate processing time
    await asyncio.sleep(0.1)
    
    conv_id = str(uuid.uuid4())
    conversations[conv_id] = {
        "id": conv_id,
        "user_id": user["id"],
        "customer_info": customer_info,
        "messages": [],
        "started_at": datetime.utcnow().isoformat()
    }
    
    return {
        "conversation_id": conv_id,
        "message": f"Hola {customer_info.get('name', 'amigo')}, bienvenido a NGX. ¿En qué puedo ayudarte hoy?",
        "metadata": {
            "sentiment": "positive",
            "detected_intent": "greeting"
        }
    }

@app.post("/v1/conversation/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    message: str,
    user: Dict = Depends(get_current_user)
):
    """Send a message in conversation."""
    # Simulate processing time
    await asyncio.sleep(0.2)
    
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Add message to conversation
    conversations[conversation_id]["messages"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Generate mock response
    responses = [
        "NGX ofrece planes desde $99/mes para Essential hasta $649/mes para Elite.",
        "Nuestros servicios incluyen acceso a 11 agentes de IA especializados.",
        "Con NGX puedes mejorar la retención de clientes hasta un 25%.",
        "Ofrecemos soporte 24/7 y actualizaciones gratuitas."
    ]
    
    import random
    response = random.choice(responses)
    
    conversations[conversation_id]["messages"].append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "conversation_id": conversation_id,
        "message": response,
        "metadata": {
            "sentiment": "neutral",
            "detected_intent": "information_request",
            "confidence": 0.85
        }
    }

@app.get("/v1/analytics/conversation/{conversation_id}")
async def get_analytics(
    conversation_id: str,
    user: Dict = Depends(get_current_user)
):
    """Get conversation analytics."""
    # Simulate processing time
    await asyncio.sleep(0.15)
    
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv = conversations[conversation_id]
    
    return {
        "conversation_id": conversation_id,
        "duration_seconds": 120,
        "message_count": len(conv["messages"]),
        "customer_engagement_score": 0.75,
        "objections_handled": 2,
        "conversion_probability": 0.65,
        "roi_projection": {
            "percentage": 350,
            "annual_value": 42000,
            "payback_months": 3.2
        }
    }

@app.post("/v1/predictive/objection/predict")
async def predict_objections(
    conversation_id: str,
    messages: list,
    user: Dict = Depends(get_current_user)
):
    """Predict objections."""
    # Simulate ML processing
    await asyncio.sleep(0.3)
    
    return {
        "objections": [
            {
                "type": "price",
                "probability": 0.75,
                "suggested_response": "Entiendo tu preocupación por el precio...",
                "confidence": 0.85
            }
        ]
    }

@app.post("/v1/predictive/needs/predict")
async def predict_needs(
    conversation_id: str,
    messages: list,
    user: Dict = Depends(get_current_user)
):
    """Predict customer needs."""
    # Simulate ML processing
    await asyncio.sleep(0.25)
    
    return {
        "needs": [
            {
                "category": "retention",
                "description": "Mejorar retención de clientes",
                "priority": "high",
                "confidence": 0.9
            }
        ]
    }

@app.post("/v1/predictive/conversion/predict")
async def predict_conversion(
    conversation_id: str,
    messages: list,
    user: Dict = Depends(get_current_user)
):
    """Predict conversion probability."""
    # Simulate ML processing
    await asyncio.sleep(0.2)
    
    return {
        "probability": 0.72,
        "category": "high",
        "factors": [
            {
                "factor": "engagement_level",
                "impact": "positive",
                "weight": 0.3
            }
        ]
    }

@app.post("/v1/qualification/score")
async def calculate_score(
    customer_info: Dict,
    user: Dict = Depends(get_current_user)
):
    """Calculate qualification score."""
    # Simulate processing
    await asyncio.sleep(0.1)
    
    return {
        "lead_score": 75,
        "qualification": "warm",
        "recommended_actions": ["Schedule demo", "Send case studies"],
        "tier_recommendation": "pro"
    }

@app.get("/v1/analytics/aggregate")
async def get_aggregate_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Get aggregate analytics."""
    # Simulate processing
    await asyncio.sleep(0.2)
    
    return {
        "period": {
            "start": start_date or "2025-01-01",
            "end": end_date or "2025-01-31"
        },
        "total_conversations": 1250,
        "conversions": 187,
        "conversion_rate": 0.15,
        "average_conversation_duration": 420
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            },
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    print("🚀 Starting Mock Production Server with Rate Limiting")
    print("="*60)
    print("Rate Limits:")
    print("  - Regular users: 60 req/min, 1000 req/hour")
    print("  - Premium users: 120 req/min, 2000 req/hour")
    print("  - Admin users: No limits")
    print("="*60)
    print("Server running at: http://localhost:8000")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)