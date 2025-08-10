#!/bin/bash
# Run production load test with rate limits

echo "🚀 NGX Voice Sales Agent - Production Load Test"
echo "=============================================="
echo ""
echo "This test simulates production load with rate limiting enabled."
echo ""

# Check if mock server should be started
if [ "$1" == "with-server" ]; then
    echo "📦 Starting mock production server..."
    python scripts/mock_production_server.py &
    SERVER_PID=$!
    echo "Server PID: $SERVER_PID"
    echo "Waiting for server to start..."
    sleep 5
fi

# Run load test with different configurations
echo ""
echo "🧪 Test Configurations:"
echo "1. Quick test (10 users, 60 seconds)"
echo "2. Standard test (50 users, 5 minutes)"
echo "3. Stress test (100 users, 10 minutes)"
echo "4. Custom configuration"
echo ""

read -p "Select test configuration (1-4): " choice

case $choice in
    1)
        USERS=10
        DURATION=60
        RAMPUP=10
        ;;
    2)
        USERS=50
        DURATION=300
        RAMPUP=30
        ;;
    3)
        USERS=100
        DURATION=600
        RAMPUP=60
        ;;
    4)
        read -p "Number of users: " USERS
        read -p "Duration (seconds): " DURATION
        read -p "Ramp-up time (seconds): " RAMPUP
        ;;
    *)
        echo "Invalid choice. Using standard configuration."
        USERS=50
        DURATION=300
        RAMPUP=30
        ;;
esac

echo ""
echo "📊 Running load test with:"
echo "  - Users: $USERS"
echo "  - Duration: $DURATION seconds"
echo "  - Ramp-up: $RAMPUP seconds"
echo ""

# Run the load test
python scripts/production_load_test.py \
    --users $USERS \
    --duration $DURATION \
    --ramp-up $RAMPUP \
    --url http://localhost:8000/v1

# Clean up
if [ ! -z "$SERVER_PID" ]; then
    echo ""
    echo "🛑 Stopping mock server..."
    kill $SERVER_PID 2>/dev/null
fi

echo ""
echo "✅ Load test complete!"
echo "Check the generated JSON report for detailed results."