#!/usr/bin/env python3
"""
OKX 模拟盘交易测试脚本
测试开仓功能，诊断 "All operations failed" 错误
"""

import asyncio
import aiohttp
import hmac
import hashlib
import base64
import json
from datetime import datetime, timezone

# OKX API 凭证
API_KEY = "3bb25505-53d5-4f11-8d18-8a77aeccfffd"
SECRET_KEY = "6AB2457533613EFC7D1474F11568758D"
PASSPHRASE = "4Y9nu9fr9981752@"
DEMO_MODE = True

BASE_URL = "https://www.okx.com"


def get_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def sign(timestamp, method, path, body=''):
    message = timestamp + method + path + body
    mac = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def get_headers(method, path, body=''):
    timestamp = get_timestamp()
    signature = sign(timestamp, method, path, body)
    headers = {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }
    if DEMO_MODE:
        headers['x-simulated-trading'] = '1'
    return headers


async def test_account_balance():
    """测试获取账户余额"""
    print("\n" + "="*60)
    print("📊 测试1: 获取账户余额")
    print("="*60)

    path = '/api/v5/account/balance'
    headers = get_headers('GET', path)

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL + path, headers=headers) as resp:
            data = await resp.json()
            print(f"响应码: {data.get('code')}")
            print(f"消息: {data.get('msg')}")

            if data.get('code') == '0':
                account = data.get('data', [{}])[0]
                print(f"总权益: ${float(account.get('totalEq', 0)):,.2f}")
                for detail in account.get('details', []):
                    if detail.get('ccy') == 'USDT':
                        print(f"USDT 可用: ${float(detail.get('availBal', 0)):,.2f}")
                        print(f"USDT 冻结: ${float(detail.get('frozenBal', 0)):,.2f}")
                return True
            else:
                print(f"❌ 获取余额失败: {data.get('msg')}")
                return False


async def test_market_price():
    """测试获取市场价格"""
    print("\n" + "="*60)
    print("📈 测试2: 获取市场价格 (公开API)")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/api/v5/market/ticker?instId=BTC-USDT-SWAP"
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get('code') == '0' and data.get('data'):
                ticker = data['data'][0]
                price = float(ticker.get('last', 0))
                print(f"BTC-USDT-SWAP 价格: ${price:,.2f}")
                return price
            else:
                print(f"❌ 获取价格失败: {data.get('msg')}")
                return None


async def test_account_config():
    """测试获取账户配置（持仓模式）"""
    print("\n" + "="*60)
    print("⚙️ 测试3a: 获取账户配置")
    print("="*60)

    path = '/api/v5/account/config'
    headers = get_headers('GET', path)

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL + path, headers=headers) as resp:
            data = await resp.json()
            print(f"响应码: {data.get('code')}")

            if data.get('code') == '0' and data.get('data'):
                config = data['data'][0]
                pos_mode = config.get('posMode')
                print(f"持仓模式: {pos_mode}")
                print(f"  - net_mode = 单向持仓（不区分多空）")
                print(f"  - long_short_mode = 双向持仓（区分多空）")

                if pos_mode == 'net_mode':
                    print("\n⚠️ 当前是单向持仓模式！")
                    print("   代码使用了 posSide='long'，需要切换到双向持仓模式")
                    return 'net_mode'
                else:
                    print("✅ 双向持仓模式")
                    return 'long_short_mode'
            else:
                print(f"❌ 获取配置失败: {data.get('msg')}")
                return None


async def test_set_pos_mode():
    """设置为双向持仓模式"""
    print("\n" + "="*60)
    print("⚙️ 测试3b: 设置双向持仓模式")
    print("="*60)

    path = '/api/v5/account/set-position-mode'
    body = json.dumps({'posMode': 'long_short_mode'})
    headers = get_headers('POST', path, body)

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL + path, headers=headers, data=body) as resp:
            data = await resp.json()
            print(f"响应码: {data.get('code')}")
            print(f"消息: {data.get('msg')}")

            if data.get('code') == '0':
                print("✅ 设置双向持仓模式成功")
                return True
            else:
                print(f"❌ 设置失败: {data.get('msg')}")
                # 51020 表示已经是该模式
                if '51020' in str(data):
                    print("   (已经是双向持仓模式)")
                    return True
                return False


async def test_set_leverage():
    """测试设置杠杆"""
    print("\n" + "="*60)
    print("⚙️ 测试3c: 设置杠杆 (10x)")
    print("="*60)

    path = '/api/v5/account/set-leverage'
    body = json.dumps({
        'instId': 'BTC-USDT-SWAP',
        'lever': '10',
        'mgnMode': 'cross'
    })
    headers = get_headers('POST', path, body)

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL + path, headers=headers, data=body) as resp:
            data = await resp.json()
            print(f"响应码: {data.get('code')}")
            print(f"消息: {data.get('msg')}")
            print(f"完整响应: {json.dumps(data, indent=2)}")

            if data.get('code') == '0':
                print("✅ 设置杠杆成功")
                return True
            else:
                print(f"❌ 设置杠杆失败: {data.get('msg')}")
                return False


async def test_place_order(price):
    """测试下单"""
    print("\n" + "="*60)
    print("🛒 测试4: 下单 (市价开多)")
    print("="*60)

    # BTC-USDT-SWAP: 1 contract = 0.01 BTC
    # 用 $100 @ 10x 杠杆 = $1000 名义价值
    # 需要 $1000 / $92500 / 0.01 ≈ 1 contract
    amount_usdt = 100
    leverage = 10
    contract_val = 0.01
    sz = int((amount_usdt * leverage) / (price * contract_val))
    sz = max(1, sz)

    print(f"下单参数:")
    print(f"  - 保证金: ${amount_usdt}")
    print(f"  - 杠杆: {leverage}x")
    print(f"  - 当前价格: ${price:,.2f}")
    print(f"  - 合约数量: {sz}")

    path = '/api/v5/trade/order'
    order_data = {
        'instId': 'BTC-USDT-SWAP',
        'tdMode': 'cross',
        'side': 'buy',
        'posSide': 'long',
        'ordType': 'market',
        'sz': str(sz)
    }
    body = json.dumps(order_data)
    headers = get_headers('POST', path, body)

    print(f"\n请求体: {body}")

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL + path, headers=headers, data=body) as resp:
            data = await resp.json()
            print(f"\n响应码: {data.get('code')}")
            print(f"消息: {data.get('msg')}")
            print(f"完整响应: {json.dumps(data, indent=2)}")

            if data.get('code') == '0':
                order_id = data.get('data', [{}])[0].get('ordId', '')
                print(f"✅ 下单成功! 订单ID: {order_id}")
                return order_id
            else:
                print(f"❌ 下单失败: {data.get('msg')}")
                # 详细错误码解析
                if data.get('data'):
                    for item in data.get('data', []):
                        print(f"  - sCode: {item.get('sCode')}")
                        print(f"  - sMsg: {item.get('sMsg')}")
                return None


async def test_get_position():
    """测试获取持仓"""
    print("\n" + "="*60)
    print("📋 测试5: 获取当前持仓")
    print("="*60)

    path = '/api/v5/account/positions?instId=BTC-USDT-SWAP'
    headers = get_headers('GET', path)

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL + path, headers=headers) as resp:
            data = await resp.json()
            print(f"响应码: {data.get('code')}")

            if data.get('code') == '0':
                positions = data.get('data', [])
                if positions:
                    for pos in positions:
                        pos_amt = float(pos.get('pos', 0) or 0)
                        if abs(pos_amt) > 0:
                            print(f"✅ 有持仓!")
                            print(f"  - 方向: {'多' if pos_amt > 0 else '空'}")
                            print(f"  - 数量: {abs(pos_amt)}")
                            print(f"  - 入场价: ${float(pos.get('avgPx', 0)):,.2f}")
                            print(f"  - 杠杆: {pos.get('lever')}x")
                            print(f"  - 未实现盈亏: ${float(pos.get('upl', 0)):,.2f}")
                            return True
                print("无持仓")
                return False
            else:
                print(f"❌ 获取持仓失败: {data.get('msg')}")
                return False


async def test_close_position():
    """测试平仓"""
    print("\n" + "="*60)
    print("🔄 测试6: 平仓")
    print("="*60)

    path = '/api/v5/trade/close-position'
    body = json.dumps({
        'instId': 'BTC-USDT-SWAP',
        'mgnMode': 'cross',
        'posSide': 'long'
    })
    headers = get_headers('POST', path, body)

    async with aiohttp.ClientSession() as session:
        async with session.post(BASE_URL + path, headers=headers, data=body) as resp:
            data = await resp.json()
            print(f"响应码: {data.get('code')}")
            print(f"消息: {data.get('msg')}")

            if data.get('code') == '0':
                print("✅ 平仓成功")
                return True
            else:
                print(f"❌ 平仓失败: {data.get('msg')}")
                return False


async def main():
    print("="*60)
    print("🔍 OKX 模拟盘交易诊断测试")
    print("="*60)
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"Demo Mode: {DEMO_MODE}")
    print(f"Base URL: {BASE_URL}")

    # 测试1: 账户余额
    balance_ok = await test_account_balance()
    if not balance_ok:
        print("\n⚠️ 账户余额获取失败，停止测试")
        return

    # 测试2: 市场价格
    price = await test_market_price()
    if not price:
        print("\n⚠️ 价格获取失败，停止测试")
        return

    # 测试3a: 检查账户配置
    pos_mode = await test_account_config()

    # 测试3b: 如果是单向模式，切换到双向模式
    if pos_mode == 'net_mode':
        await test_set_pos_mode()
        await asyncio.sleep(1)
        await test_account_config()  # 再次确认

    # 测试3c: 设置杠杆
    leverage_ok = await test_set_leverage()

    # 测试4: 下单
    order_id = await test_place_order(price)

    # 等待一下让订单成交
    if order_id:
        print("\n等待2秒让订单成交...")
        await asyncio.sleep(2)

    # 测试5: 获取持仓
    has_position = await test_get_position()

    # 测试6: 平仓 (如果有持仓)
    if has_position:
        await test_close_position()
        await asyncio.sleep(1)
        await test_get_position()

    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
