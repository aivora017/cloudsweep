import os
import psycopg2
from contextlib import contextmanager
from typing import List, Dict, Optional


class DatabaseManager:

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            1,
            20,
            self.database_url
        )

    @contextmanager
    def get_connection(self):
        conn = self.connection_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)

    def insert_scan_run(self, regions: List[str], findings: List[Dict]) -> int:
        total_findings = len(findings)
        total_waste_usd = sum(f['monthly_cost_usd'] for f in findings)
        total_waste_inr = sum(f['monthly_cost_inr'] for f in findings)

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO scan_runs (regions, total_findings, total_waste_usd, total_waste_inr)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (regions, total_findings, total_waste_usd, total_waste_inr))

            scan_run_id = cur.fetchone()[0]
            return scan_run_id

    def insert_findings(self, scan_run_id: int, findings: List[Dict]):
        with self.get_connection() as conn:
            cur = conn.cursor()

            for finding in findings:
                cur.execute("""
                    INSERT INTO findings (
                        scan_run_id, resource_id, resource_type, region, reason,
                        monthly_cost_usd, monthly_cost_inr, tags, detected_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    scan_run_id,
                    finding['resource_id'],
                    finding['resource_type'],
                    finding['region'],
                    finding.get('reason'),
                    finding['monthly_cost_usd'],
                    finding['monthly_cost_inr'],
                    finding.get('tags', {}),
                    finding.get('detected_at')
                ))

    def resolve_missing_findings(self, scan_run_id: int, current_resources: List[str]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE findings
                SET resolved_at = NOW()
                WHERE resolved_at IS NULL
                  AND resource_id NOT IN %s
                  AND scan_run_id != %s
            """, (tuple(current_resources), scan_run_id))

    def get_active_waste(self) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM active_waste")

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            return [dict(zip(columns, row)) for row in rows]

    def get_waste_trend(self, weeks: int = 12) -> List[Dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT scan_date, resource_type, finding_count, total_waste_inr, total_waste_usd
                FROM waste_trend_12w
                WHERE scan_date >= NOW() - INTERVAL '{weeks} weeks'
                ORDER BY scan_date DESC
            """)

            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            return [dict(zip(columns, row)) for row in rows]

    def close(self):
        self.connection_pool.closeall()
