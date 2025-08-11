/**
 * Basic Conversation Example
 * This example shows how to start and manage a basic sales conversation
 */

import { NGXVoiceSales } from '@ngx/voice-sales-sdk';

// Initialize the client
const client = new NGXVoiceSales({
  apiKey: process.env.NGX_API_KEY
});

async function main() {
  try {
    // 1. Start a new conversation
    console.log('Starting conversation...');
    
    const conversation = await client.conversations.create({
      customerInfo: {
        name: "Carlos Rodriguez",
        businessType: "gym",
        businessSize: "medium",
        location: "Barcelona",
        currentChallenges: ["member retention", "engagement"]
      },
      initialMessage: "Hola, tengo un gimnasio con 500 miembros y estoy perdiendo clientes"
    });
    
    console.log('\n🤖 Agent:', conversation.response);
    console.log('📊 Conversation ID:', conversation.id);
    
    // 2. Continue the conversation
    console.log('\n👤 Customer: ¿Cuánto cuesta NGX?');
    
    const response1 = await client.conversations.sendMessage({
      conversationId: conversation.id,
      message: "¿Cuánto cuesta NGX?",
      includeAnalytics: true
    });
    
    console.log('🤖 Agent:', response1.message);
    console.log('📈 Sentiment:', response1.analytics.sentiment);
    
    // 3. Handle objection
    console.log('\n👤 Customer: Me parece caro para mi presupuesto');
    
    const response2 = await client.conversations.sendMessage({
      conversationId: conversation.id,
      message: "Me parece caro para mi presupuesto"
    });
    
    console.log('🤖 Agent:', response2.message);
    
    // 4. Get ROI calculation
    console.log('\n💰 Calculating ROI...');
    
    const roi = await client.roi.calculate({
      conversationId: conversation.id,
      businessMetrics: {
        currentMembers: 500,
        monthlyChurn: 0.15,
        averageTicket: 89,
        currentMonthlyRevenue: 44500
      }
    });
    
    console.log('📊 ROI Analysis:');
    console.log(`  - Monthly Savings: €${roi.monthlySavings}`);
    console.log(`  - ROI: ${roi.roiPercentage}%`);
    console.log(`  - Payback Period: ${roi.paybackMonths} months`);
    
    // 5. Get conversation summary
    const summary = await client.analytics.getConversation(conversation.id);
    
    console.log('\n📋 Conversation Summary:');
    console.log(`  - Conversion Probability: ${(summary.conversionProbability * 100).toFixed(1)}%`);
    console.log(`  - Customer Sentiment: ${summary.sentiment}`);
    console.log(`  - Detected Needs: ${summary.detectedNeeds.join(', ')}`);
    console.log(`  - Recommended Tier: ${summary.recommendedTier}`);
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    
    if (error.code === 'RATE_LIMIT_EXCEEDED') {
      console.log(`⏱️  Retry after ${error.retryAfter} seconds`);
    }
  }
}

// Run the example
main();