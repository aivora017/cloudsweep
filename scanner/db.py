import os
from contextlib import contextmanager
from typing import Dict, List, Optional

from psycopg2 import pool
from psycopg2.extras import Json


class ScannerDB:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self.connection_pool = pool.SimpleConnectionPool(
            1,
            10,
            self.database_url,
        )

    @contextmanager
    def get_connection(self):
        conn = self.connection_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.connection_pool.putconn(conn)

    def insert_findings(self, regions: List[str], findings: List[Dict]) -> int:
        total_findings = len(findings)
        total_waste_usd = sum(f["monthly_cost_usd"] for f in findings)
        total_waste_inr = sum(f["monthly_cost_inr"] for f in findings)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scan_runs (
                        regions,
                        total_findings,
                        total_waste_usd,
                        total_waste_inr
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        regions,
                        total_findings,
                        total_waste_usd,
                        total_waste_inr,
                    ),
                )
                scan_run_id = cur.fetchone()[0]

                for finding in findings:
                    cur.execute(
                        """
                        INSERT INTO findings (
                            scan_run_id,
                            resource_id,
                            resource_type,
                            region,
                            reason,
                            monthly_cost_usd,
                            monthly_cost_inr,
                            tags,
                            detected_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            scan_run_id,
                            finding["resource_id"],
                            finding["resource_type"],
                            finding["region"],
                            finding.get("reason"),
                            finding["monthly_cost_usd"],
                            finding["monthly_cost_inr"],
                            Json(finding.get("tags", {})),
                            finding.get("detected_at"),
                        ),
                    )

                return scan_run_id

    def resolve_finding(self, resource_id: str) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE findings
                    SET resolved_at = NOW(), updated_at = NOW()
                    WHERE resource_id = %s AND resolved_at IS NULL
                    """,
                    (resource_id,),
                )
                return cur.rowcount

    def get_waste_trend(self, weeks: int = 12) -> List[Dict]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        scan_date,
                        resource_type,
                        finding_count,
                        total_waste_inr,
                        total_waste_usd
                    FROM waste_trend_12w
                    WHERE scan_date >= NOW() - INTERVAL %s
                    ORDER BY scan_date DESC, resource_type
                    """,
                    (f"{weeks} weeks",),
                )
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]

    def close(self):
        self.connection_pool.closeall()
