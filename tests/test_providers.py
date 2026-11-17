import pytest
from rune.core.providers import BudgetExceeded, ProviderConfig, ProviderUsage, UsageLedger


def test_usage_ledger_tracks_monthly_spend(tmp_path):
    ledger = UsageLedger(str(tmp_path / "usage.db"), monthly_limit_usd=1.0)
    ledger.record("test", ProviderUsage(100, 100, 0.4))
    assert ledger.spent() == pytest.approx(0.4)
    with pytest.raises(BudgetExceeded):
        ledger.record("test", ProviderUsage(100, 100, 0.7))
    ledger.close()


def test_usage_ledger_rejects_nonpositive_budget(tmp_path):
    with pytest.raises(ValueError):
        UsageLedger(str(tmp_path / "usage.db"), monthly_limit_usd=0)


def test_provider_config_keeps_model_id_configurable():
    config = ProviderConfig("primary", "configured-model-id", "RUNE_PRIMARY_API_KEY", 1.0, 2.0)
    assert config.model == "configured-model-id"
