# NGX Voice Sales Agent API Documentation

## 🚀 Quick Start

### Viewing the Documentation

1. **Interactive Documentation (Swagger UI)**:
   - Open `swagger-ui.html` in your browser
   - Explore all endpoints interactively
   - Try out API calls directly from the browser

2. **OpenAPI Specification**:
   - View `openapi.yaml` for the complete API spec
   - Import into Postman, Insomnia, or other API tools
   - Generate client SDKs using OpenAPI generators

### Base URLs

- **Production**: `https://api.ngx-sales.com/v1`
- **Staging**: `https://staging-api.ngx-sales.com/v1`
- **Development**: `http://localhost:8000/v1`

## 🔐 Authentication

All endpoints require JWT authentication except:
- `POST /auth/login` - Get access token
- `POST /auth/register` - Create new account
- `GET /metrics` - Prometheus metrics (dev only)

### Getting Started

1. **Register an account**:
```bash
curl -X POST https://api.ngx-sales.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "company": "Acme Fitness"
  }'
```

2. **Login to get JWT token**:
```bash
curl -X POST https://api.ngx-sales.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "SecurePass123!"
  }'
```

3. **Use the token in subsequent requests**:
```bash
curl -X POST https://api.ngx-sales.com/v1/conversation/start \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_info": {
      "name": "Carlos Mendoza",
      "email": "carlos@gym.com",
      "business_type": "gym"
    }
  }'
```

## 📚 Key Endpoints

### Conversation Management
- `POST /conversation/start` - Start a new sales conversation
- `POST /conversation/{id}/message` - Send message in conversation
- `GET /conversation/{id}` - Get conversation state
- `POST /conversation/{id}/end` - End conversation

### Predictive ML
- `POST /predictive/objection/predict` - Predict customer objections
- `POST /predictive/needs/predict` - Identify customer needs
- `POST /predictive/conversion/predict` - Calculate conversion probability
- `POST /predictive/decision/optimize-flow` - Get optimal conversation strategy

### Analytics
- `GET /analytics/conversation/{id}` - Get conversation analytics
- `GET /analytics/aggregate` - Get aggregated metrics

### Lead Qualification
- `POST /qualification/score` - Calculate lead qualification score

## 🛠️ SDK Examples

### JavaScript/TypeScript
```typescript
import { NGXSalesAPI } from '@ngx/sales-sdk';

const api = new NGXSalesAPI({
  baseURL: 'https://api.ngx-sales.com/v1',
  token: 'YOUR_JWT_TOKEN'
});

// Start conversation
const conversation = await api.conversations.start({
  customer_info: {
    name: 'Maria Garcia',
    business_type: 'studio'
  }
});

// Send message
const response = await api.conversations.sendMessage(
  conversation.conversation_id,
  { message: '¿Cuánto cuesta el servicio?' }
);
```

### Python
```python
from ngx_sales import NGXSalesClient

client = NGXSalesClient(
    base_url='https://api.ngx-sales.com/v1',
    token='YOUR_JWT_TOKEN'
)

# Start conversation
conversation = client.conversations.start(
    customer_info={
        'name': 'Juan Pérez',
        'business_type': 'trainer'
    }
)

# Get predictions
predictions = client.predictive.predict_conversion(
    conversation_id=conversation.id,
    messages=conversation.messages
)
```

## 📊 Response Headers

All responses include:
- `X-Request-ID` - Unique request identifier for tracking
- `X-Rate-Limit-Limit` - Rate limit maximum
- `X-Rate-Limit-Remaining` - Remaining requests
- `X-Rate-Limit-Reset` - Reset timestamp

## 🚨 Error Handling

Errors follow a consistent format:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid authentication credentials",
    "details": {}
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-01-28T12:00:00Z"
}
```

Common error codes:
- `UNAUTHORIZED` - Invalid or missing token
- `RATE_LIMITED` - Too many requests
- `NOT_FOUND` - Resource not found
- `BAD_REQUEST` - Invalid request data

## 🔧 Development Tools

### Generate Client SDK
```bash
# Install OpenAPI Generator
npm install -g @openapitools/openapi-generator-cli

# Generate TypeScript SDK
openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-axios \
  -o ./sdk/typescript

# Generate Python SDK
openapi-generator-cli generate \
  -i openapi.yaml \
  -g python \
  -o ./sdk/python
```

### Import to Postman
1. Open Postman
2. Click "Import" → "File"
3. Select `openapi.yaml`
4. Configure environment variables

## 📞 Support

- **Documentation Issues**: dev@ngx.com
- **API Support**: support@ngx.com
- **Emergency**: +1-XXX-XXX-XXXX

## 🔄 Version History

- **v1.0.0** (Current) - Initial release with full conversation management, ML predictions, and analytics