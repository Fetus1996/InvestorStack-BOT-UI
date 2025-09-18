#!/usr/bin/env python
import asyncio
import sys
sys.path.append('.')
from backend.engine.exchange_bitkub import BitkubExchange

async def test_orders():
    exchange = BitkubExchange()

    # Test with THB_BTC
    print("Testing THB_BTC:")
    try:
        orders = await exchange.fetch_open_orders("THB_BTC")
        print(f"Found {len(orders)} orders")
        for order in orders:
            print(f"  - {order}")
    except Exception as e:
        print(f"Error: {e}")

    # Also test raw API call
    print("\nTesting raw API call:")
    try:
        response = await exchange._request("POST", "/api/v3/market/my-open-orders",
                                          {"sym": "BTC_THB"}, signed=True)
        print(f"Raw response: {response}")
    except Exception as e:
        print(f"Error: {e}")

    await exchange.close()

asyncio.run(test_orders())