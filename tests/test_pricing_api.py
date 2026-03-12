import scanner.pricing as pricing


class _FakePricingClient:
    def get_products(self, **kwargs):
        return {
            "PriceList": [
                {
                    "terms": {
                        "OnDemand": {
                            "x": {
                                "priceDimensions": {
                                    "y": {
                                        "pricePerUnit": {"USD": "0.1"}
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }


def test_get_ec2_cost_from_pricing_api(monkeypatch):
    monkeypatch.setattr(pricing, "_get_pricing_client", lambda: _FakePricingClient())
    cost = pricing.get_ec2_cost("m5.large")
    assert round(cost, 2) == 73.0


def test_get_ec2_cost_csv_fallback(monkeypatch):
    class _BrokenClient:
        def get_products(self, **kwargs):
            raise RuntimeError("pricing API unavailable")

    monkeypatch.setattr(pricing, "_get_pricing_client", lambda: _BrokenClient())
    cost = pricing.get_ec2_cost("unknown.instance", default=33.0)
    assert cost == 33.0
