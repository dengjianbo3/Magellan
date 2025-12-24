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
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp ".env.example" ".env"
        echo -e "${GREEN}Created .env - please review and customize if needed${NC}"
    fi
fi

# Load environment variables
# Priority: 1. Root project .env (API keys), 2. Local .env (trading overrides)
echo -e "${BLUE}Loading configuration...${NC}"

# First, load root project .env for shared API keys
if [ -f "../.env" ]; then
    echo -e "  ${GREEN}✓${NC} Loading shared API keys from root .env"
    source "../.env" 2>/dev/null || true
fi

# Then, load local .env for trading-specific overrides
if [ -f ".env" ]; then
    echo -e "  ${GREEN}✓${NC} Loading trading overrides from local .env"
    source ".env" 2>/dev/null || true
fi

# Configuration loading priority: local .env > root .env > config.yaml > defaults
echo -e "${BLUE}Configuration priority: local .env > root .env > config.yaml > defaults${NC}"

# Helper function: get value from config.yaml
get_yaml_value() {
    local key=$1
    grep "${key}:" config.yaml 2>/dev/null | head -1 | sed 's/.*://' | tr -d ' "' | sed 's/#.*//'
}

# Helper function: set env var if not already set (priority: .env > yaml > default)
set_if_empty() {
    local var_name=$1
    local yaml_key=$2
    local default_val=$3

    # If already set from .env, keep it
    if [ -n "${!var_name}" ]; then
        return
    fi

    # Try to get from config.yaml
    local yaml_val=$(get_yaml_value "$yaml_key")
    if [ -n "$yaml_val" ]; then
        export "$var_name"="$yaml_val"
        return
    fi

    # Use default
    if [ -n "$default_val" ]; then
        export "$var_name"="$default_val"
    fi
}

# Trading config (priority: .env > config.yaml > defaults)
set_if_empty TRADING_SYMBOL "symbol" "BTC-USDT-SWAP"
set_if_empty OKX_DEMO_MODE "demo_mode" "true"

# Scheduler config
set_if_empty SCHEDULER_INTERVAL_HOURS "interval_hours" "4"
set_if_empty COOLDOWN_HOURS "cooldown_hours" "24"
set_if_empty MAX_CONSECUTIVE_LOSSES "max_consecutive_losses" "3"

# Risk control config
set_if_empty MAX_LEVERAGE "max_leverage" "20"
set_if_empty MAX_POSITION_PERCENT "max_position_percent" "30"
set_if_empty MIN_POSITION_PERCENT "min_position_percent" "10"
set_if_empty DEFAULT_POSITION_PERCENT "default_position_percent" "20"
set_if_empty MIN_CONFIDENCE "min_confidence" "60"
set_if_empty DEFAULT_TP_PERCENT "default_tp_percent" "5.0"
set_if_empty DEFAULT_SL_PERCENT "default_sl_percent" "2.0"

# Other config
set_if_empty DEFAULT_LLM_PROVIDER "provider" "deepseek"
set_if_empty LOG_LEVEL "level" "INFO"
set_if_empty EMAIL_ENABLED "enabled" "false"

echo ""
echo -e "${GREEN}Configuration loaded:${NC}"
echo "  Symbol:          ${TRADING_SYMBOL:-BTC-USDT-SWAP}"
echo "  Demo Mode:       ${OKX_DEMO_MODE:-true}"
echo "  Analysis Interval: ${SCHEDULER_INTERVAL_HOURS:-4} hours"
echo ""
echo -e "${GREEN}Risk Control Settings:${NC}"
echo "  Max Leverage:    ${MAX_LEVERAGE:-20}x"
echo "  Position Range:  ${MIN_POSITION_PERCENT:-10}% - ${MAX_POSITION_PERCENT:-30}%"
echo "  Default Position: ${DEFAULT_POSITION_PERCENT:-20}%"
echo "  Min Confidence:  ${MIN_CONFIDENCE:-60}%"
echo "  Default TP/SL:   +${DEFAULT_TP_PERCENT:-5.0}% / -${DEFAULT_SL_PERCENT:-2.0}%"
echo ""
echo -e "${GREEN}Other Settings:${NC}"
echo "  Cooldown Hours:  ${COOLDOWN_HOURS:-24}"
echo "  Max Losses:      ${MAX_CONSECUTIVE_LOSSES:-3}"
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
elif docker-compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}Error: Neither 'docker compose' nor 'docker-compose' is available.${NC}"
    exit 1
fi

# Build and start services
echo -e "${BLUE}Starting Docker services...${NC}"
echo ""

# Smart rebuild: only build if --build flag is passed or if images don't exist
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
