#!/bin/bash
# View agent discussions for Trading Standalone
# 专门为 Trading Standalone 设计的 Agent 讨论查看器

docker compose logs -f trading_service 2>&1 | python3 -c "
import sys
import codecs
import re
import json

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
GRAY = '\033[90m'

# Track state
current_agent = None
in_meeting = False

def print_colored(text, color='', bold=False):
    '''Print with colors'''
    prefix = BOLD if bold else ''
    print(f'{prefix}{color}{text}{RESET}')

def should_skip_line(line):
    '''Skip lines that are definitely not agent content'''
    # Skip Docker/HTTP noise
    skip_patterns = [
        r'INFO:.*uvicorn',
        r'INFO:.*fastapi',
        r'HTTP/1\.',
        r'HTTP Request:',
        r'^\s*trading-service\s+\|\s+\{\s*$',  # Opening brace only
        r'^\s*trading-service\s+\|\s+\}\s*$',  # Closing brace only
        r'^\s*trading-service\s+\|\s+\]\s*$',  # Closing bracket only
        r'\"role\":',
        r'\"parts\":',
        r'\"history\":',
        r'\[BROADCAST\]',
        r'\[MEETING MSG\]',
        r'LLM call',
        r'Calling LLM',
        r'Sending to LLM Gateway',
    ]

    for pattern in skip_patterns:
        if re.search(pattern, line):
            return True
    return False

def extract_content(line):
    '''Extract actual content from log line'''
    # Remove container prefix
    match = re.match(r'^\s*trading-service\s+\|\s+(.+)$', line)
    if match:
        content = match.group(1).strip()
        # Remove quotes if it's a JSON string
        if content.startswith('\"') and content.endswith('\"'):
            try:
                # Unescape JSON string
                content = json.loads(content)
            except:
                pass
        return content
    return line

def is_system_message(content):
    '''Check if this is a system message'''
    return '**系统**:' in content or '**System**:' in content

def extract_agent_name(content):
    '''Extract agent name from message'''
    # Pattern: **AgentName**: content
    match = re.search(r'\*\*(\w+)\*\*:', content)
    if match:
        return match.group(1)
    return None

def is_phase_message(content):
    '''Check if this is a phase transition'''
    return '阶段' in content or 'Phase' in content or '## 阶段' in content

def format_agent_message(agent, content):
    '''Format and print agent message'''
    global current_agent

    # Print header if agent changed
    if current_agent != agent:
        current_agent = agent
        separator = '=' * 80
        print_colored(f'\n{separator}', CYAN)
        print_colored(f'🤖 {agent}', CYAN, bold=True)
        print_colored(separator, CYAN)

    # Extract actual message (remove agent name prefix)
    msg = re.sub(r'^\*\*\w+\*\*:\s*', '', content)

    # Print message
    print(msg)

def format_system_message(content):
    '''Format system/phase messages'''
    if '阶段' in content or 'Phase' in content:
        print_colored(f'\n📍 {content}', MAGENTA, bold=True)
    elif '会议议程' in content or '交易参数' in content:
        print_colored(f'\n📋 {content}', BLUE, bold=True)

# Main processing loop
for line in sys.stdin:
    try:
        # Try to decode unicode escape sequences
        try:
            decoded = line.encode('latin1').decode('unicode_escape')
        except:
            decoded = line

        # Skip noise
        if should_skip_line(decoded):
            continue

        # Extract content
        content = extract_content(decoded)
        if not content or len(content.strip()) < 5:
            continue

        # Handle system messages
        if is_system_message(content):
            if is_phase_message(content):
                format_system_message(content)
            continue

        # Handle agent messages
        agent = extract_agent_name(content)
        if agent and agent not in ['系统', 'System']:
            # Skip system role descriptions (prompts)
            if '你是' in content and '专家' in content and len(content) > 200:
                continue
            if 'You are' in content and 'expert' in content and len(content) > 200:
                continue

            # Print agent message
            format_agent_message(agent, content)

    except Exception as e:
        # Silently skip problematic lines
        pass
"
