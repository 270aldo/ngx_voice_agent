#!/bin/bash
# =========================================
# NGX Voice Agent - New Repository Setup
# =========================================
# This script sets up the newly migrated repository
# Date: 2025-08-10

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

NEW_REPO_DIR="../ngx_voice_agent"

echo "🚀 NGX Voice Agent - Setting Up New Repository"
echo "=============================================="
echo ""

# Step 1: Navigate to new repository
echo -e "${BLUE}Step 1: Navigating to new repository...${NC}"
cd "$NEW_REPO_DIR"
pwd

# Step 2: Copy beta verification script
echo -e "${BLUE}Step 2: Copying verification scripts...${NC}"
cp ../ngx_closer.Agent/beta_verification.sh . 2>/dev/null || echo "Verification script already exists"
chmod +x beta_verification.sh 2>/dev/null || true

# Step 3: Setup Python environment
echo -e "${BLUE}Step 3: Setting up Python environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Step 4: Install Python dependencies
echo -e "${BLUE}Step 4: Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Python dependencies installed"

# Step 5: Setup frontend dependencies
echo -e "${BLUE}Step 5: Setting up frontend...${NC}"
cd apps/pwa
npm install
echo "✅ Frontend dependencies installed"

# Step 6: Build frontend
echo -e "${BLUE}Step 6: Building frontend...${NC}"
npm run build
echo "✅ Frontend built successfully"

# Return to root
cd ../..

# Step 7: Setup environment variables
echo -e "${BLUE}Step 7: Setting up environment variables...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️  .env file created from .env.example${NC}"
        echo -e "${YELLOW}   Please update with your actual credentials!${NC}"
    else
        echo -e "${RED}❌ No .env.example found${NC}"
    fi
else
    echo "✅ .env file already exists"
fi

# Step 8: Run verification
echo ""
echo -e "${BLUE}Step 8: Running beta verification...${NC}"
./beta_verification.sh

# Step 9: Summary
echo ""
echo "=============================================="
echo -e "${GREEN}✅ NEW REPOSITORY SETUP COMPLETE!${NC}"
echo "=============================================="
echo ""
echo "Repository Path: $NEW_REPO_DIR"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Update .env with production credentials"
echo "2. Review verification results above"
echo "3. Start development server:"
echo "   - Backend: python -m uvicorn src.api.main:app --reload"
echo "   - Frontend: cd apps/pwa && npm run dev"
echo ""
echo "4. For production deployment:"
echo "   - Backend: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
echo "   - Frontend: cd apps/pwa && npm run preview"
echo ""
echo -e "${GREEN}Beta Launch Target: 2025-08-13${NC}"
echo "=============================================="