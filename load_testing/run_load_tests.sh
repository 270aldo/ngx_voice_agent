#!/bin/bash

# Load Testing Runner Script for NGX Voice Sales Agent
# This script runs various load testing scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESULTS_DIR="./results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create results directory
mkdir -p "$RESULTS_DIR"

echo -e "${GREEN}🚀 NGX Voice Sales Agent - Load Testing Suite${NC}"
echo "================================================"

# Function to check if API is running
check_api() {
    echo -e "${YELLOW}Checking if API is running...${NC}"
    if curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✓ API is running${NC}"
        return 0
    else
        echo -e "${RED}✗ API is not running. Please start the API first.${NC}"
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing load testing dependencies...${NC}"
    pip install locust==2.17.0 requests
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Function to run a test scenario
run_scenario() {
    local scenario=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local description=$5
    
    echo ""
    echo -e "${YELLOW}Running scenario: ${description}${NC}"
    echo "Users: $users, Spawn rate: $spawn_rate/s, Duration: $duration"
    
    # Create scenario-specific results directory
    local scenario_dir="$RESULTS_DIR/${scenario}_${TIMESTAMP}"
    mkdir -p "$scenario_dir"
    
    # Run locust
    locust \
        --config locust.conf \
        --users "$users" \
        --spawn-rate "$spawn_rate" \
        --run-time "$duration" \
        --csv "$scenario_dir/results" \
        --html "$scenario_dir/report.html" \
        --headless \
        --only-summary \
        2>&1 | tee "$scenario_dir/output.log"
    
    echo -e "${GREEN}✓ Scenario completed. Results saved to: $scenario_dir${NC}"
}

# Function to generate summary report
generate_summary() {
    echo ""
    echo -e "${GREEN}📊 Generating Summary Report...${NC}"
    
    local summary_file="$RESULTS_DIR/summary_${TIMESTAMP}.md"
    
    cat > "$summary_file" << EOF
# NGX Voice Sales Agent - Load Testing Summary
Generated: $(date)

## Test Scenarios Executed

### 1. Baseline Test (10 users)
- Duration: 2 minutes
- Purpose: Establish baseline performance metrics

### 2. Standard Load (50 users)
- Duration: 5 minutes
- Purpose: Test normal operating conditions

### 3. Target Load (100 users)
- Duration: 10 minutes
- Purpose: Validate 100+ concurrent users requirement

### 4. Stress Test (200 users)
- Duration: 5 minutes
- Purpose: Find system breaking point

## Key Metrics to Review
- Response Time (p50, p95, p99)
- Requests per Second (RPS)
- Failure Rate
- CPU and Memory Usage

## Results Location
All detailed results are saved in: $RESULTS_DIR

## Recommendations
Review the HTML reports in each scenario directory for detailed analysis.
EOF

    echo -e "${GREEN}✓ Summary report generated: $summary_file${NC}"
}

# Main execution
main() {
    echo "Starting at: $(date)"
    
    # Check if API is running
    if ! check_api; then
        exit 1
    fi
    
    # Check if running with --install flag
    if [[ "$1" == "--install" ]]; then
        install_dependencies
        exit 0
    fi
    
    # Check if locust is installed
    if ! command -v locust &> /dev/null; then
        echo -e "${RED}Locust is not installed. Run: $0 --install${NC}"
        exit 1
    fi
    
    # Run test scenarios
    case "${1:-all}" in
        baseline)
            run_scenario "baseline" 10 2 "2m" "Baseline Performance Test"
            ;;
        standard)
            run_scenario "standard" 50 5 "5m" "Standard Load Test"
            ;;
        target)
            run_scenario "target" 100 10 "10m" "Target Load Test (100 users)"
            ;;
        stress)
            run_scenario "stress" 200 20 "5m" "Stress Test"
            ;;
        quick)
            # Quick test for development
            run_scenario "quick" 20 5 "1m" "Quick Development Test"
            ;;
        all)
            # Run all scenarios in sequence
            run_scenario "baseline" 10 2 "2m" "Baseline Performance Test"
            sleep 30  # Cool down between tests
            
            run_scenario "standard" 50 5 "5m" "Standard Load Test"
            sleep 30
            
            run_scenario "target" 100 10 "10m" "Target Load Test (100 users)"
            sleep 30
            
            run_scenario "stress" 200 20 "5m" "Stress Test"
            
            generate_summary
            ;;
        *)
            echo "Usage: $0 [all|baseline|standard|target|stress|quick|--install]"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}✅ Load testing completed at: $(date)${NC}"
    echo -e "Results saved in: ${RESULTS_DIR}"
}

# Run main function
main "$@"