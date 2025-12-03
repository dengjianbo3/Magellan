#!/bin/bash
# Debug version - Show what patterns are matching
# 调试版本 - 显示哪些模式被匹配到了

docker compose logs --tail=100 trading_service 2>&1 | python3 -c "
import sys
import codecs
import re

# Set stdout to UTF-8
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='ignore')

# Statistics
total_lines = 0
skipped_lines = 0
agent_lines = 0
tool_lines = 0
other_lines = 0

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

print('=== DEBUG MODE ===')
print('Analyzing last 100 log lines...\n')

for line in sys.stdin:
    total_lines += 1
    try:
        # Try to decode unicode escape sequences
        try:
            decoded = line.encode('latin1').decode('unicode_escape')
        except:
            decoded = line

        # Check if skipped
        if should_skip_line(decoded):
            skipped_lines += 1
            continue

        # Check for agent pattern
        agent_match = re.search(r'\[(\w+Agent|Leader|RiskAssessor)\]', decoded)
        if agent_match:
            agent_lines += 1
            print(f'[AGENT] {decoded.strip()[:100]}')
            continue

        # Check for tool calls
        if 'Tool Calling:' in decoded or '工具调用:' in decoded:
            tool_lines += 1
            print(f'[TOOL] {decoded.strip()[:100]}')
            continue

        # Check for tool results
        if 'Tool result:' in decoded or '工具结果:' in decoded:
            tool_lines += 1
            print(f'[RESULT] {decoded.strip()[:100]}')
            continue

        # Check for phase transitions
        if 'Phase:' in decoded or '阶段:' in decoded:
            print(f'[PHASE] {decoded.strip()[:100]}')
            continue

        # Check for keywords
        if any(keyword in decoded for keyword in [
            '做多', '做空', '观望',
            'long', 'short', 'hold',
            '信心度', 'confidence',
            '杠杆', 'leverage',
            '建议', 'recommend',
            '投票', 'vote',
            '决策', 'decision',
        ]):
            other_lines += 1
            print(f'[KEYWORD] {decoded.strip()[:100]}')
            continue

    except Exception as e:
        pass

print(f'\n=== STATISTICS ===')
print(f'Total lines: {total_lines}')
print(f'Skipped (noise): {skipped_lines}')
print(f'Agent messages: {agent_lines}')
print(f'Tool calls/results: {tool_lines}')
print(f'Keyword matches: {other_lines}')
print(f'Unmatched: {total_lines - skipped_lines - agent_lines - tool_lines - other_lines}')
"
