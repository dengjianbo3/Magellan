#!/usr/bin/env python3
"""
Test ReWOO Agent with Real LLM
测试ReWOO Agent是否能正常工作
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services/report_orchestrator'))

from app.core.roundtable.investment_agents import create_financial_expert
from app.core.roundtable.mcp_tools import create_mcp_tools_for_agent


async def test_rewoo_financial_expert():
    """测试Financial Expert的ReWOO分析"""
    print("="*80)
    print("Testing ReWOO Financial Expert")
    print("="*80)

    # 创建Financial Expert (ReWOO架构)
    agent = create_financial_expert(language="zh")

    # 添加工具
    tools = create_mcp_tools_for_agent("FinancialExpert")
    for tool in tools:
        agent.register_tool(tool)

    print(f"\n✅ Created agent: {agent.name}")
    print(f"✅ Registered {len(agent.tools)} tools: {list(agent.tools.keys())}")

    # 测试场景1: 分析Tesla (在硬编码列表中)
    print("\n" + "="*80)
    print("Test Case 1: Analyze Tesla (TSLA)")
    print("="*80)

    query = "请分析Tesla (TSLA)的财务健康度"
    context = {
        "company": "Tesla",
        "ticker": "TSLA",
        "analysis_type": "financial_health"
    }

    try:
        print(f"\n📝 Query: {query}")
        print(f"📝 Context: {context}")
        print(f"\n⏳ Running ReWOO analysis (this may take 1-2 minutes)...\n")

        result = await agent.analyze_with_rewoo(query, context)

        print("\n✅ Analysis Complete!")
        print("="*80)
        print("RESULT:")
        print("="*80)
        print(result[:1000])  # Print first 1000 chars
        if len(result) > 1000:
            print(f"\n... (truncated, total length: {len(result)} chars)")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_json_parsing():
    """测试JSON解析功能"""
    print("\n" + "="*80)
    print("Test Case 2: JSON Parsing")
    print("="*80)

    agent = create_financial_expert(language="zh")

    # 测试不同的JSON格式
    test_cases = [
        # Case 1: 纯JSON
        '[{"step": 1, "tool": "test", "params": {}, "purpose": "test"}]',

        # Case 2: 带markdown代码块
        '''```json
[{"step": 1, "tool": "test", "params": {}, "purpose": "test"}]
```''',

        # Case 3: 带额外文字
        '''Here is the plan:
```json
[{"step": 1, "tool": "test", "params": {}, "purpose": "test"}]
```
This plan will help us analyze...''',

        # Case 4: 空数组
        '[]',

        # Case 5: 格式错误
        'This is not JSON at all',
    ]

    for i, test_input in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_input[:50]}...")
        try:
            result = agent._parse_plan(test_input)
            print(f"✅ Parsed successfully: {result}")
        except Exception as e:
            print(f"❌ Parse failed: {e}")

    print("\n" + "="*80)


async def main():
    """主测试函数"""
    print("\n🚀 Starting ReWOO Agent Tests\n")

    # Test 1: JSON Parsing
    await test_json_parsing()

    # Test 2: Full ReWOO Analysis (only if LLM gateway is available)
    print("\n" + "="*80)
    print("Checking if LLM Gateway is available...")
    print("="*80)

    # 检查环境变量
    llm_gateway_url = os.getenv("LLM_GATEWAY_URL", "http://llm_gateway:8003")
    print(f"LLM Gateway URL: {llm_gateway_url}")

    # 尝试测试LLM连接
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{llm_gateway_url}/health")
            print(f"✅ LLM Gateway is reachable: {response.status_code}")

            # 运行完整测试
            success = await test_rewoo_financial_expert()

            if success:
                print("\n" + "="*80)
                print("🎉 ALL TESTS PASSED!")
                print("="*80)
            else:
                print("\n" + "="*80)
                print("⚠️  Some tests failed")
                print("="*80)

    except Exception as e:
        print(f"⚠️  Cannot reach LLM Gateway: {e}")
        print("Skipping full ReWOO test. Please ensure services are running:")
        print("  docker-compose up -d")


if __name__ == "__main__":
    asyncio.run(main())
