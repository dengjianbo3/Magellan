#!/bin/bash
# Trading System Test Runner

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Trading System Test Suite ===${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest not found. Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Parse arguments
TEST_PATH="${1:-}"
COVERAGE_FLAG="${2:-}"

# Set default test timeout
export TEST_TIMEOUT="${TEST_TIMEOUT:-30}"

# Control real API usage (default: false)
export USE_REAL_LLM="${USE_REAL_LLM:-false}"
export USE_REAL_PRICE="${USE_REAL_PRICE:-false}"

echo "Configuration:"
echo "  - USE_REAL_LLM: $USE_REAL_LLM"
echo "  - USE_REAL_PRICE: $USE_REAL_PRICE"
echo "  - TEST_TIMEOUT: ${TEST_TIMEOUT}s"
echo ""

# Run tests based on arguments
if [ "$TEST_PATH" = "unit" ]; then
    echo -e "${GREEN}Running unit tests...${NC}"
    pytest unit/ -v -m "not slow"
    
elif [ "$TEST_PATH" = "integration" ]; then
    echo -e "${GREEN}Running integration tests...${NC}"
    pytest integration/ -v
    
elif [ "$TEST_PATH" = "slow" ]; then
    echo -e "${GREEN}Running slow tests...${NC}"
    pytest -v -m "slow"
    
elif [ "$TEST_PATH" = "critical" ]; then
    echo -e "${GREEN}Running critical tests...${NC}"
    pytest -v -m "critical"
    
elif [ "$COVERAGE_FLAG" = "--coverage" ] || [ "$TEST_PATH" = "--coverage" ]; then
    echo -e "${GREEN}Running all tests with coverage...${NC}"
    pytest -v \
        --cov=../../backend/services/report_orchestrator/app/core/trading \
        --cov-report=html \
        --cov-report=term-missing
    
    echo ""
    echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    
elif [ -n "$TEST_PATH" ] && [ -f "$TEST_PATH" ]; then
    echo -e "${GREEN}Running specific test file: $TEST_PATH${NC}"
    pytest "$TEST_PATH" -v -s
    
elif [ -z "$TEST_PATH" ]; then
    echo -e "${GREEN}Running all tests...${NC}"
    pytest -v
    
else
    echo -e "${RED}Unknown test path: $TEST_PATH${NC}"
    echo ""
    echo "Usage:"
    echo "  ./run_tests.sh                    # Run all tests"
    echo "  ./run_tests.sh unit               # Run unit tests only"
    echo "  ./run_tests.sh integration        # Run integration tests only"
    echo "  ./run_tests.sh critical           # Run critical tests only"
    echo "  ./run_tests.sh --coverage         # Run with coverage report"
    echo "  ./run_tests.sh path/to/test.py    # Run specific test file"
    exit 1
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo ""
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
