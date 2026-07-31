import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from forecast_ai.config import HolderTierConfig
from forecast_ai.services.balance_checker import BalanceChecker, _BALANCE_CACHE, _TOKEN_DECIMALS_CACHE

@pytest.fixture
def balance_checker():
    cfg = HolderTierConfig(
        token_contract_address="0xcc9c1ec224c3824ae5ea699ec72ef5fad4165e49",
        rpc_url="https://rpc.mainnet.chain.robinhood.com",
        holder_threshold=200000.0,
        pro_holder_threshold=1000000.0
    )
    checker = BalanceChecker(cfg)
    checker.clear_cache()
    return checker

@pytest.mark.asyncio
async def test_fetch_token_decimals_caching(balance_checker):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Hex for 18 (0x12)
        mock_resp.json.return_value = {"result": "0x12"}
        mock_post.return_value = mock_resp

        decimals = await balance_checker.fetch_token_decimals("0xcc9c1ec224c3824ae5ea699ec72ef5fad4165e49")
        assert decimals == 18

        # Verify second call reads from process cache without additional RPC call
        decimals_cached = await balance_checker.fetch_token_decimals("0xcc9c1ec224c3824ae5ea699ec72ef5fad4165e49")
        assert decimals_cached == 18
        assert mock_post.call_count == 1

@pytest.mark.asyncio
async def test_zero_balance_wallet_tier(balance_checker):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": "0x0"}
        mock_post.return_value = mock_resp

        addr = "0x0000000000000000000000000000000000000001"
        balance = await balance_checker.fetch_onchain_balance(addr)
        assert balance == 0.0
        
        tier = balance_checker.evaluate_holder_tier(balance)
        assert tier == "Free"

@pytest.mark.asyncio
async def test_holder_tier_balance(balance_checker):
    # 250,000 $FORAI in wei = 250,000 * 10^18 = 0x3635c9adc5dea00000
    hex_250k = hex(250000 * (10**18))
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": hex_250k}
        mock_post.return_value = mock_resp

        addr = "0x1111111111111111111111111111111111111111"
        balance = await balance_checker.fetch_onchain_balance(addr)
        assert balance == 250000.0

        tier = balance_checker.evaluate_holder_tier(balance)
        assert tier == "Holder"

@pytest.mark.asyncio
async def test_pro_holder_tier_balance(balance_checker):
    # 1,500,000 $FORAI in wei = 1,500,000 * 10^18
    hex_1_5m = hex(1500000 * (10**18))

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": hex_1_5m}
        mock_post.return_value = mock_resp

        addr = "0x2222222222222222222222222222222222222222"
        balance = await balance_checker.fetch_onchain_balance(addr)
        assert balance == 1500000.0

        tier = balance_checker.evaluate_holder_tier(balance)
        assert tier == "Pro Holder"

@pytest.mark.asyncio
async def test_multi_wallet_aggregation(balance_checker):
    # Wallet 1: 150k, Wallet 2: 100k -> Total: 250k (Holder tier)
    hex_150k = hex(150000 * (10**18))
    hex_100k = hex(100000 * (10**18))

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        r1 = MagicMock()
        r1.status_code = 200
        r1.json.return_value = {"result": hex_150k}

        r2 = MagicMock()
        r2.status_code = 200
        r2.json.return_value = {"result": hex_100k}

        mock_post.side_effect = [r1, r2]

        wallets = ["0x3333333333333333333333333333333333333333", "0x4444444444444444444444444444444444444444"]
        total_balance = await balance_checker.fetch_onchain_balance(wallets)
        assert total_balance == 250000.0
        assert balance_checker.evaluate_holder_tier(total_balance) == "Holder"
