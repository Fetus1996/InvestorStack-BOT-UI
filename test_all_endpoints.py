#!/usr/bin/env python
import asyncio
import sys
sys.path.append('.')
from backend.engine.exchange_bitkub import BitkubExchange

async def test_all_endpoints():
    exchange = BitkubExchange()

    print("=" * 50)
    print("Testing Bitkub API Endpoints")
    print("=" * 50)

    # Test different endpoints
    endpoints_to_test = [
        ("/api/v3/market/my-open-orders", {"sym": "BTC_THB"}),
        ("/api/v3/market/my-open-orders", {"sym": "THB_BTC"}),
        ("/api/v3/market/my-open-orders", {"sym": "BTC"}),
        ("/api/v3/market/my-open-orders", {}),  # No symbol
        ("/api/market/my-open-orders", {"sym": "BTC_THB"}),  # v1 endpoint
        ("/api/v3/market/my-order-history", {"sym": "BTC_THB", "lmt": 10}),
    ]

    for endpoint, params in endpoints_to_test:
        print(f"\n🔍 Testing: {endpoint}")
        print(f"   Params: {params}")
        try:
            response = await exchange._request("POST", endpoint, params, signed=True)
            print(f"   ✅ Response: {response}")
            if isinstance(response, dict) and 'result' in response:
                result = response['result']
                if result:
                    print(f"   📊 Found data: {len(result) if isinstance(result, list) else 'dict'} items")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Also test wallet to make sure API works
    print("\n🔍 Testing Wallet API:")
    try:
        balance = await exchange.fetch_balance()
        print(f"   ✅ Balance: {balance['total']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    await exchange.close()

asyncio.run(test_all_endpoints())