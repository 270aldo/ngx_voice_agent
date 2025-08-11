#!/bin/bash

# NGX Voice Sales Agent - Real Tests Runner
# Este script ejecuta todos los tests con la API real

echo "🚀 NGX Voice Sales Agent - Real Tests Suite"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if API is running
echo "🔍 Checking if API is running..."
API_URL="${API_URL:-http://localhost:8000}"
if curl -s "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ API is running at $API_URL${NC}"
else
    echo -e "${RED}❌ API is not running at $API_URL${NC}"
    echo "Please start the API with: python run.py"
    exit 1
fi

# Check environment variables
echo ""
echo "🔐 Checking environment..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set. Loading from .env...${NC}"
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    else
        echo -e "${RED}❌ No .env file found${NC}"
        exit 1
    fi
fi

# Create results directory
mkdir -p tests/results

# Function to run a test
run_test() {
    local test_name=$1
    local test_file=$2
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧪 Running: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    python "$test_file"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $test_name completed successfully${NC}"
    else
        echo -e "${RED}❌ $test_name failed${NC}"
    fi
}

# Test 1: API Validation
run_test "API Validation Test" "tests/real_api_validation.py"

# Test 2: Conversation Quality
echo ""
echo -e "${YELLOW}⏸️  Pausing 5 seconds before quality test...${NC}"
sleep 5
run_test "Conversation Quality Test" "tests/real_conversation_quality_test.py"

# Test 3: Load Test (Optional - takes longer)
echo ""
echo -e "${YELLOW}🤔 Run load test? This will take 10-15 minutes. (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}⏸️  Pausing 10 seconds before load test...${NC}"
    sleep 10
    run_test "Progressive Load Test" "tests/real_load_test.py"
else
    echo "Skipping load test."
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST SUITE COMPLETED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Results saved in: tests/results/"
echo ""
echo "Latest results:"
ls -la tests/results/ | tail -5
echo ""
echo -e "${GREEN}✨ All tests completed!${NC}"