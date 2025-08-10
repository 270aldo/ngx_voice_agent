/**
 * Advanced Features Example
 * This example demonstrates voice integration, webhooks, and real-time analytics
 */

import { NGXVoiceSales } from '@ngx/voice-sales-sdk';

const client = new NGXVoiceSales({
  apiKey: process.env.NGX_API_KEY
});

// Example 1: Voice-Enabled Conversation
async function voiceConversationExample() {
  console.log('\n🎤 VOICE CONVERSATION EXAMPLE');
  console.log('================================\n');
  
  // Start conversation
  const conversation = await client.conversations.create({
    customerInfo: {
      name: "Ana Martinez",
      businessType: "studio",
      preferredLanguage: "es-ES"
    }
  });
  
  // Enable voice
  const voiceSession = await client.voice.createSession({
    conversationId: conversation.id,
    voiceProvider: 'elevenlabs',
    voiceId: 'maria', // Spanish voice
    language: 'es-ES',
    streamingEnabled: true
  });
  
  // Handle voice events
  voiceSession.on('ready', () => {
    console.log('✅ Voice session ready');
  });
  
  voiceSession.on('transcription', (data) => {
    console.log(`👤 Customer said: "${data.text}"`);
    console.log(`   Confidence: ${data.confidence}`);
  });
  
  voiceSession.on('agent-speaking', (data) => {
    console.log(`🤖 Agent saying: "${data.text}"`);
  });
  
  voiceSession.on('sentiment-change', (sentiment) => {
    console.log(`📊 Sentiment changed to: ${sentiment}`);
  });
  
  // Start voice session
  await voiceSession.start();
  
  // Simulate conversation
  setTimeout(() => voiceSession.stop(), 30000); // 30 seconds demo
}

// Example 2: Real-time Analytics Dashboard
async function realtimeAnalyticsExample(conversationId) {
  console.log('\n📊 REAL-TIME ANALYTICS EXAMPLE');
  console.log('================================\n');
  
  // Set up real-time analytics stream
  const analyticsStream = await client.analytics.streamConversation(conversationId);
  
  analyticsStream.on('update', (metrics) => {
    console.clear();
    console.log('🎯 Live Conversation Metrics:');
    console.log('─────────────────────────────');
    console.log(`Conversion Probability: ${(metrics.conversionProbability * 100).toFixed(1)}%`);
    console.log(`Sentiment: ${metrics.sentiment} (${metrics.sentimentScore.toFixed(2)})`);
    console.log(`Engagement Score: ${(metrics.engagementScore * 100).toFixed(1)}%`);
    console.log(`Message Count: ${metrics.messageCount}`);
    console.log(`Time in Conversation: ${metrics.timeInSeconds}s`);
    console.log(`\nDetected Intents: ${metrics.detectedIntents.join(', ')}`);
    console.log(`Objections: ${metrics.objections.join(', ') || 'None'}`);
    console.log(`\nNext Best Action: ${metrics.recommendedAction}`);
    console.log(`Strategy: ${metrics.currentStrategy}`);
  });
  
  // Stop after 60 seconds
  setTimeout(() => analyticsStream.stop(), 60000);
}

// Example 3: A/B Testing with Custom Variants
async function abTestingExample() {
  console.log('\n🧪 A/B TESTING EXAMPLE');
  console.log('=======================\n');
  
  // Create an A/B test
  const abTest = await client.abTesting.create({
    name: 'greeting_optimization_q4',
    variants: [
      {
        id: 'formal',
        weight: 0.33,
        greeting: "Buenos días, soy María de NGX. ¿En qué puedo ayudarle con su negocio?"
      },
      {
        id: 'friendly',
        weight: 0.33,
        greeting: "¡Hola! Soy María de NGX 😊 Me encantaría conocer más sobre tu negocio"
      },
      {
        id: 'value_focused',
        weight: 0.34,
        greeting: "Hola, soy María de NGX. Ayudamos a negocios como el tuyo a crecer 10x. ¿Cuál es tu mayor reto?"
      }
    ],
    successMetric: 'conversion_rate',
    minimumSampleSize: 100
  });
  
  console.log(`Created A/B test: ${abTest.id}`);
  
  // Run 10 test conversations
  for (let i = 0; i < 10; i++) {
    const conversation = await client.conversations.create({
      customerInfo: {
        name: `Test Customer ${i}`,
        businessType: ['gym', 'studio', 'trainer'][i % 3]
      },
      abTestId: abTest.id
    });
    
    console.log(`Test ${i + 1}: Variant "${conversation.abTestVariant}" selected`);
  }
  
  // Get test results
  const results = await client.abTesting.getResults(abTest.id);
  console.log('\n📈 A/B Test Results:');
  results.variants.forEach(variant => {
    console.log(`\nVariant: ${variant.id}`);
    console.log(`  Conversations: ${variant.conversationCount}`);
    console.log(`  Conversion Rate: ${(variant.conversionRate * 100).toFixed(1)}%`);
    console.log(`  Confidence: ${(variant.confidence * 100).toFixed(1)}%`);
    console.log(`  Status: ${variant.isWinning ? '🏆 WINNING' : ''}`);
  });
}

// Example 4: Webhook Integration
async function webhookExample() {
  console.log('\n🔗 WEBHOOK INTEGRATION EXAMPLE');
  console.log('================================\n');
  
  // Register webhook
  const webhook = await client.webhooks.create({
    url: 'https://your-server.com/ngx-webhook',
    events: [
      'conversation.started',
      'conversation.completed',
      'lead.qualified',
      'objection.detected',
      'sentiment.negative',
      'appointment.scheduled',
      'tier.detected'
    ],
    headers: {
      'X-Custom-Header': 'your-secret'
    }
  });
  
  console.log(`Webhook created: ${webhook.id}`);
  console.log(`Endpoint: ${webhook.url}`);
  console.log(`Events: ${webhook.events.join(', ')}`);
  
  // Example webhook payload handler (for your server)
  console.log('\n📝 Example Webhook Handler:');
  console.log(`
app.post('/ngx-webhook', (req, res) => {
  const { event, data } = req.body;
  
  switch(event) {
    case 'lead.qualified':
      // Add to CRM
      crm.createLead({
        name: data.customerName,
        score: data.leadScore,
        tier: data.recommendedTier
      });
      break;
      
    case 'appointment.scheduled':
      // Add to calendar
      calendar.createEvent({
        title: \`NGX Demo - \${data.customerName}\`,
        date: data.appointmentDate,
        duration: 30
      });
      break;
      
    case 'sentiment.negative':
      // Alert team
      slack.sendAlert({
        channel: '#sales-alerts',
        message: \`⚠️ Negative sentiment detected in conversation \${data.conversationId}\`
      });
      break;
  }
  
  res.json({ received: true });
});
  `);
}

// Example 5: Custom Training Integration
async function customTrainingExample() {
  console.log('\n🎓 CUSTOM TRAINING EXAMPLE');
  console.log('===========================\n');
  
  // Upload custom training data
  const training = await client.training.uploadData({
    type: 'conversation_examples',
    data: [
      {
        context: "Customer owns a boutique gym in Madrid",
        customerMessage: "No creo que la IA pueda entender mi negocio único",
        idealResponse: "Entiendo tu preocupación. Cada negocio es único, por eso NGX aprende específicamente de TU gimnasio boutique. Ya trabajamos con más de 50 gimnasios boutique en Madrid, cada uno con su propia personalidad. ¿Qué hace especial a tu gimnasio?",
        outcome: "positive"
      },
      {
        context: "Yoga studio owner concerned about maintaining personal touch",
        customerMessage: "En yoga, la conexión personal es fundamental",
        idealResponse: "Absolutamente, la conexión humana es sagrada en yoga. NGX no reemplaza esa conexión, la amplifica. Imagina poder mantener esa misma calidez personal con cada alumno, incluso cuando no estás. Nuestros estudios de yoga reportan que sus alumnos se sienten MÁS conectados porque reciben atención personalizada 24/7.",
        outcome: "positive"
      }
    ]
  });
  
  console.log(`Training data uploaded: ${training.id}`);
  console.log(`Status: ${training.status}`);
  
  // Monitor training progress
  const checkProgress = setInterval(async () => {
    const status = await client.training.getStatus(training.id);
    console.log(`Training progress: ${status.progress}%`);
    
    if (status.complete) {
      clearInterval(checkProgress);
      console.log('✅ Training complete!');
      console.log(`Model version: ${status.modelVersion}`);
    }
  }, 5000);
}

// Run all examples
async function runAllExamples() {
  try {
    // Create a test conversation first
    const conversation = await client.conversations.create({
      customerInfo: {
        name: "Demo User",
        businessType: "gym"
      }
    });
    
    // Run examples
    await voiceConversationExample();
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    await realtimeAnalyticsExample(conversation.id);
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    await abTestingExample();
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    await webhookExample();
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    await customTrainingExample();
    
  } catch (error) {
    console.error('Error:', error);
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllExamples();
}

export {
  voiceConversationExample,
  realtimeAnalyticsExample,
  abTestingExample,
  webhookExample,
  customTrainingExample
};