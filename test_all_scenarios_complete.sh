#!/bin/bash

# =============================================================================
# Magellan Analysis Module - 完整的端到端测试套件
# 测试所有5个投资场景 x 3种深度模式 = 15个测试用例
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# API地址
API_BASE="http://localhost:8001"
ANALYSIS_ENDPOINT="${API_BASE}/analysis/start"

# 测试结果存储
declare -a FAILED_TEST_NAMES

# =============================================================================
# 辅助函数
# =============================================================================

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}[TEST $TOTAL_TESTS] $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 测试单个场景
test_scenario() {
    local scenario=$1
    local depth=$2
    local payload=$3
    local test_name="${scenario} - ${depth}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    print_test "$test_name"

    # 发送请求
    response=$(curl -s -w "\n%{http_code}" -X POST "$ANALYSIS_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$payload")

    # 分离响应体和状态码
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    # 检查HTTP状态码
    if [ "$http_code" != "200" ] && [ "$http_code" != "201" ] && [ "$http_code" != "202" ]; then
        print_error "HTTP $http_code - 请求失败"
        print_info "Response: $body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$test_name (HTTP $http_code)")
        return 1
    fi

    # 检查响应JSON格式
    if ! echo "$body" | jq empty 2>/dev/null; then
        print_error "响应不是有效的JSON"
        print_info "Response: $body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$test_name (Invalid JSON)")
        return 1
    fi

    # 提取关键字段
    session_id=$(echo "$body" | jq -r '.session_id // .data.session_id // empty')
    status=$(echo "$body" | jq -r '.status // .data.status // empty')
    message=$(echo "$body" | jq -r '.message // .data.message // empty')

    # 验证响应内容
    if [ -z "$session_id" ]; then
        print_error "缺少session_id"
        print_info "Response: $body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$test_name (Missing session_id)")
        return 1
    fi

    # 成功
    PASSED_TESTS=$((PASSED_TESTS + 1))
    print_success "测试通过 (session: ${session_id:0:8}...)"
    print_info "Status: $status, Message: $message"

    # 短暂延迟,避免过载
    sleep 1

    return 0
}

# =============================================================================
# 测试用例定义
# =============================================================================

# -----------------------------------------------------------------------------
# 1. 早期投资场景 (Early Stage Investment)
# -----------------------------------------------------------------------------
test_early_stage() {
    print_header "场景1: 早期投资 (Early Stage Investment)"

    # Quick Mode
    test_scenario "Early Stage" "Quick" '{
        "target": {
            "company_name": "AI教育科技公司",
            "stage": "seed",
            "industry": "EdTech",
            "team_members": [
                {"name": "张三", "role": "CEO", "background": "前阿里技术总监"}
            ]
        },
        "config": {
            "depth": "quick",
            "focus_areas": ["team", "market"]
        }
    }'

    # Standard Mode
    test_scenario "Early Stage" "Standard" '{
        "target": {
            "company_name": "智能医疗设备公司",
            "stage": "series-a",
            "industry": "HealthTech",
            "team_members": [
                {"name": "李四", "role": "CTO", "background": "斯坦福PhD"}
            ]
        },
        "config": {
            "depth": "standard",
            "focus_areas": ["team", "market", "product"]
        }
    }'

    # Comprehensive Mode
    test_scenario "Early Stage" "Comprehensive" '{
        "target": {
            "company_name": "企业SaaS平台",
            "stage": "series-a",
            "industry": "Enterprise Software",
            "team_members": [
                {"name": "王五", "role": "CEO", "background": "连续创业者"}
            ]
        },
        "config": {
            "depth": "comprehensive",
            "focus_areas": ["team", "market", "product", "financials"]
        }
    }'
}

# -----------------------------------------------------------------------------
# 2. 成长期投资场景 (Growth Investment)
# -----------------------------------------------------------------------------
test_growth_investment() {
    print_header "场景2: 成长期投资 (Growth Investment)"

    # Quick Mode
    test_scenario "Growth" "Quick" '{
        "target": {
            "company_name": "云计算独角兽",
            "stage": "series-c",
            "annual_revenue": 50000000,
            "growth_rate": 150
        },
        "config": {
            "depth": "quick",
            "focus_areas": ["financials", "growth"]
        }
    }'

    # Standard Mode
    test_scenario "Growth" "Standard" '{
        "target": {
            "company_name": "电商平台",
            "stage": "series-d",
            "annual_revenue": 200000000,
            "growth_rate": 80
        },
        "config": {
            "depth": "standard",
            "focus_areas": ["financials", "growth", "market"]
        }
    }'

    # Comprehensive Mode
    test_scenario "Growth" "Comprehensive" '{
        "target": {
            "company_name": "金融科技公司",
            "stage": "pre-ipo",
            "annual_revenue": 500000000,
            "growth_rate": 60
        },
        "config": {
            "depth": "comprehensive",
            "focus_areas": ["financials", "growth", "market", "operations"]
        }
    }'
}

# -----------------------------------------------------------------------------
# 3. 公开市场投资场景 (Public Market Investment)
# -----------------------------------------------------------------------------
test_public_market() {
    print_header "场景3: 公开市场投资 (Public Market Investment)"

    # Quick Mode
    test_scenario "Public Market" "Quick" '{
        "target": {
            "ticker": "AAPL",
            "exchange": "NASDAQ",
            "asset_type": "stock"
        },
        "config": {
            "depth": "quick",
            "focus_areas": ["valuation", "fundamentals"]
        }
    }'

    # Standard Mode
    test_scenario "Public Market" "Standard" '{
        "target": {
            "ticker": "TSLA",
            "exchange": "NASDAQ",
            "asset_type": "stock"
        },
        "config": {
            "depth": "standard",
            "focus_areas": ["valuation", "fundamentals", "technical"]
        }
    }'

    # Comprehensive Mode
    test_scenario "Public Market" "Comprehensive" '{
        "target": {
            "ticker": "NVDA",
            "exchange": "NASDAQ",
            "asset_type": "stock"
        },
        "config": {
            "depth": "comprehensive",
            "focus_areas": ["valuation", "fundamentals", "technical", "market_sentiment"]
        }
    }'
}

# -----------------------------------------------------------------------------
# 4. 另类投资场景 (Alternative Investment)
# -----------------------------------------------------------------------------
test_alternative_investment() {
    print_header "场景4: 另类投资 (Alternative Investment)"

    # Quick Mode
    test_scenario "Alternative" "Quick" '{
        "target": {
            "asset_type": "crypto",
            "symbol": "ETH",
            "project_name": "Ethereum"
        },
        "config": {
            "depth": "quick",
            "focus_areas": ["tech", "tokenomics"]
        }
    }'

    # Standard Mode
    test_scenario "Alternative" "Standard" '{
        "target": {
            "asset_type": "defi",
            "symbol": "UNI",
            "project_name": "Uniswap",
            "chain": "ethereum"
        },
        "config": {
            "depth": "standard",
            "focus_areas": ["tech", "tokenomics", "community"]
        }
    }'

    # Comprehensive Mode
    test_scenario "Alternative" "Comprehensive" '{
        "target": {
            "asset_type": "web3",
            "symbol": "MATIC",
            "project_name": "Polygon",
            "chain": "ethereum"
        },
        "config": {
            "depth": "comprehensive",
            "focus_areas": ["tech", "tokenomics", "community", "onchain"]
        }
    }'
}

# -----------------------------------------------------------------------------
# 5. 行业研究场景 (Industry Research)
# -----------------------------------------------------------------------------
test_industry_research() {
    print_header "场景5: 行业研究 (Industry Research)"

    # Quick Mode
    test_scenario "Industry Research" "Quick" '{
        "target": {
            "industry_name": "人工智能",
            "research_topic": "生成式AI市场规模",
            "geo_scope": "global"
        },
        "config": {
            "depth": "quick",
            "focus_areas": ["market_size", "trends"]
        }
    }'

    # Standard Mode
    test_scenario "Industry Research" "Standard" '{
        "target": {
            "industry_name": "新能源汽车",
            "research_topic": "电池技术趋势",
            "geo_scope": "china"
        },
        "config": {
            "depth": "standard",
            "focus_areas": ["market_size", "trends", "competition"]
        }
    }'

    # Comprehensive Mode
    test_scenario "Industry Research" "Comprehensive" '{
        "target": {
            "industry_name": "生物医药",
            "research_topic": "mRNA疫苗市场",
            "geo_scope": "global"
        },
        "config": {
            "depth": "comprehensive",
            "focus_areas": ["market_size", "trends", "competition", "opportunities"]
        }
    }'
}

# =============================================================================
# 主测试流程
# =============================================================================

main() {
    print_header "Magellan Analysis Module - 完整端到端测试"

    print_info "API地址: $API_BASE"
    print_info "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 检查API是否可用
    print_info "检查API健康状态..."
    if ! curl -s "$API_BASE/health" > /dev/null 2>&1; then
        print_error "API不可访问,请确保服务已启动"
        print_info "提示: docker-compose up -d"
        exit 1
    fi
    print_success "API健康检查通过"
    echo ""

    # 执行所有测试
    test_early_stage
    test_growth_investment
    test_public_market
    test_alternative_investment
    test_industry_research

    # 输出测试总结
    print_header "测试总结"

    echo -e "总测试数:   ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "通过:       ${GREEN}$PASSED_TESTS${NC}"
    echo -e "失败:       ${RED}$FAILED_TESTS${NC}"

    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "\n${RED}失败的测试:${NC}"
        for test in "${FAILED_TEST_NAMES[@]}"; do
            echo -e "  ${RED}✗ $test${NC}"
        done
    fi

    echo -e "\n结束时间: $(date '+%Y-%m-%d %H:%M:%S')"

    # 返回适当的退出码
    if [ $FAILED_TESTS -eq 0 ]; then
        print_success "所有测试通过! 🎉"
        exit 0
    else
        print_error "有 $FAILED_TESTS 个测试失败"
        exit 1
    fi
}

# 执行主函数
main
