from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from ..core.config_models import APIResponse
from ..core.logging import logger

router = APIRouter(prefix="/api", tags=["keys"])


class KeysRequest(BaseModel):
    exchange: str
    # OKX
    okx_api_key: Optional[str] = None
    okx_api_secret: Optional[str] = None
    okx_passphrase: Optional[str] = None
    # Bitkub
    bitkub_api_key: Optional[str] = None
    bitkub_api_secret: Optional[str] = None
    # Network
    network: Optional[str] = "live"


def mask_key(key: str) -> str:
    """Mask API key for display."""
    if not key or len(key) < 8:
        return "****"
    return key[:4] + "****" + key[-4:]


@router.post("/keys")
async def save_keys(request: KeysRequest):
    """Save API keys to .env file."""
    try:
        env_file = ".env"
        env_lines = []

        # Read existing .env
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()

        # Prepare updates
        updates = {}

        if request.exchange == "okx":
            if request.okx_api_key:
                updates['OKX_API_KEY'] = request.okx_api_key
            if request.okx_api_secret:
                updates['OKX_API_SECRET'] = request.okx_api_secret
            if request.okx_passphrase:
                updates['OKX_PASSPHRASE'] = request.okx_passphrase
            updates['NETWORK'] = request.network or 'live'
        elif request.exchange == "bitkub":
            if request.bitkub_api_key:
                updates['BITKUB_API_KEY'] = request.bitkub_api_key
            if request.bitkub_api_secret:
                updates['BITKUB_API_SECRET'] = request.bitkub_api_secret

        updates['EXCHANGE'] = request.exchange

        # Update env lines
        updated_lines = []
        updated_keys = set()

        for line in env_lines:
            if '=' in line:
                key = line.split('=')[0].strip()
                if key in updates:
                    updated_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # Add new keys
        for key, value in updates.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}\n")

        # Write back to .env
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)

        # Set file permissions to 0600 if possible
        try:
            os.chmod(env_file, 0o600)
        except:
            pass

        # Return masked keys
        response_data = {
            "saved": True,
            "exchange": request.exchange,
            "network": request.network
        }

        if request.exchange == "okx":
            response_data.update({
                "okx_api_key": mask_key(request.okx_api_key) if request.okx_api_key else None,
                "okx_api_secret": mask_key(request.okx_api_secret) if request.okx_api_secret else None,
                "okx_passphrase": mask_key(request.okx_passphrase) if request.okx_passphrase else None,
            })
        else:
            response_data.update({
                "bitkub_api_key": mask_key(request.bitkub_api_key) if request.bitkub_api_key else None,
                "bitkub_api_secret": mask_key(request.bitkub_api_secret) if request.bitkub_api_secret else None,
            })

        return APIResponse(success=True, message="API keys saved", data=response_data)

    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.get("/keys")
async def get_keys_status():
    """Get API keys status (whether they exist)."""
    try:
        from dotenv import load_dotenv
        import importlib
        import sys

        # Force reload environment variables
        if 'os' in sys.modules:
            importlib.reload(sys.modules['os'])

        # Clear existing environment and reload
        load_dotenv(override=True)

        exchange = os.getenv("EXCHANGE", "okx")
        network = os.getenv("NETWORK", "live")

        has_keys = False
        if exchange == "okx":
            has_keys = bool(os.getenv("OKX_API_KEY") and os.getenv("OKX_API_SECRET") and os.getenv("OKX_PASSPHRASE"))
        elif exchange == "bitkub":
            has_keys = bool(os.getenv("BITKUB_API_KEY") and os.getenv("BITKUB_API_SECRET"))

        return APIResponse(
            success=True,
            data={
                "exchange": exchange,
                "network": network,
                "has_keys": has_keys
            }
        )

    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.delete("/keys")
async def delete_keys():
    """Delete API keys from .env file."""
    try:
        env_file = ".env"

        if not os.path.exists(env_file):
            return APIResponse(success=False, message="No configuration file found")

        # Read existing .env
        with open(env_file, 'r') as f:
            env_lines = f.readlines()

        # Keys to remove
        keys_to_remove = [
            'EXCHANGE',
            'OKX_API_KEY', 'OKX_API_SECRET', 'OKX_PASSPHRASE',
            'BITKUB_API_KEY', 'BITKUB_API_SECRET',
            'NETWORK'
        ]

        # Filter out the API key lines
        updated_lines = []
        for line in env_lines:
            if '=' in line:
                key = line.split('=')[0].strip()
                if key not in keys_to_remove:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # Write back to .env
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)

        # Clear from current process environment
        for key in keys_to_remove:
            if key in os.environ:
                del os.environ[key]

        return APIResponse(
            success=True,
            message="API keys deleted successfully",
            data={"deleted": True}
        )

    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.post("/keys/test")
async def test_api_connection():
    """Test API connection with current credentials."""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        exchange = os.getenv("EXCHANGE", "okx")

        # Test based on exchange
        if exchange == "okx":
            from ..engine.exchange_okx_ccxt import OKXExchange

            try:
                exchange_client = OKXExchange()
                # Try to fetch balance as connection test
                balance = await exchange_client.fetch_balance()

                # Filter out zero balances for cleaner display
                non_zero_balance = {}
                total_value_thb = 0.0

                if balance and 'total' in balance:
                    for currency, amount in balance['total'].items():
                        if amount > 0:
                            non_zero_balance[currency] = {
                                'total': amount,
                                'free': balance['free'].get(currency, 0),
                                'used': balance['used'].get(currency, 0)
                            }

                            # Calculate THB value for each currency (OKX uses USDT as base)
                            if currency == 'USDT':
                                # Convert USDT to THB (approximate rate: 1 USDT = ~36 THB)
                                try:
                                    ticker = await exchange_client.fetch_ticker('USDT/THB')
                                    usdt_price = ticker['last']  # USDT price in THB
                                    total_value_thb += amount * usdt_price
                                except Exception:
                                    # Fallback approximation if ticker fails
                                    total_value_thb += amount * 36.0
                            elif currency == 'BTC':
                                try:
                                    # Get BTC/USDT price and convert to THB
                                    ticker_btc = await exchange_client.fetch_ticker('BTC/USDT')
                                    btc_usdt_price = ticker_btc['last']
                                    ticker_usdt = await exchange_client.fetch_ticker('USDT/THB')
                                    usdt_thb_price = ticker_usdt['last']
                                    btc_thb_price = btc_usdt_price * usdt_thb_price
                                    total_value_thb += amount * btc_thb_price
                                except Exception:
                                    # Fallback approximation
                                    total_value_thb += amount * 2500000.0  # Rough BTC/THB estimate

                await exchange_client.close()

                return APIResponse(
                    success=True,
                    message="Successfully connected to OKX API",
                    data={
                        "exchange": "okx",
                        "status": "connected",
                        "network": os.getenv("NETWORK", "live"),
                        "balance": non_zero_balance,
                        "total_value_thb": total_value_thb
                    }
                )
            except Exception as e:
                error_msg = str(e)
                if "apiKey" in error_msg or "API" in error_msg:
                    return APIResponse(
                        success=False,
                        message="Invalid API credentials",
                        error="Please check your API Key, Secret, and Passphrase"
                    )
                else:
                    return APIResponse(
                        success=False,
                        message="Connection failed",
                        error=error_msg
                    )

        elif exchange == "bitkub":
            from ..engine.exchange_bitkub import BitkubExchange

            try:
                exchange_client = BitkubExchange()
                # Try to fetch balance as connection test
                balance = await exchange_client.fetch_balance()

                # Filter out zero balances for cleaner display
                non_zero_balance = {}
                total_value_thb = 0.0

                if balance and 'total' in balance:
                    for currency, amount in balance['total'].items():
                        if amount > 0:
                            non_zero_balance[currency] = {
                                'total': amount,
                                'free': balance['free'].get(currency, 0),
                                'used': balance['used'].get(currency, 0)
                            }

                            # Calculate THB value for each currency
                            if currency == 'THB':
                                total_value_thb += amount
                            elif currency == 'BTC':
                                try:
                                    # Fetch BTC/THB price
                                    ticker = await exchange_client.fetch_ticker('THB_BTC')
                                    btc_price = ticker['last']  # Current BTC price in THB
                                    total_value_thb += amount * btc_price
                                except Exception as e:
                                    logger.warning(f"Failed to get BTC price for portfolio calculation: {e}")
                            elif currency == 'DOGE':
                                try:
                                    # Fetch DOGE/THB price
                                    ticker = await exchange_client.fetch_ticker('THB_DOGE')
                                    doge_price = ticker['last']  # Current DOGE price in THB
                                    total_value_thb += amount * doge_price
                                except Exception as e:
                                    logger.warning(f"Failed to get DOGE price for portfolio calculation: {e}")
                            # Add other currencies as needed

                await exchange_client.close()

                return APIResponse(
                    success=True,
                    message="Successfully connected to Bitkub API",
                    data={
                        "exchange": "bitkub",
                        "status": "connected",
                        "balance": non_zero_balance,
                        "total_value_thb": total_value_thb
                    }
                )
            except Exception as e:
                error_msg = str(e)
                if "API" in error_msg or "Invalid" in error_msg:
                    return APIResponse(
                        success=False,
                        message="Invalid API credentials",
                        error="Please check your API Key and Secret"
                    )
                else:
                    return APIResponse(
                        success=False,
                        message="Connection failed",
                        error=error_msg
                    )
        else:
            return APIResponse(
                success=False,
                message="Unknown exchange",
                error=f"Exchange {exchange} not supported"
            )

    except Exception as e:
        return APIResponse(
            success=False,
            message="Failed to test connection",
            error=str(e)
        )