from scanner.pricing import convert_usd_to_inr, get_usd_to_inr_rate


def test_convert_usd_to_inr_fixed_rate():
    assert round(convert_usd_to_inr(100, rate=83.5), 2) == 8350.00


def test_get_usd_to_inr_rate_fallback(monkeypatch):
    import scanner.pricing as pricing

    pricing.get_usd_to_inr_rate.cache_clear()

    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *args, **kwargs):
            raise RuntimeError("network unavailable")

    monkeypatch.setattr(pricing.httpx, "Client", BrokenClient)
    rate = pricing.get_usd_to_inr_rate()
    assert rate > 0
