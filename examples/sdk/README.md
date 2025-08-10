# NGX Voice Sales SDK Examples

This directory contains example code demonstrating how to use the NGX Voice Sales SDK in various programming languages.

## Quick Start

### JavaScript/TypeScript

1. Install the SDK:
```bash
npm install @ngx/voice-sales-sdk
```

2. Set your API key:
```bash
export NGX_API_KEY=your-api-key-here
```

3. Run examples:
```bash
node javascript/basic-conversation.js
node javascript/advanced-features.js
```

### Python

1. Install the SDK:
```bash
pip install ngx-voice-sales
```

2. Set your API key:
```bash
export NGX_API_KEY=your-api-key-here
```

3. Run examples:
```bash
python python/basic_conversation.py
python python/advanced_features.py
```

## Examples Overview

### Basic Examples

#### `basic-conversation`
- Starting a conversation
- Sending messages
- Handling responses
- Getting analytics
- ROI calculations

### Advanced Examples

#### `advanced-features`
- Voice-enabled conversations
- Real-time analytics streaming
- A/B testing setup
- Webhook integration
- Custom model training

### Integration Examples

#### `crm-integration` (Coming Soon)
- Salesforce integration
- HubSpot integration
- Custom CRM webhooks

#### `voice-platforms` (Coming Soon)
- Twilio integration
- VoIP integration
- Call center integration

## Common Patterns

### Error Handling

```javascript
try {
  const response = await client.conversations.sendMessage({
    conversationId,
    message
  });
} catch (error) {
  if (error.code === 'RATE_LIMIT_EXCEEDED') {
    await sleep(error.retryAfter * 1000);
    // Retry
  } else if (error.code === 'CONVERSATION_NOT_FOUND') {
    // Handle missing conversation
  } else {
    // Generic error handling
  }
}
```

### Async/Await Pattern

All SDK methods return promises and can be used with async/await:

```javascript
async function handleConversation() {
  const conversation = await client.conversations.create({...});
  const response = await client.conversations.sendMessage({...});
  const analytics = await client.analytics.getConversation(conversation.id);
}
```

### Event Handling

For real-time features:

```javascript
const stream = await client.analytics.streamConversation(conversationId);

stream.on('update', (data) => {
  // Handle updates
});

stream.on('error', (error) => {
  // Handle errors
});

stream.on('end', () => {
  // Stream ended
});
```

## Best Practices

1. **Always handle errors** - The API may return various error codes
2. **Use environment variables** for API keys - Never hardcode credentials
3. **Implement retry logic** for transient failures
4. **Monitor rate limits** - Respect the API rate limits
5. **Log important events** for debugging
6. **Test in staging** before production deployment

## Need Help?

- 📚 [Full Documentation](https://docs.ngx.com)
- 🔧 [API Reference](https://api.ngx.com/docs)
- 💬 [Community Forum](https://community.ngx.com)
- 📧 [Support](mailto:support@ngx.com)