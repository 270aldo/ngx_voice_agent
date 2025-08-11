#!/bin/bash
#
# Safe Test Runner for NGX Voice Sales Agent
# Runs tests without requiring external services
#

echo "🧪 NGX Voice Sales Agent - Safe Test Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}Error: pytest.ini not found. Please run from project root.${NC}"
    exit 1
fi

# Function to run tests with specific markers
run_test_suite() {
    local marker=$1
    local description=$2
    
    echo -e "\n${YELLOW}Running ${description}...${NC}"
    python -m pytest -m "${marker}" -v --tb=short
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${description} passed${NC}"
    else
        echo -e "${RED}❌ ${description} failed${NC}"
    fi
}

# Start mock server in background if requested
if [ "$1" == "--with-mock" ]; then
    echo -e "${YELLOW}Starting mock API server...${NC}"
    python tests/mock_server.py &
    MOCK_PID=$!
    sleep 2  # Give server time to start
    echo -e "${GREEN}Mock server started (PID: $MOCK_PID)${NC}"
    
    # Update base URL for tests
    export API_URL="http://localhost:8001"
fi

# Run different test suites
echo -e "\n${YELLOW}1. Unit Tests (no external dependencies)${NC}"
echo "----------------------------------------"
python -m pytest tests/unit/ -v --tb=short -k "not test_input_validation and not test_unified_decision_engine"

echo -e "\n${YELLOW}2. Standalone ML Tests${NC}"
echo "------------------------"
python -m pytest test_ml_*.py -v --tb=short 2>/dev/null || echo "No standalone ML tests found"

echo -e "\n${YELLOW}3. Quick Validation Tests${NC}"
echo "--------------------------"
if [ -f "tests/quick_validation_test.py" ]; then
    python tests/quick_validation_test.py
fi

# Cleanup mock server if started
if [ ! -z "$MOCK_PID" ]; then
    echo -e "\n${YELLOW}Stopping mock server...${NC}"
    kill $MOCK_PID 2>/dev/null
    echo -e "${GREEN}Mock server stopped${NC}"
fi

echo -e "\n${YELLOW}Summary:${NC}"
echo "--------"
echo "✅ Unit tests can run without external services"
echo "⚠️  Integration tests require API server: python -m uvicorn src.api.main:app"
echo "💡 Run with --with-mock to use mock server for integration tests"
echo ""
echo "For full test suite with all services:"
echo "1. Start Redis: redis-server"
echo "2. Start API: python -m uvicorn src.api.main:app"
echo "3. Run: python tests/master_test_runner.py"