from scanner.db import ScannerDB


class _FakeCursor:
    def __init__(self):
        self.rowcount = 1
        self.description = [
            ("scan_date",),
            ("resource_type",),
            ("finding_count",),
            ("total_waste_inr",),
            ("total_waste_usd",),
        ]
        self._rows = [("2026-03-12", "EC2", 1, 1000.0, 12.0)]

    def execute(self, query, params=None):
        self._query = query
        self._params = params

    def fetchone(self):
        return [42]

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def cursor(self):
        return _FakeCursor()

    def commit(self):
        pass

    def rollback(self):
        pass


class _FakePool:
    def __init__(self, *args, **kwargs):
        self.conn = _FakeConnection()

    def getconn(self):
        return self.conn

    def putconn(self, conn):
        pass

    def closeall(self):
        pass


def test_insert_and_resolve(monkeypatch):
    import scanner.db as db_module

    monkeypatch.setattr(db_module.pool, "SimpleConnectionPool", _FakePool)

    db = ScannerDB("postgresql://fake")
    findings = [
        {
            "resource_id": "i-1",
            "resource_type": "EC2",
            "region": "ap-south-1",
            "reason": "test",
            "monthly_cost_usd": 10.0,
            "monthly_cost_inr": 900.0,
            "tags": {},
            "detected_at": "2026-03-12T00:00:00Z",
        }
    ]
    scan_run_id = db.insert_findings(["ap-south-1"], findings)
    assert scan_run_id == 42

    updated = db.resolve_finding("i-1")
    assert updated == 1

    trend = db.get_waste_trend(12)
    assert trend[0]["resource_type"] == "EC2"
