#!/bin/bash
# View agent discussions and tool calls only - Clean output
# 只显示agent讨论内容和工具调用结果,过滤掉prompt、API调用等噪音

docker compose logs -f trading_service 2>&1 | python3 -c "
import sys
import codecs
import re

# Set stdout to UTF-8
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='ignore')

# Colors for terminal output
RESET = '\033[0m'
BOLD = '\033[1m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RED = '\033[91m'

# Track state
in_agent_response = False
in_tool_result = False
current_agent = None
buffer = []

def should_skip_line(line):
    '''Skip noisy lines we don't want to see'''
    skip_patterns = [
        # Skip HTTP requests and responses
        r'POST /chat',
        r'GET /',
        r'HTTP/1\.',
        r'Content-Type:',
        r'Connection:',
        r'Host:',
        r'User-Agent:',

        # Skip LLM API calls
        r'Making LLM call',
        r'LLM call completed',
        r'Request to provider',
        r'Response from provider',
        r'llm_gateway',

        # Skip prompt construction and messages
        r'System prompt:',
        r'User prompt:',
        r'Prompt tokens:',
        r'Completion tokens:',
        r'Sending prompt to',
        r'role.*:.*system',
        r'role.*:.*user',

        # Skip prompt content indicators
        r'You are.*expert',
        r'You are.*analyst',
        r'Your task is',
        r'Please analyze',
        r'Based on.*provide',
        r'Consider.*factors',

        # Skip generic INFO logs
        r'INFO:.*uvicorn',
        r'INFO:.*fastapi',
        r'Accepted connection',

        # Skip WebSocket noise
        r'WebSocket.*connected',
        r'WebSocket.*disconnected',
        r'Sending.*via WebSocket',

        # Skip raw JSON dumps (but keep parsed results)
        r'^\s*\{\"messages\"',
        r'^\s*\{\"id\":',
        r'^\s*\"role\":',
        r'^\s*\"content\":',
    ]

    for pattern in skip_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False

def print_colored(text, color='', bold=False):
    '''Print with colors'''
    prefix = BOLD if bold else ''
    print(f'{prefix}{color}{text}{RESET}')

def format_agent_header(agent_name, phase=''):
    '''Format agent discussion header'''
    separator = '=' * 80
    phase_text = f' [{phase}]' if phase else ''
    print_colored(separator, CYAN)
    print_colored(f'🤖 {agent_name}{phase_text}', CYAN, bold=True)
    print_colored(separator, CYAN)

def format_tool_header(tool_name):
    '''Format tool call header'''
    print_colored(f'\\n🔧 Tool: {tool_name}', YELLOW, bold=True)

def format_vote_summary(text):
    '''Format vote summary'''
    print_colored('\\n📊 Vote Summary:', GREEN, bold=True)
    print_colored(text, GREEN)

for line in sys.stdin:
    try:
        # Try to decode unicode escape sequences
        try:
            decoded = line.encode('latin1').decode('unicode_escape')
        except:
            decoded = line

        # Skip noisy lines
        if should_skip_line(decoded):
            continue

        # Detect phase transitions
        if 'Phase:' in decoded or '阶段:' in decoded:
            phase_match = re.search(r'Phase: ([A-Za-z_]+)|阶段: (.+)', decoded)
            if phase_match:
                phase = phase_match.group(1) or phase_match.group(2)
                print_colored(f'\\n📍 {phase}', MAGENTA, bold=True)
                continue

        # Detect agent discussions
        agent_match = re.search(r'\\[(\\w+Agent|Leader|RiskAssessor)\\]', decoded)
        if agent_match:
            agent = agent_match.group(1)
            if current_agent != agent:
                current_agent = agent
                format_agent_header(agent)

            # Extract and print agent message (remove log prefix)
            message = re.sub(r'^.*?\\[(\\w+Agent|Leader|RiskAssessor)\\]\\s*', '', decoded)
            print_colored(message.strip(), '')
            continue

        # Detect tool calls
        if 'Tool Calling:' in decoded or '工具调用:' in decoded:
            tool_match = re.search(r'Tool.*?: ([a-z_]+)', decoded, re.IGNORECASE)
            if tool_match:
                format_tool_header(tool_match.group(1))
            continue

        # Detect tool results
        if 'Tool result:' in decoded or '工具结果:' in decoded:
            print_colored('\\n✅ Result:', BLUE)
            in_tool_result = True
            continue

        # Detect vote summaries
        if '以下是各专家的投票结果' in decoded or 'Vote summary' in decoded.lower():
            format_vote_summary('')
            continue

        # Detect final decisions
        if '最终决策' in decoded or 'Final decision' in decoded.lower():
            print_colored('\\n🎯 Final Decision:', RED, bold=True)
            continue

        # Detect errors
        if 'Error' in decoded or 'ERROR' in decoded or '错误' in decoded:
            print_colored(decoded.strip(), RED)
            continue

        # Print other relevant lines (only if from agent response context)
        # Only print if we've seen an agent header recently (within agent response)
        if current_agent and decoded.strip() and not decoded.strip().startswith('{'):
            # Skip pure JSON lines and prompt-like content
            # Only print lines that look like agent responses (short, actionable)
            if any(keyword in decoded for keyword in [
                '做多', '做空', '观望',  # Trading decisions
                'long', 'short', 'hold',  # English trading decisions
                '信心度', 'confidence',  # Confidence
                '杠杆', 'leverage',  # Leverage
                '建议', 'recommend',  # Recommendations
                '投票', 'vote',  # Voting
                '决策', 'decision',  # Decisions
            ]):
                # Extra filter: skip if it looks like a prompt instruction
                if not any(prompt_word in decoded.lower() for prompt_word in [
                    'you are', 'your task', 'please', 'consider', 'based on'
                ]):
                    print(decoded.strip())

    except Exception as e:
        # Silently skip lines that cause errors
        pass
"
