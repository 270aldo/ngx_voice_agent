#!/bin/bash
# =========================================
# NGX Voice Agent - Beta Verification Script
# =========================================
# This script verifies all critical components before beta launch
# Date: 2025-08-10
# Target Beta: 2025-08-13

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🚀 NGX Voice Agent - Beta Launch Verification"
echo "=============================================="
echo "Target Launch: 2025-08-13"
echo ""

# Initialize counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to check status
check_status() {
    local name="$1"
    local command="$2"
    local critical="$3"
    
    echo -n "Checking $name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        if [ "$critical" = "true" ]; then
            echo -e "${RED}❌ FAILED (CRITICAL)${NC}"
            ((FAILED++))
            return 1
        else
            echo -e "${YELLOW}⚠️  WARNING${NC}"
            ((WARNINGS++))
            return 0
        fi
    fi
}

echo -e "${BLUE}=== ENVIRONMENT CHECKS ===${NC}"
check_status "Python 3.11+" "python3 --version | grep -E '3\.(1[1-9]|[2-9][0-9])'" true
check_status "Node.js 18+" "node --version | grep -E 'v(1[8-9]|[2-9][0-9])'" true
check_status "PostgreSQL client" "which psql" false
check_status "Redis client" "which redis-cli" false

echo ""
echo -e "${BLUE}=== CONFIGURATION CHECKS ===${NC}"
check_status ".env file exists" "[ -f .env ]" true
check_status ".env.example exists" "[ -f .env.example ]" false
check_status "JWT_SECRET configured" "grep -q 'JWT_SECRET=' .env && ! grep -q 'JWT_SECRET=your-secret' .env" true
check_status "SUPABASE_URL configured" "grep -q 'SUPABASE_URL=' .env" true
check_status "SUPABASE_KEY configured" "grep -q 'SUPABASE_ANON_KEY=' .env" true

echo ""
echo -e "${BLUE}=== BACKEND CHECKS ===${NC}"
check_status "requirements.txt exists" "[ -f requirements.txt ]" true
check_status "FastAPI installed" "python3 -c 'import fastapi' 2>/dev/null" true
check_status "Main API file" "[ -f src/api/main.py ]" true
check_status "Config file" "[ -f src/config/settings.py ]" true
check_status "JWT handler" "[ -f src/auth/jwt_handler.py ]" true
check_status "WebSocket manager" "[ -f src/services/websocket/websocket_manager.py ]" true
check_status "Session manager" "[ -f src/services/websocket/session_manager.py ]" true
check_status "Rate limiter" "[ -f src/api/middleware/rate_limiter.py ]" true

echo ""
echo -e "${BLUE}=== FRONTEND CHECKS ===${NC}"
check_status "PWA directory" "[ -d apps/pwa ]" true
check_status "package.json" "[ -f apps/pwa/package.json ]" true
check_status "Frontend dependencies" "[ -d apps/pwa/node_modules ]" false
check_status "Vite config" "[ -f apps/pwa/vite.config.ts ]" true
check_status "TypeScript config" "[ -f apps/pwa/tsconfig.json ]" true

echo ""
echo -e "${BLUE}=== SECURITY CHECKS ===${NC}"
check_status "No hardcoded secrets" "! grep -r 'sk-[a-zA-Z0-9]{48}' src/ 2>/dev/null | grep -v 'sk-\*\*\*' | grep -v 'regex' | grep -v 'pattern'" true
check_status "No debug mode in production" "! grep -r 'DEBUG.*=.*True' src/config/settings.py" true
check_status "CORS configured" "grep -q 'CORSMiddleware' src/api/main.py" true
check_status "Rate limiting enabled" "grep -q 'RateLimiter' src/api/main.py" true

echo ""
echo -e "${BLUE}=== ML PIPELINE CHECKS ===${NC}"
check_status "ML services directory" "[ -d src/services/ml ]" true
check_status "Objection prediction" "[ -f src/services/ml/objection_prediction.py ]" true
check_status "Needs prediction" "[ -f src/services/ml/needs_prediction.py ]" true
check_status "Conversion prediction" "[ -f src/services/ml/conversion_prediction.py ]" true
check_status "Decision engine" "[ -f src/services/ml/decision_engine.py ]" true

echo ""
echo -e "${BLUE}=== TEST SUITE CHECKS ===${NC}"
check_status "Tests directory" "[ -d tests ]" true
check_status "Test runner" "[ -f tests/master_test_runner.py ]" false
check_status "Safe tests script" "[ -f tests/run_safe_tests.sh ]" false

echo ""
echo -e "${BLUE}=== DOCUMENTATION CHECKS ===${NC}"
check_status "README.md" "[ -f README.md ]" true
check_status "CLAUDE.md" "[ -f CLAUDE.md ]" true
check_status "API documentation" "[ -f docs/API_REFERENCE.md ]" false
check_status "Deployment guide" "[ -f docs/DEPLOYMENT.md ]" false

echo ""
echo "=============================================="
echo -e "${BLUE}VERIFICATION SUMMARY${NC}"
echo "=============================================="
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo ""

# Calculate readiness percentage
TOTAL=$((PASSED + WARNINGS + FAILED))
READINESS=$((PASSED * 100 / TOTAL))

echo -e "Beta Readiness: ${BLUE}${READINESS}%${NC}"
echo ""

# Final status
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ READY FOR BETA LAUNCH!${NC}"
    echo "All critical checks passed. You can proceed with beta deployment."
else
    echo -e "${RED}❌ NOT READY FOR BETA${NC}"
    echo "Please fix the $FAILED critical issues before launching beta."
    echo ""
    echo "Critical issues to fix:"
    if ! python3 --version | grep -E '3\.(1[1-9]|[2-9][0-9])' > /dev/null 2>&1; then
        echo "  - Install Python 3.11 or higher"
    fi
    if ! node --version | grep -E 'v(1[8-9]|[2-9][0-9])' > /dev/null 2>&1; then
        echo "  - Install Node.js 18 or higher"
    fi
    if [ ! -f .env ]; then
        echo "  - Create .env file from .env.example"
    fi
    if ! grep -q 'JWT_SECRET=' .env || grep -q 'JWT_SECRET=your-secret' .env 2>/dev/null; then
        echo "  - Configure JWT_SECRET in .env"
    fi
fi

echo ""
echo "=============================================="
echo "Next Steps for Beta Launch:"
echo "1. Run migration script: ./migrate_to_new_repo.sh"
echo "2. Install dependencies: pip install -r requirements.txt && cd apps/pwa && npm install"
echo "3. Run this verification again: ./beta_verification.sh"
echo "4. Deploy to staging environment"
echo "5. Perform final testing"
echo "6. Launch beta on 2025-08-13"
echo "=============================================="