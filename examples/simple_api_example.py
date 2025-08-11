#!/usr/bin/env python3
"""
NGX Voice Sales Agent - Simple API Example
==========================================

This is a minimal FastAPI example showing basic conversation endpoints.
This file was moved from the root directory to examples/ for better organization.

For the full production API, use:
    uvicorn src.api.main:app

This example demonstrates:
- Basic FastAPI setup
- In-memory conversation storage
- Simple health check endpoint
- Basic conversation management
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="NGX Voice Sales Agent API", version="1.0.0")

# Store conversations in memory
conversations = {}
conversation_counter = 0

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": "production"
    })

@app.post("/conversations/start")
async def start_conversation(data: dict):
    """Start a new conversation."""
    global conversation_counter
    conversation_counter += 1
    
    conversation_id = f"conv_{conversation_counter}"
    conversations[conversation_id] = {
        "id": conversation_id,
        "customer_data": data.get("customer_data", {}),
        "started_at": datetime.now().isoformat(),
        "messages": []
    }
    
    return JSONResponse({
        "conversation_id": conversation_id,
        "status": "active",
        "phase": "greeting",
        "message": "¡Hola! Soy el agente de ventas de NGX. ¿En qué puedo ayudarte hoy?"
    })

@app.post("/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, data: dict):
    """Send a message in conversation."""
    if conversation_id not in conversations:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    
    message = data.get("message", "")
    conversations[conversation_id]["messages"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Simple response
    response = "Gracias por tu mensaje. NGX ofrece soluciones innovadoras para fitness profesionales."
    if "precio" in message.lower():
        response = "Nuestros planes comienzan desde $297/mes. ¿Te gustaría conocer más detalles?"
    elif "demo" in message.lower():
        response = "¡Excelente! Puedo agendar una demo personalizada. ¿Cuándo te vendría bien?"
    
    conversations[conversation_id]["messages"].append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now().isoformat()
    })
    
    return JSONResponse({
        "response": response,
        "conversation_id": conversation_id
    })

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation state."""
    if conversation_id not in conversations:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    
    return JSONResponse(conversations[conversation_id])

@app.post("/conversations/{conversation_id}/end")
async def end_conversation(conversation_id: str):
    """End a conversation."""
    if conversation_id not in conversations:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    
    conversations[conversation_id]["ended_at"] = datetime.now().isoformat()
    conversations[conversation_id]["status"] = "ended"
    
    return JSONResponse({
        "message": "Conversation ended",
        "conversation_id": conversation_id
    })

@app.get("/analytics/aggregate")
async def get_analytics():
    """Get aggregate analytics."""
    return JSONResponse({
        "total_conversations": len(conversations),
        "active_conversations": sum(1 for c in conversations.values() if c.get("status") != "ended"),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    logger.info("Starting NGX Voice Sales Agent API on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)