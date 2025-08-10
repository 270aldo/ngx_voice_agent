# NGX Voice Sales Agent - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Making Your First Call](#making-your-first-call)
4. [Conversation Management](#conversation-management)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites
- NGX account with API access
- API key (get from dashboard)
- Node.js 16+ or Python 3.8+

### Installation

#### JavaScript/TypeScript
```bash
npm install @ngx/voice-sales-sdk
```

#### Python
```bash
pip install ngx-voice-sales
```

## Authentication

### Setting up your API key

#### JavaScript
```javascript
import { NGXVoiceSales } from '@ngx/voice-sales-sdk';

const client = new NGXVoiceSales({
  apiKey: 'your-api-key-here',
  baseUrl: 'https://api.ngx.com/v1' // optional
});
```

#### Python
```python
from ngx_voice_sales import NGXVoiceSales

client = NGXVoiceSales(
    api_key='your-api-key-here',
    base_url='https://api.ngx.com/v1'  # optional
)
```

## Making Your First Call

### Starting a conversation

#### JavaScript
```javascript
async function startConversation() {
  try {
    const conversation = await client.conversations.create({
      customerInfo: {
        name: "John Doe",
        businessType: "gym",
        businessSize: "medium"
      },
      initialMessage: "Hola, estoy interesado en mejorar mi gimnasio"
    });
    
    console.log('Conversation ID:', conversation.id);
    console.log('Agent response:', conversation.response);
  } catch (error) {
    console.error('Error:', error);
  }
}
```

#### Python
```python
async def start_conversation():
    try:
        conversation = await client.conversations.create(
            customer_info={
                "name": "John Doe",
                "business_type": "gym",
                "business_size": "medium"
            },
            initial_message="Hola, estoy interesado en mejorar mi gimnasio"
        )
        
        print(f"Conversation ID: {conversation.id}")
        print(f"Agent response: {conversation.response}")
    except Exception as e:
        print(f"Error: {e}")
```

## Conversation Management

### Continuing a conversation

#### JavaScript
```javascript
async function continueConversation(conversationId, message) {
  const response = await client.conversations.sendMessage({
    conversationId,
    message,
    includeAnalytics: true // optional
  });
  
  console.log('Agent:', response.message);
  console.log('Sentiment:', response.analytics?.sentiment);
  console.log('Intent:', response.analytics?.intent);
}
```

### Getting conversation history

#### JavaScript
```javascript
async function getHistory(conversationId) {
  const history = await client.conversations.getHistory(conversationId);
  
  history.messages.forEach(msg => {
    console.log(`${msg.role}: ${msg.content}`);
  });
}
```

## Advanced Features

### 1. Real-time Analytics

Monitor conversation metrics in real-time:

```javascript
const analytics = await client.analytics.getConversation(conversationId);

console.log('Conversion probability:', analytics.conversionProbability);
console.log('Customer sentiment:', analytics.sentiment);
console.log('Detected needs:', analytics.detectedNeeds);
console.log('Objection count:', analytics.objectionCount);
```

### 2. A/B Testing

Test different conversation strategies:

```javascript
// The SDK automatically handles A/B test variant selection
const conversation = await client.conversations.create({
  customerInfo: { /* ... */ },
  enableABTesting: true,
  testGroup: 'greeting_optimization' // optional
});
```

### 3. Voice Integration

Enable voice conversations:

```javascript
const voiceSession = await client.voice.createSession({
  conversationId,
  voiceProvider: 'elevenlabs',
  voiceId: 'sarah', // or custom voice ID
  language: 'es-ES'
});

// Handle voice events
voiceSession.on('transcription', (text) => {
  console.log('Customer said:', text);
});

voiceSession.on('response', (audio) => {
  // Play audio response
});
```

### 4. Lead Qualification

Get automatic lead scoring:

```javascript
const qualification = await client.qualification.analyze(conversationId);

console.log('Lead score:', qualification.score);
console.log('Tier recommendation:', qualification.recommendedTier);
console.log('Qualified:', qualification.isQualified);
```

### 5. ROI Calculation

Calculate potential ROI for customers:

```javascript
const roi = await client.roi.calculate({
  conversationId,
  businessMetrics: {
    currentMembers: 500,
    monthlyChurn: 0.15,
    averageTicket: 89
  }
});

console.log('Potential monthly savings:', roi.monthlySavings);
console.log('ROI percentage:', roi.roiPercentage);
console.log('Payback period:', roi.paybackMonths);
```

## Best Practices

### 1. Customer Information
Always provide as much customer context as possible:

```javascript
const conversation = await client.conversations.create({
  customerInfo: {
    name: "Maria Garcia",
    businessType: "studio",
    businessSize: "small",
    location: "Madrid",
    currentChallenges: ["client retention", "class scheduling"],
    monthlyBudget: 500
  }
});
```

### 2. Error Handling
Implement proper error handling:

```javascript
try {
  const response = await client.conversations.sendMessage({
    conversationId,
    message
  });
} catch (error) {
  if (error.code === 'RATE_LIMIT_EXCEEDED') {
    // Wait and retry
    await sleep(error.retryAfter * 1000);
  } else if (error.code === 'INVALID_MESSAGE') {
    // Handle invalid input
  }
}
```

### 3. Webhooks
Set up webhooks for important events:

```javascript
// Configure in your dashboard or via API
await client.webhooks.create({
  url: 'https://your-server.com/webhook',
  events: [
    'conversation.completed',
    'lead.qualified',
    'appointment.scheduled'
  ]
});
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
- **Error**: `401 Unauthorized`
- **Solution**: Check your API key is correct and active

#### 2. Rate Limiting
- **Error**: `429 Too Many Requests`
- **Solution**: Implement exponential backoff:

```javascript
async function retryWithBackoff(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (error.code === 'RATE_LIMIT_EXCEEDED' && i < maxRetries - 1) {
        await sleep(Math.pow(2, i) * 1000);
      } else {
        throw error;
      }
    }
  }
}
```

#### 3. Timeout Errors
- **Error**: `Request timeout`
- **Solution**: Increase timeout or optimize request:

```javascript
const client = new NGXVoiceSales({
  apiKey: 'your-api-key',
  timeout: 30000 // 30 seconds
});
```

### Debug Mode

Enable debug logging:

```javascript
const client = new NGXVoiceSales({
  apiKey: 'your-api-key',
  debug: true
});
```

## Support

- **Documentation**: https://docs.ngx.com
- **API Reference**: https://api.ngx.com/docs
- **Support Email**: support@ngx.com
- **Community Forum**: https://community.ngx.com