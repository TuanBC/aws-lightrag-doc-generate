import pytest
from fastapi import HTTPException

from app.services.cache import InMemoryTTLCache
from app.services.scoring_engine import ScoringEngine


class DummyEtherscan:
    def __init__(self, transactions):
        self.transactions = transactions
        self.calls = 0

    async def fetch_transactions(self, address: str):
        self.calls += 1
        return self.transactions.get(address, [])


class DummyCreditService:
    def extract_features(self, transactions, wallet_address):
        return {
            "account_age_days": 720,
            "avg_tx_value": 0.02,
            "tx_count_6m": 5,
            "unique_counterparties": 10,
            "contract_interactions": 3,
            "largest_outgoing_tx": 50,
            "months_with_tx": 24,
            "tx_value_skewness": 10,
            "total_transactions": len(transactions),
        }

    def calculate_scorecard_credit_score(self, features):
        return 640.0

    def extract_time_series_data(self, transactions, wallet_address):
        return {
            "monthly_tx_count": [],
            "monthly_tx_volume": [],
            "monthly_avg_value": [],
            "cumulative_balance": [],
        }


class DummyOffchain:
    def generate(self, wallet_address, features):
        return {"age": 30, "occupation": "professional"}


ADDRESS = "0x" + "a" * 40


@pytest.mark.asyncio
async def test_scoring_engine_returns_result():
    etherscan = DummyEtherscan(
        {
            ADDRESS: [
                {
                    "value": 1,
                    "timeStamp": 1,
                    "from": ADDRESS,
                    "to": ADDRESS,
                    "input": "",
                    "isError": 0,
                }
            ]
        }
    )
    engine = ScoringEngine(
        etherscan_service=etherscan,
        credit_scoring_service=DummyCreditService(),
        offchain_generator=DummyOffchain(),
        cache=InMemoryTTLCache(ttl_seconds=60, max_items=10),
    )

    result = await engine.evaluate_wallet(ADDRESS)
    assert result.credit_score == pytest.approx(640.0)
    assert result.transaction_count == 1


@pytest.mark.asyncio
async def test_scoring_engine_caches_results():
    etherscan = DummyEtherscan(
        {
            ADDRESS: [
                {
                    "value": 1,
                    "timeStamp": 1,
                    "from": ADDRESS,
                    "to": ADDRESS,
                    "input": "",
                    "isError": 0,
                }
            ]
        }
    )
    engine = ScoringEngine(
        etherscan_service=etherscan,
        credit_scoring_service=DummyCreditService(),
        offchain_generator=DummyOffchain(),
        cache=InMemoryTTLCache(ttl_seconds=60, max_items=10),
    )

    await engine.evaluate_wallet(ADDRESS)
    await engine.evaluate_wallet(ADDRESS)
    assert etherscan.calls == 1


@pytest.mark.asyncio
async def test_scoring_engine_validates_address():
    engine = ScoringEngine(
        etherscan_service=DummyEtherscan({}),
        credit_scoring_service=DummyCreditService(),
        offchain_generator=DummyOffchain(),
    )

    with pytest.raises(HTTPException):
        await engine.evaluate_wallet("invalid")
