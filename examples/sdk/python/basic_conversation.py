"""
Basic Conversation Example
This example shows how to start and manage a basic sales conversation
"""

import asyncio
import os
from ngx_voice_sales import NGXVoiceSales

# Initialize the client
client = NGXVoiceSales(
    api_key=os.environ.get('NGX_API_KEY')
)


async def main():
    try:
        # 1. Start a new conversation
        print('Starting conversation...')
        
        conversation = await client.conversations.create(
            customer_info={
                "name": "Carlos Rodriguez",
                "business_type": "gym",
                "business_size": "medium",
                "location": "Barcelona",
                "current_challenges": ["member retention", "engagement"]
            },
            initial_message="Hola, tengo un gimnasio con 500 miembros y estoy perdiendo clientes"
        )
        
        print(f'\n🤖 Agent: {conversation.response}')
        print(f'📊 Conversation ID: {conversation.id}')
        
        # 2. Continue the conversation
        print('\n👤 Customer: ¿Cuánto cuesta NGX?')
        
        response1 = await client.conversations.send_message(
            conversation_id=conversation.id,
            message="¿Cuánto cuesta NGX?",
            include_analytics=True
        )
        
        print(f'🤖 Agent: {response1.message}')
        print(f'📈 Sentiment: {response1.analytics.sentiment}')
        
        # 3. Handle objection
        print('\n👤 Customer: Me parece caro para mi presupuesto')
        
        response2 = await client.conversations.send_message(
            conversation_id=conversation.id,
            message="Me parece caro para mi presupuesto"
        )
        
        print(f'🤖 Agent: {response2.message}')
        
        # 4. Get ROI calculation
        print('\n💰 Calculating ROI...')
        
        roi = await client.roi.calculate(
            conversation_id=conversation.id,
            business_metrics={
                "current_members": 500,
                "monthly_churn": 0.15,
                "average_ticket": 89,
                "current_monthly_revenue": 44500
            }
        )
        
        print('📊 ROI Analysis:')
        print(f'  - Monthly Savings: €{roi.monthly_savings}')
        print(f'  - ROI: {roi.roi_percentage}%')
        print(f'  - Payback Period: {roi.payback_months} months')
        
        # 5. Get conversation summary
        summary = await client.analytics.get_conversation(conversation.id)
        
        print('\n📋 Conversation Summary:')
        print(f'  - Conversion Probability: {summary.conversion_probability * 100:.1f}%')
        print(f'  - Customer Sentiment: {summary.sentiment}')
        print(f'  - Detected Needs: {", ".join(summary.detected_needs)}')
        print(f'  - Recommended Tier: {summary.recommended_tier}')
        
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        
        if hasattr(e, 'code') and e.code == 'RATE_LIMIT_EXCEEDED':
            print(f'⏱️  Retry after {e.retry_after} seconds')


# Run the example
if __name__ == "__main__":
    asyncio.run(main())