#!/bin/bash
# ===========================================
# Magellan Trading Standalone - Startup Script
# ===========================================
# Simplified: All config now in main project .env

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Magellan Trading Standalone - Startup    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Load environment from main project .env (single source of truth)
if [ -f "../.env" ]; then
    echo -e "  ${GREEN}✓${NC} Loading config from main project .env"
    set -a
    source "../.env"
    set +a
else
    echo -e "${RED}Error: Main project .env not found!${NC}"
    echo "Please create .env in the project root directory."
    exit 1
fi

echo ""
echo -e "${GREEN}Configuration loaded:${NC}"
echo "  Symbol:           ${TRADING_SYMBOL:-BTC-USDT-SWAP}"
echo "  Demo Mode:        ${OKX_DEMO_MODE:-true}"
echo "  Use OKX Trading:  ${USE_OKX_TRADING:-false}"
echo "  Analysis Interval: ${SCHEDULER_INTERVAL_HOURS:-2} hours"
echo ""
echo -e "${GREEN}Risk Control Settings:${NC}"
echo "  Max Leverage:     ${MAX_LEVERAGE:-20}x"
echo "  Position Range:   ${MIN_POSITION_PERCENT:-10}% - ${MAX_POSITION_PERCENT:-30}%"
echo "  Default Position: ${DEFAULT_POSITION_PERCENT:-20}%"
echo "  Min Confidence:   ${MIN_CONFIDENCE:-60}%"
echo "  Default TP/SL:    +${DEFAULT_TP_PERCENT:-5.0}% / -${DEFAULT_SL_PERCENT:-2.0}%"
echo ""

# Check required environment variables
echo -e "${BLUE}Checking required API keys...${NC}"

missing_keys=()

if [ -z "$GOOGLE_API_KEY" ] && [ "$DEFAULT_LLM_PROVIDER" == "gemini" ]; then
    missing_keys+=("GOOGLE_API_KEY")
fi

if [ -z "$KIMI_API_KEY" ] && [ "$DEFAULT_LLM_PROVIDER" == "kimi" ]; then
    missing_keys+=("KIMI_API_KEY")
fi

if [ -z "$DEEPSEEK_API_KEY" ] && [ "$DEFAULT_LLM_PROVIDER" == "deepseek" ]; then
    missing_keys+=("DEEPSEEK_API_KEY")
fi

if [ -z "$OKX_API_KEY" ]; then
    missing_keys+=("OKX_API_KEY")
fi

if [ -z "$OKX_SECRET_KEY" ]; then
    missing_keys+=("OKX_SECRET_KEY")
fi

if [ -z "$OKX_PASSPHRASE" ]; then
    missing_keys+=("OKX_PASSPHRASE")
fi

if [ ${#missing_keys[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required API keys:${NC}"
    for key in "${missing_keys[@]}"; do
        echo "  - $key"
    done
    echo ""
    echo "Please set these in the main project .env file."
    exit 1
fi

echo -e "${GREEN}All required API keys found.${NC}"
echo ""

# Create logs directory
mkdir -p logs

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running.${NC}"
    exit 1
fi

# Detect docker compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}Error: Neither 'docker compose' nor 'docker-compose' is available.${NC}"
    exit 1
fi

# Build and start services
echo -e "${BLUE}Starting Docker services...${NC}"
echo ""

# Smart rebuild
BUILD_FLAG=""
if [[ "$*" == *"--build"* ]] || [[ "$*" == *"-b"* ]]; then
    echo -e "${YELLOW}Build flag detected, rebuilding images...${NC}"
    BUILD_FLAG="--build"
elif ! docker images | grep -q "trading-standalone"; then
    echo -e "${YELLOW}Images not found, building for first time...${NC}"
    BUILD_FLAG="--build"
else
    echo -e "${GREEN}Using existing images (pass --build to force rebuild)${NC}"
fi

$DOCKER_COMPOSE up -d $BUILD_FLAG

# Wait for services
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"

max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if $DOCKER_COMPOSE ps | grep -q "healthy"; then
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done
echo ""

# Check service status
echo ""
echo -e "${BLUE}Service Status:${NC}"
$DOCKER_COMPOSE ps

# Start trading
echo ""
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Trading Service Started Successfully!    ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    echo "Useful commands:"
    echo "  ./logs.sh          - View live logs"
    echo "  ./logs.sh trading  - View trading service logs"
    echo "  ./stop.sh          - Stop all services"
    echo "  ./status.sh        - Check service status"
    echo ""
    echo -e "${GREEN}Web Dashboard:${NC}"
    echo "  http://localhost:8888/    - Trading status dashboard"
    echo ""

    # Auto-start trading
    echo -e "${YELLOW}Starting automatic trading...${NC}"
    sleep 5

    response=$(curl -s -X POST http://localhost:8000/api/trading/start 2>/dev/null || echo '{"error": "Service not ready"}')

    if echo "$response" | grep -q "success\|running"; then
        echo -e "${GREEN}Trading started successfully!${NC}"
        echo ""
        echo "The system will now:"
        echo "  1. Analyze the market every ${SCHEDULER_INTERVAL_HOURS:-2} hours"
        echo "  2. Execute trades based on AI analysis"
        echo "  3. Monitor positions for TP/SL"
    else
        echo -e "${YELLOW}Note: Trading auto-start pending. You can start manually:${NC}"
        echo "  curl -X POST http://localhost:8000/api/trading/start"
    fi
else
    echo -e "${RED}Warning: Some services may not be running properly.${NC}"
    echo "Check logs with: ./logs.sh"
fi
