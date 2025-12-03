#!/bin/bash
# View Docker logs with proper Chinese character encoding

docker compose logs -f trading_service 2>&1 | python3 -c "
import sys
import codecs

# Set stdout to UTF-8
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='ignore')

for line in sys.stdin:
    try:
        # Try to decode unicode escape sequences
        decoded = line.encode('latin1').decode('unicode_escape')
        print(decoded, end='')
    except:
        # If decoding fails, print as-is
        print(line, end='')
"
