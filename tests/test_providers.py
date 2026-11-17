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


def test_usage_ledger_reservations_prevent_concurrent_overspend(tmp_path):
    import threading

    path = str(tmp_path / "shared-usage.db")
    first = UsageLedger(path, monthly_limit_usd=1.0)
    second = UsageLedger(path, monthly_limit_usd=1.0)
    outcomes = []
    barrier = threading.Barrier(2)

    def reserve(ledger):
        barrier.wait()
        try:
            ledger.reserve("test", 0.7)
            outcomes.append("reserved")
        except BudgetExceeded:
            outcomes.append("blocked")

    threads = [
        threading.Thread(target=reserve, args=(first,)),
        threading.Thread(target=reserve, args=(second,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["blocked", "reserved"]
    first.close()
    second.close()


def test_usage_ledger_rejects_non_finite_reservations(tmp_path):
    ledger = UsageLedger(str(tmp_path / "usage.db"), monthly_limit_usd=1.0)
    with pytest.raises(ValueError):
        ledger.reserve("test", float("inf"))
    ledger.close()
