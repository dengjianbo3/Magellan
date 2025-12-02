#!/bin/bash
# ===========================================
# Magellan Trading Standalone - Startup Script
# ===========================================

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

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}Error: config.yaml not found!${NC}"
    echo "Please create config.yaml from the template."
    exit 1
fi

# Check if .env exists, if not create from parent or template
if [ ! -f ".env" ]; then
    if [ -f "../.env" ]; then
        echo -e "${YELLOW}Creating .env from parent directory...${NC}"
        cp "../.env" ".env"
    else
        echo -e "${RED}Error: .env file not found!${NC}"
        echo "Please create .env with your API keys."
        exit 1
    fi
fi

# Load environment variables
source .env 2>/dev/null || true

# Parse config.yaml and export as environment variables
echo -e "${BLUE}Loading configuration from config.yaml...${NC}"

# Function to parse YAML (simple parser for our flat structure)
parse_yaml() {
    local yaml_file=$1
    local prefix=$2
    local s='[[:space:]]*'
    local w='[a-zA-Z0-9_]*'

    # Extract key values using grep and sed
    grep -E "^${s}[a-zA-Z_]+:" "$yaml_file" | while read line; do
        key=$(echo "$line" | sed 's/:.*//' | tr -d ' ')
        value=$(echo "$line" | sed 's/[^:]*://' | tr -d ' "' | sed 's/#.*//')

        if [[ -n "$value" && "$value" != "\${" && ! "$value" =~ ^\$ ]]; then
            echo "export ${prefix}${key}=\"${value}\""
        fi
    done
}

# Export trading config
export TRADING_SYMBOL=$(grep "symbol:" config.yaml | head -1 | sed 's/.*://' | tr -d ' "')
export TRADING_LEVERAGE=$(grep "leverage:" config.yaml | head -1 | sed 's/.*://' | tr -d ' ')
export TRADING_POSITION_SIZE=$(grep "position_size:" config.yaml | head -1 | sed 's/.*://' | tr -d ' ')
export TRADING_TP_PERCENT=$(grep "take_profit_percent:" config.yaml | sed 's/.*://' | tr -d ' ')
export TRADING_SL_PERCENT=$(grep "stop_loss_percent:" config.yaml | sed 's/.*://' | tr -d ' ')
export OKX_DEMO_MODE=$(grep "demo_mode:" config.yaml | tail -1 | sed 's/.*://' | tr -d ' ')
export SCHEDULER_INTERVAL_HOURS=$(grep "interval_hours:" config.yaml | head -1 | sed 's/.*://' | tr -d ' ')
export DEFAULT_LLM_PROVIDER=$(grep "provider:" config.yaml | head -1 | sed 's/.*://' | tr -d ' "')
export LOG_LEVEL=$(grep "level:" config.yaml | head -1 | sed 's/.*://' | tr -d ' "')
export REDIS_MAX_MEMORY=$(grep "redis_max_memory:" config.yaml | sed 's/.*://' | tr -d ' "')
export LLM_WORKERS=$(grep "llm_workers:" config.yaml | sed 's/.*://' | tr -d ' ')

# Email config
export EMAIL_ENABLED=$(grep "enabled:" config.yaml | head -1 | sed 's/.*://' | tr -d ' ')

echo ""
echo -e "${GREEN}Configuration loaded:${NC}"
echo "  Symbol:          ${TRADING_SYMBOL:-BTC-USDT-SWAP}"
echo "  Leverage:        ${TRADING_LEVERAGE:-10}x"
echo "  Position Size:   ${TRADING_POSITION_SIZE:-100} USDT"
echo "  Take Profit:     ${TRADING_TP_PERCENT:-5.0}%"
echo "  Stop Loss:       ${TRADING_SL_PERCENT:-3.0}%"
echo "  Demo Mode:       ${OKX_DEMO_MODE:-true}"
echo "  Analysis Interval: ${SCHEDULER_INTERVAL_HOURS:-4} hours"
echo "  LLM Provider:    ${DEFAULT_LLM_PROVIDER:-gemini}"
echo "  Email Enabled:   ${EMAIL_ENABLED:-false}"
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
    echo "Please set these in your .env file."
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

# Detect docker compose command (v2 uses "docker compose", v1 uses "docker-compose")
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Build and start services
echo -e "${BLUE}Starting Docker services...${NC}"
echo ""

$DOCKER_COMPOSE up -d --build

# Wait for services to be healthy
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

# Start trading if all services are up
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

    # Auto-start trading
    echo -e "${YELLOW}Starting automatic trading...${NC}"
    sleep 5

    response=$(curl -s -X POST http://localhost:8000/api/trading/start 2>/dev/null || echo '{"error": "Service not ready"}')

    if echo "$response" | grep -q "success\|running"; then
        echo -e "${GREEN}Trading started successfully!${NC}"
        echo ""
        echo "The system will now:"
        echo "  1. Analyze the market every ${SCHEDULER_INTERVAL_HOURS:-4} hours"
        echo "  2. Execute trades based on AI analysis"
        echo "  3. Monitor positions for TP/SL"
        if [ "$EMAIL_ENABLED" == "true" ]; then
            echo "  4. Send email notifications on decisions"
        fi
    else
        echo -e "${YELLOW}Note: Trading auto-start pending. You can start manually:${NC}"
        echo "  curl -X POST http://localhost:8000/api/trading/start"
    fi
else
    echo -e "${RED}Warning: Some services may not be running properly.${NC}"
    echo "Check logs with: ./logs.sh"
fi
