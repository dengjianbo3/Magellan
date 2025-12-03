# Log Viewer Guide - Chinese Character Support

**Created**: 2025-12-03
**Purpose**: View Docker logs with properly decoded Chinese characters

---

## Problem

When viewing Docker logs with:
```bash
docker-compose logs -f trading-service
```

You see Unicode escape sequences instead of Chinese characters:
```
\u89e3\u8bfb**: \u5f53\u524d\u5e02\u573a\u60c5\u7eea\u5904\u4e8e\u6050\u614c\u72b6\u6001
```

---

## Solution

Use the provided `view-logs.sh` script that automatically decodes Unicode:

### Usage

```bash
# Navigate to trading-standalone directory
cd /Users/dengjianbo/Documents/Magellan/trading-standalone

# Run the log viewer
./view-logs.sh
```

**Expected Output**: Chinese characters properly displayed:
```
解读**: 当前市场情绪处于恐慌状态
```

---

## How It Works

The script pipes Docker logs through Python to decode Unicode escape sequences:

```bash
docker-compose logs -f trading-service 2>&1 | python3 -c "
import sys, codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='ignore')
for line in sys.stdin:
    try:
        decoded = line.encode('latin1').decode('unicode_escape')
        print(decoded, end='')
    except:
        print(line, end='')
"
```

---

## Alternative Methods

### Method 1: Direct Command (One-time)
```bash
docker-compose logs -f trading-service 2>&1 | python3 -c "
import sys, codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='ignore')
for line in sys.stdin:
    try:
        print(line.encode('latin1').decode('unicode_escape'), end='')
    except:
        print(line, end='')
"
```

### Method 2: View Last N Lines
```bash
# View last 100 lines with Chinese characters
docker-compose logs --tail=100 trading-service 2>&1 | python3 -c "
import sys, codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='ignore')
for line in sys.stdin:
    try:
        print(line.encode('latin1').decode('unicode_escape'), end='')
    except:
        print(line, end='')
"
```

### Method 3: Search for Specific Terms
```bash
# Search for "决策" (decision) with proper Chinese display
docker-compose logs trading-service 2>&1 | grep "决策" | python3 -c "
import sys, codecs
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='ignore')
for line in sys.stdin:
    try:
        print(line.encode('latin1').decode('unicode_escape'), end='')
    except:
        print(line, end='')
"
```

---

## Troubleshooting

### Issue: Permission Denied
```bash
chmod +x view-logs.sh
```

### Issue: Script Not Found
```bash
# Check you're in the correct directory
pwd  # Should show: /Users/dengjianbo/Documents/Magellan/trading-standalone

# Check file exists
ls -lah view-logs.sh
```

### Issue: Python3 Not Found
```bash
# Install Python 3 (macOS)
brew install python3

# Or use system Python
which python3
```

### Issue: Still Seeing Escape Sequences
Some terminals may not support UTF-8 properly. Try:
```bash
# Set terminal to UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# Then run the script
./view-logs.sh
```

---

## For Remote Server (45.76.159.149)

Copy the script to the remote server:

```bash
# Copy script
scp view-logs.sh root@45.76.159.149:/root/trading-standalone/

# SSH to server
ssh root@45.76.159.149

# Navigate and run
cd /root/trading-standalone
chmod +x view-logs.sh
./view-logs.sh
```

---

## Exit

Press `Ctrl+C` to stop following logs.

---

**Guide Created**: 2025-12-03
**Script**: view-logs.sh
**Location**: /Users/dengjianbo/Documents/Magellan/trading-standalone/
