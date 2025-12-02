#!/bin/bash
# ===========================================
# Magellan Trading Standalone - Log Viewer
# ===========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default values
SERVICE=""
LINES=100
FOLLOW=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        trading|llm|redis|all)
            SERVICE="$1"
            shift
            ;;
        -h|--help)
            echo "Usage: ./logs.sh [options] [service]"
            echo ""
            echo "Services:"
            echo "  trading    - Trading service logs"
            echo "  llm        - LLM Gateway logs"
            echo "  redis      - Redis logs"
            echo "  all        - All services (default)"
            echo ""
            echo "Options:"
            echo "  -f, --follow    Follow log output (like tail -f)"
            echo "  -n, --lines N   Show last N lines (default: 100)"
            echo "  -h, --help      Show this help"
            echo ""
            echo "Examples:"
            echo "  ./logs.sh                  # Show last 100 lines from all services"
            echo "  ./logs.sh trading -f       # Follow trading logs"
            echo "  ./logs.sh -n 50 llm        # Show last 50 lines of LLM logs"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h for help"
            exit 1
            ;;
    esac
done

# Map service names to docker-compose service names
case $SERVICE in
    trading)
        DOCKER_SERVICE="trading_service"
        ;;
    llm)
        DOCKER_SERVICE="llm_gateway"
        ;;
    redis)
        DOCKER_SERVICE="redis"
        ;;
    *)
        DOCKER_SERVICE=""
        ;;
esac

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Magellan Trading Standalone - Logs       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Build command
CMD="docker-compose logs"

if [ "$FOLLOW" = true ]; then
    CMD="$CMD -f"
fi

CMD="$CMD --tail=$LINES"

if [ -n "$DOCKER_SERVICE" ]; then
    CMD="$CMD $DOCKER_SERVICE"
fi

# Execute
echo -e "${CYAN}Command: $CMD${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to exit${NC}"
echo ""
echo "─────────────────────────────────────────────"
echo ""

$CMD
