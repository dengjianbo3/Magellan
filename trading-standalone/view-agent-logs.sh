#!/bin/bash
# Agent System Log Viewer
# Focuses on agent execution flow, distinguishing prompts from results
#
# Usage:
#   ./view-agent-logs.sh          # Follow logs with agent highlights
#   ./view-agent-logs.sh --errors # Show only errors
#   ./view-agent-logs.sh --flow   # Show only execution flow
#   ./view-agent-logs.sh --tools  # Show only tool executions

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Parse arguments
MODE="${1:-all}"

case "$MODE" in
    --errors|-e)
        echo -e "${RED}🔴 Showing ERRORS only${NC}"
        FILTER="Error|Failed|failed|错误|❌"
        ;;
    --flow|-f)
        echo -e "${BLUE}📊 Showing execution FLOW only${NC}"
        FILTER="Phase|Meeting|Cycle|signal|SIGNAL|Decision|Scheduler"
        ;;
    --tools|-t)
        echo -e "${CYAN}🔧 Showing TOOL executions only${NC}"
        FILTER="Tool|tool|Step [0-9]|Executing|execute|tavily|get_market|get_klines|calculate_|get_fear|get_funding|black_swan"
        ;;
    --rewoo|-r)
        echo -e "${MAGENTA}🧠 Showing ReWOO phases only${NC}"
        FILTER="ReWOO|Phase 1|Phase 2|Phase 3|plan with|Executing.*tools|Solving"
        ;;
    --help|-h)
        echo "Agent System Log Viewer"
        echo ""
        echo "Usage: ./view-agent-logs.sh [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (none)      Show all logs with color highlighting"
        echo "  --errors    Show only errors and failures"
        echo "  --flow      Show execution flow (phases, decisions)"
        echo "  --tools     Show tool executions"
        echo "  --rewoo     Show ReWOO 3-phase execution"
        echo "  --help      Show this help"
        exit 0
        ;;
    *)
        echo -e "${GREEN}📋 Showing ALL agent logs with highlights${NC}"
        FILTER=""
        ;;
esac

echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${WHITE}Legend:${NC}"
echo -e "  ${RED}■${NC} ERROR     ${GREEN}■${NC} SUCCESS     ${YELLOW}■${NC} PHASE     ${BLUE}■${NC} AGENT"
echo -e "  ${CYAN}■${NC} TOOL      ${MAGENTA}■${NC} ReWOO       ${GRAY}■${NC} PROMPT"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Main log processing
docker compose logs -f trading_service 2>&1 | python3 -c "
import sys
import re

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
CYAN = '\033[0;36m'
WHITE = '\033[1;37m'
GRAY = '\033[0;90m'
NC = '\033[0m'
BOLD = '\033[1m'

# Filter pattern (empty means show all)
filter_pattern = '''$FILTER'''

for line in sys.stdin:
    try:
        # Decode unicode escapes
        try:
            line = line.encode('latin1').decode('unicode_escape')
        except:
            pass
        
        # Apply filter if set
        if filter_pattern and not re.search(filter_pattern, line, re.IGNORECASE):
            continue
        
        # Skip very long prompt content (likely full prompts)
        if len(line) > 500 and ('role' in line or 'parts' in line or 'system_prompt' in line):
            # Show truncated version
            short = line[:100].strip()
            print(f'{GRAY}[PROMPT] {short}...{NC}')
            continue
        
        # Highlight patterns
        output = line
        
        # ERRORS - Red
        if re.search(r'Error|Failed|failed|Exception|❌|错误', line, re.IGNORECASE):
            output = f'{RED}{BOLD}{line.strip()}{NC}'
        
        # SUCCESS - Green  
        elif re.search(r'✅|completed|success|Successfully', line, re.IGNORECASE):
            output = f'{GREEN}{line.strip()}{NC}'
        
        # PHASES - Yellow
        elif re.search(r'Phase [0-9]|## Phase|Meeting|Cycle.*START|Cycle.*END', line, re.IGNORECASE):
            output = f'{YELLOW}{BOLD}{line.strip()}{NC}'
        
        # AGENT names - Blue
        elif re.search(r'\[(TechnicalAnalyst|MacroEconomist|SentimentAnalyst|QuantStrategist|RiskAssessor|Leader|TradeExecutor)\]', line):
            output = f'{BLUE}{line.strip()}{NC}'
        
        # REWOO - Magenta
        elif re.search(r'\[ReWOO\]|Phase 1:|Phase 2:|Phase 3:|Generated plan|3-phase execution', line):
            output = f'{MAGENTA}{BOLD}{line.strip()}{NC}'
        
        # TOOLS - Cyan
        elif re.search(r'Step [0-9]+:|Tool.*result|Executing.*tool|tavily_search|get_market_price|get_klines|calculate_technical|get_fear_greed|get_funding_rate|black_swan', line, re.IGNORECASE):
            output = f'{CYAN}{line.strip()}{NC}'
        
        # SIGNALS - White Bold
        elif re.search(r'SIGNAL|direction=|confidence=|leverage=', line, re.IGNORECASE):
            output = f'{WHITE}{BOLD}{line.strip()}{NC}'
        
        # DECISIONS - Green Bold
        elif re.search(r'hold|open_long|open_short|close_position|Decision', line, re.IGNORECASE):
            match = line.strip()
            output = f'{GREEN}{BOLD}{match}{NC}'
        
        # HTTP/API calls - Gray
        elif re.search(r'HTTP Request|POST http|GET http', line):
            output = f'{GRAY}{line.strip()}{NC}'
        
        # Default
        else:
            output = line.strip()
        
        print(output)
        sys.stdout.flush()
        
    except Exception as e:
        print(line, end='')
"
