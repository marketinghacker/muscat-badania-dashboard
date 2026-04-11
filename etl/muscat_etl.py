#!/usr/bin/env python3
"""
Muscat Data Intelligence — ETL Pipeline
Extracts data from Odoo PostgreSQL (via VPN) → transforms → loads to Railway PostgreSQL.

Usage:
    python3 muscat_etl.py                          # full ETL
    python3 muscat_etl.py --dry-run                # query Odoo, print stats, don't write
    python3 muscat_etl.py --railway-url <URL>       # override Railway connection string

Requires: Active Pritunl VPN connection to Muscat network.
"""

import argparse
import json
import os
import sys
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ─── Odoo (source) connection ───────────────────────────────────────────────
ODOO_CONFIG = {
    "host": "10.0.216.28",
    "port": 5432,
    "dbname": "odoo",
    "user": "marcin",
    "password": "cx4iqGA1EHw0",
}

# ─── POS → City mapping ────────────────────────────────────────────────────
CITY_MAP = {
    "ARK": {"city": "Warszawa", "salon": "Arkadia", "type": "galeria", "opened": "2015-01-01"},
    "GA1": {"city": "Gdańsk", "salon": "Galeria Bałtycka", "type": "galeria", "opened": "2024-06-01"},
    "GDA": {"city": "Gdynia", "salon": "Riviera", "type": "galeria", "opened": "2015-01-01"},
    "KAT": {"city": "Katowice", "salon": "Silesia City Center", "type": "galeria", "opened": "2015-01-01"},
    "KR2": {"city": "Kraków", "salon": "Starowiślna", "type": "ulica", "opened": "2015-01-01"},
    "KRA": {"city": "Kraków", "salon": "Galeria Krakowska", "type": "galeria", "opened": "2015-01-01"},
    "LDZ": {"city": "Łódź", "salon": "Manufaktura", "type": "galeria", "opened": "2015-01-01"},
    "LUB": {"city": "Lublin", "salon": "Lublin Plaza", "type": "galeria", "opened": "2015-01-01"},
    "POZ": {"city": "Poznań", "salon": "Posnania", "type": "galeria", "opened": "2015-01-01"},
    "SZC": {"city": "Szczecin", "salon": "Galaxy / Kaskada", "type": "galeria", "opened": "2015-01-01"},
    "TRG": {"city": "Warszawa", "salon": "Targowa", "type": "ulica", "opened": "2015-01-01"},
    "WA4": {"city": "Warszawa", "salon": "Wola Park", "type": "galeria", "opened": "2024-03-01"},
    "WA5": {"city": "Warszawa", "salon": "Galeria Mokotów", "type": "galeria", "opened": "2025-11-01"},
    "WAW": {"city": "Warszawa", "salon": "Chmielna", "type": "ulica", "opened": "2015-01-01"},
    "WR2": {"city": "Wrocław", "salon": "Wroclavia", "type": "galeria", "opened": "2025-10-01"},
    "WRO": {"city": "Wrocław", "salon": "Stawowa", "type": "ulica", "opened": "2015-01-01", "closed": "2025-09-01"},
}

EXCLUDE_POS = {"PRA"}  # Praga CZ

# Sale teams that map to POS codes
SALE_TEAM_TO_POS = {
    "ARK": "ARK", "GA1": "GA1", "GDA": "GDA", "KAT": "KAT",
    "KR2": "KR2", "KRA": "KRA", "LDZ": "LDZ", "LUB": "LUB",
    "POZ": "POZ", "SZC": "SZC", "TRG": "TRG", "WA4": "WA4",
    "WA5": "WA5", "WAW": "WAW", "WR2": "WR2", "WRO": "WRO",
}
EXCLUDE_TEAMS = {"eCZ", "PRA"}


def get_city(pos_code):
    info = CITY_MAP.get(pos_code)
    return info["city"] if info else None


# ─── EXTRACT ────────────────────────────────────────────────────────────────

def extract_events(conn):
    """Extract real visits (no empty slots) from muscat_events_report."""
    query = """
    SELECT
        pos,
        date_trunc('month', exam_datetime::timestamp)::date AS month,
        count(*) AS total,
        count(*) FILTER (WHERE status_post = 'done') AS done,
        count(*) FILTER (WHERE status_post = 'canceled') AS canceled,
        count(*) FILTER (WHERE status_post = 'absent') AS absent,
        count(*) FILTER (WHERE source = 'website') AS source_website,
        count(*) FILTER (WHERE source = 'showroom') AS source_showroom,
        count(*) FILTER (WHERE source = 'helpline') AS source_helpline,
        count(*) FILTER (WHERE source = 'docplanner') AS source_docplanner
    FROM muscat_events_report
    WHERE (slot_type IS NULL OR slot_type = '')
      AND exam_datetime IS NOT NULL
      AND exam_datetime::timestamp >= '2023-01-01'
    GROUP BY pos, month
    ORDER BY pos, month
    """
    df = pd.read_sql(query, conn)
    df = df[~df["pos"].isin(EXCLUDE_POS)]
    df["city"] = df["pos"].map(get_city)
    df["done_rate"] = (df["done"] / df["total"]).round(4)
    df["cancel_rate"] = (df["canceled"] / df["total"]).round(4)
    return df


def extract_sales(conn):
    """Extract monthly sales aggregates from muscat_sale_report."""
    query = """
    SELECT
        sale_team,
        date_trunc('month', order_date)::date AS month,
        count(*) AS order_lines,
        count(DISTINCT order_number) AS unique_orders,
        sum(product_price_gross_in_pln) AS revenue_gross,
        count(*) FILTER (WHERE is_glasses = 1) AS glasses_lines,
        sum(product_price_gross_in_pln) FILTER (WHERE is_glasses = 1) AS glasses_revenue,
        -- Product offer breakdown (glasses only)
        sum(product_price_gross_in_pln) FILTER (WHERE is_glasses = 1 AND product_offer = 'Blue Block') AS blue_block_revenue,
        sum(product_price_gross_in_pln) FILTER (WHERE is_glasses = 1 AND product_offer = 'Relax') AS relax_revenue,
        sum(product_price_gross_in_pln) FILTER (WHERE is_glasses = 1 AND product_offer = 'Classic') AS classic_revenue,
        sum(product_price_gross_in_pln) FILTER (WHERE is_glasses = 1 AND product_offer = 'Sun') AS sun_revenue,
        -- Product category breakdown
        sum(product_price_gross_in_pln) FILTER (WHERE product_category = 'Zerówki') AS zerowki_revenue,
        sum(product_price_gross_in_pln) FILTER (WHERE product_category = 'Korekcja') AS korekcja_revenue,
        sum(product_price_gross_in_pln) FILTER (WHERE product_category = 'Progresywne') AS progresywne_revenue,
        -- Premium metrics
        count(*) FILTER (WHERE is_glasses = 1 AND product_construction = 'Asfera') AS asfera_count,
        count(*) FILTER (WHERE is_glasses = 1 AND product_construction = 'Sfera') AS sfera_count,
        sum(product_price_gross_in_pln) FILTER (WHERE is_glasses = 1 AND product_construction = 'Asfera') AS asfera_revenue,
        -- Index breakdown
        count(*) FILTER (WHERE is_glasses = 1 AND product_index = '1.5') AS index_15_count,
        count(*) FILTER (WHERE is_glasses = 1 AND product_index = '1.6') AS index_16_count,
        count(*) FILTER (WHERE is_glasses = 1 AND product_index IN ('1.67','1.74')) AS index_premium_count
    FROM muscat_sale_report
    WHERE order_date >= '2023-01-01'
    GROUP BY sale_team, month
    ORDER BY sale_team, month
    """
    df = pd.read_sql(query, conn)
    df = df[~df["sale_team"].isin(EXCLUDE_TEAMS)]
    df["city"] = df["sale_team"].map(lambda t: get_city(SALE_TEAM_TO_POS.get(t, t)))
    df["avg_order_value"] = (df["glasses_revenue"] / df["glasses_lines"]).round(2)
    df.loc[df["glasses_lines"] == 0, "avg_order_value"] = 0
    return df


def extract_traffic(conn):
    """Extract monthly traffic aggregates from muscat_traffic."""
    query = """
    SELECT
        team_name,
        date_trunc('month', visit_date)::date AS month,
        sum(entries) AS total_entries,
        sum(passing) AS total_passing,
        round(avg(entries)::numeric, 2) AS avg_hourly_entries
    FROM muscat_traffic
    GROUP BY team_name, month
    ORDER BY team_name, month
    """
    df = pd.read_sql(query, conn)
    df["city"] = df["team_name"].map(get_city)
    return df


def extract_customers_city(conn):
    """Extract customer demographics aggregated by city."""
    query = """
    SELECT
        city,
        count(*) AS total_customers,
        count(*) FILTER (WHERE customer_type = 'NOWY') AS new_customers,
        count(*) FILTER (WHERE customer_type = 'STARY') AS returning_customers,
        avg(orders_amount) FILTER (WHERE orders_amount > 0) AS avg_order_value,
        round((100.0 * count(*) FILTER (WHERE sex = 'female')
            / NULLIF(count(*) FILTER (WHERE sex IN ('female','male')), 0))::numeric, 1) AS female_pct,
        round((100.0 * count(*) FILTER (WHERE sex = 'male')
            / NULLIF(count(*) FILTER (WHERE sex IN ('female','male')), 0))::numeric, 1) AS male_pct,
        round(avg(age) FILTER (WHERE age IS NOT NULL AND age BETWEEN 10 AND 100)::numeric, 1) AS avg_age,
        round((100.0 * count(*) FILTER (WHERE consent_marketing_email)
            / NULLIF(count(*), 0))::numeric, 1) AS consent_email_pct,
        round((100.0 * count(*) FILTER (WHERE consent_marketing_sms)
            / NULLIF(count(*), 0))::numeric, 1) AS consent_sms_pct
    FROM muscat_customer_report_anon
    WHERE city IS NOT NULL AND city != ''
    GROUP BY city
    ORDER BY total_customers DESC
    """
    return pd.read_sql(query, conn)


def _fetch_customer_demographics(conn):
    """Fetch only unique_id, age, sex from customers (lightweight query)."""
    query = """
    SELECT unique_id, age, sex
    FROM muscat_customer_report_anon
    WHERE age IS NOT NULL AND age BETWEEN 18 AND 80
      AND sex IN ('female','male')
    """
    return pd.read_sql(query, conn)


def _age_group(age):
    if 18 <= age <= 25: return '18-25'
    if 26 <= age <= 35: return '26-35'
    if 36 <= age <= 45: return '36-45'
    if 46 <= age <= 55: return '46-55'
    if age > 55: return '55+'
    return None


def extract_demographics_temporal(conn, cust_df=None):
    """Extract age/sex demographics over time per salon — JOIN in pandas (fast)."""
    events_q = """
    SELECT event_id, pos, exam_datetime, status_post, client_id
    FROM muscat_events_report
    WHERE (slot_type IS NULL OR slot_type = '')
      AND exam_datetime IS NOT NULL
      AND exam_datetime::timestamp >= '2023-01-01'
      AND pos != 'PRA'
      AND client_id IS NOT NULL AND client_id != ''
    """
    events = pd.read_sql(events_q, conn)
    if cust_df is None:
        cust_df = _fetch_customer_demographics(conn)

    merged = events.merge(cust_df, left_on='client_id', right_on='unique_id', how='inner')
    merged['year'] = pd.to_datetime(merged['exam_datetime']).dt.year
    merged['age_group'] = merged['age'].apply(_age_group)
    merged = merged.dropna(subset=['age_group'])

    result = merged.groupby(['pos', 'year', 'age_group', 'sex']).agg(
        bookings=('event_id', 'nunique'),
        done=('event_id', lambda x: merged.loc[x.index][merged.loc[x.index, 'status_post'] == 'done']['event_id'].nunique())
    ).reset_index()

    # Simpler done count
    merged['is_done'] = (merged['status_post'] == 'done').astype(int)
    result = merged.groupby(['pos', 'year', 'age_group', 'sex']).agg(
        bookings=('event_id', 'nunique'),
        done=('is_done', 'sum')
    ).reset_index()

    result['city'] = result['pos'].map(get_city)
    return result


def extract_sales_demographics(conn, cust_df=None):
    """Extract AOV per age group per year per salon — JOIN in pandas (fast)."""
    sales_q = """
    SELECT sale_team, order_date, order_number, product_price_gross_in_pln, client_unique_id
    FROM muscat_sale_report
    WHERE is_glasses = 1 AND order_date >= '2023-01-01'
      AND sale_team NOT IN ('eCZ','PRA')
      AND client_unique_id IS NOT NULL AND client_unique_id != ''
    """
    sales = pd.read_sql(sales_q, conn)
    if cust_df is None:
        cust_df = _fetch_customer_demographics(conn)

    merged = sales.merge(cust_df, left_on='client_unique_id', right_on='unique_id', how='inner')
    merged['year'] = pd.to_datetime(merged['order_date']).dt.year
    merged['age_group'] = merged['age'].apply(_age_group)
    merged = merged.dropna(subset=['age_group'])

    result = merged.groupby(['sale_team', 'year', 'age_group', 'sex']).agg(
        orders=('order_number', 'nunique'),
        avg_price=('product_price_gross_in_pln', 'mean'),
        total_revenue=('product_price_gross_in_pln', 'sum')
    ).reset_index()
    result['avg_price'] = result['avg_price'].round(2)
    result['total_revenue'] = result['total_revenue'].round(2)
    result = result.rename(columns={'sale_team': 'pos'})
    result['city'] = result['pos'].map(lambda t: get_city(SALE_TEAM_TO_POS.get(t, t)))
    return result


def extract_product_trends(conn):
    """Extract top product (frame) models per salon per quarter."""
    query = """
    SELECT
        sale_team AS pos,
        date_trunc('quarter', order_date)::date AS quarter,
        product_name,
        count(*) AS qty,
        round(sum(product_price_gross_in_pln)::numeric, 2) AS revenue,
        round(avg(product_price_gross_in_pln)::numeric, 2) AS avg_price
    FROM muscat_sale_report
    WHERE is_glasses = 1
      AND order_date >= '2023-01-01'
      AND product_name IS NOT NULL AND product_name != ''
      AND sale_team NOT IN ('eCZ','PRA')
    GROUP BY sale_team, quarter, product_name
    HAVING count(*) >= 3
    ORDER BY sale_team, quarter, qty DESC
    """
    df = pd.read_sql(query, conn)
    df["city"] = df["pos"].map(lambda t: get_city(SALE_TEAM_TO_POS.get(t, t)))
    return df


def extract_geo_coverage(conn):
    """Extract customer ZIP prefix distribution per city."""
    query = """
    SELECT
        LEFT(zip, 2) AS zip_prefix,
        city,
        count(*) AS customers,
        count(*) FILTER (WHERE customer_type = 'STARY') AS returning_customers,
        avg(orders_amount) FILTER (WHERE orders_amount > 0) AS avg_order_value
    FROM muscat_customer_report_anon
    WHERE zip IS NOT NULL AND zip != '' AND city IS NOT NULL AND city != ''
    GROUP BY zip_prefix, city
    HAVING count(*) >= 5
    ORDER BY customers DESC
    """
    return pd.read_sql(query, conn)


# ─── LOAD (to Railway) ─────────────────────────────────────────────────────

SCHEMA_SQL = """
DROP TABLE IF EXISTS events_monthly CASCADE;
DROP TABLE IF EXISTS sales_monthly CASCADE;
DROP TABLE IF EXISTS traffic_monthly CASCADE;
DROP TABLE IF EXISTS customers_city CASCADE;
DROP TABLE IF EXISTS demographics_temporal CASCADE;
DROP TABLE IF EXISTS sales_demographics CASCADE;
DROP TABLE IF EXISTS product_trends CASCADE;
DROP TABLE IF EXISTS geo_coverage CASCADE;
DROP TABLE IF EXISTS city_mapping CASCADE;
DROP TABLE IF EXISTS ad_spend_monthly CASCADE;
DROP TABLE IF EXISTS etl_log CASCADE;

CREATE TABLE events_monthly (
    pos TEXT, city TEXT, month DATE,
    total INT, done INT, canceled INT, absent INT,
    source_website INT, source_showroom INT, source_helpline INT, source_docplanner INT,
    done_rate NUMERIC, cancel_rate NUMERIC
);

CREATE TABLE sales_monthly (
    sale_team TEXT, city TEXT, month DATE,
    order_lines INT, unique_orders INT, revenue_gross NUMERIC,
    glasses_lines INT, glasses_revenue NUMERIC, avg_order_value NUMERIC,
    blue_block_revenue NUMERIC, relax_revenue NUMERIC, classic_revenue NUMERIC, sun_revenue NUMERIC,
    zerowki_revenue NUMERIC, korekcja_revenue NUMERIC, progresywne_revenue NUMERIC,
    asfera_count INT, sfera_count INT, asfera_revenue NUMERIC,
    index_15_count INT, index_16_count INT, index_premium_count INT
);

CREATE TABLE traffic_monthly (
    team_name TEXT, city TEXT, month DATE,
    total_entries INT, total_passing INT, avg_hourly_entries NUMERIC
);

CREATE TABLE customers_city (
    city TEXT, total_customers INT, new_customers INT, returning_customers INT,
    avg_order_value NUMERIC, female_pct NUMERIC, male_pct NUMERIC, avg_age NUMERIC,
    consent_email_pct NUMERIC, consent_sms_pct NUMERIC
);

CREATE TABLE demographics_temporal (
    pos TEXT, city TEXT, year INT, age_group TEXT, sex TEXT,
    bookings INT, done INT
);

CREATE TABLE sales_demographics (
    pos TEXT, city TEXT, year INT, age_group TEXT, sex TEXT,
    orders INT, avg_price NUMERIC, total_revenue NUMERIC
);

CREATE TABLE product_trends (
    pos TEXT, city TEXT, quarter DATE, product_name TEXT,
    qty INT, revenue NUMERIC, avg_price NUMERIC
);

CREATE TABLE geo_coverage (
    zip_prefix TEXT, city TEXT, customers INT,
    returning_customers INT, avg_order_value NUMERIC
);

CREATE TABLE city_mapping (
    pos_code TEXT PRIMARY KEY, city TEXT, salon_name TEXT,
    location_type TEXT, opened_date DATE, closed_date DATE
);

CREATE TABLE ad_spend_monthly (
    city TEXT, month DATE,
    meta_spend NUMERIC, google_spend NUMERIC, total_spend NUMERIC,
    meta_impressions BIGINT, google_impressions BIGINT,
    meta_clicks INT, google_clicks INT, google_conversions NUMERIC
);

CREATE TABLE etl_log (
    run_at TIMESTAMP DEFAULT now(),
    table_name TEXT, row_count INT, min_date TEXT, max_date TEXT
);
"""


def load_dataframe(railway_conn, table_name, df, date_col=None):
    """Insert DataFrame into Railway PostgreSQL table."""
    if df.empty:
        print(f"  ⚠ {table_name}: empty DataFrame, skipping")
        return

    # Replace NaN with None for SQL
    df = df.where(pd.notnull(df), None)

    cols = list(df.columns)
    placeholders = ",".join(["%s"] * len(cols))
    col_names = ",".join(cols)

    cur = railway_conn.cursor()
    values = [tuple(row) for row in df.values]
    execute_values(
        cur,
        f"INSERT INTO {table_name} ({col_names}) VALUES %s",
        values,
        page_size=1000,
    )

    # Log
    min_d = str(df[date_col].min()) if date_col and date_col in df.columns else ""
    max_d = str(df[date_col].max()) if date_col and date_col in df.columns else ""
    cur.execute(
        "INSERT INTO etl_log (table_name, row_count, min_date, max_date) VALUES (%s,%s,%s,%s)",
        (table_name, len(df), min_d, max_d),
    )
    railway_conn.commit()
    print(f"  ✓ {table_name}: {len(df)} rows ({min_d} → {max_d})")


def load_city_mapping(railway_conn):
    """Insert city mapping reference data."""
    cur = railway_conn.cursor()
    for pos, info in CITY_MAP.items():
        cur.execute(
            """INSERT INTO city_mapping (pos_code, city, salon_name, location_type, opened_date, closed_date)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (pos, info["city"], info["salon"], info["type"],
             info["opened"], info.get("closed")),
        )
    railway_conn.commit()
    print(f"  ✓ city_mapping: {len(CITY_MAP)} rows")


# ─── MAIN ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Muscat ETL: Odoo → Railway PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Extract only, print stats")
    parser.add_argument("--railway-url", type=str, default=os.environ.get("RAILWAY_DATABASE_URL"),
                        help="Railway PostgreSQL connection string")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Muscat Data Intelligence — ETL Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── Extract from Odoo ──
    print("📡 Connecting to Odoo (10.0.216.28)...")
    try:
        odoo_conn = psycopg2.connect(**ODOO_CONFIG)
        print("  ✓ Connected to Odoo PostgreSQL 17.9\n")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print("  → Is Pritunl VPN connected?")
        sys.exit(1)

    print("📊 Extracting data...")
    events = extract_events(odoo_conn)
    print(f"  events_monthly: {len(events)} rows")

    sales = extract_sales(odoo_conn)
    print(f"  sales_monthly: {len(sales)} rows")

    traffic = extract_traffic(odoo_conn)
    print(f"  traffic_monthly: {len(traffic)} rows")

    customers = extract_customers_city(odoo_conn)
    print(f"  customers_city: {len(customers)} rows")

    print("  fetching customer demographics for local JOIN...")
    cust_df = _fetch_customer_demographics(odoo_conn)
    print(f"  customer demographics: {len(cust_df)} rows (for local JOIN)")

    demo_temporal = extract_demographics_temporal(odoo_conn, cust_df)
    print(f"  demographics_temporal: {len(demo_temporal)} rows")

    sales_demo = extract_sales_demographics(odoo_conn, cust_df)
    print(f"  sales_demographics: {len(sales_demo)} rows")

    products = extract_product_trends(odoo_conn)
    print(f"  product_trends: {len(products)} rows")

    geo = extract_geo_coverage(odoo_conn)
    print(f"  geo_coverage: {len(geo)} rows")

    odoo_conn.close()
    print(f"\n  Total: {len(events)+len(sales)+len(traffic)+len(customers)+len(demo_temporal)+len(sales_demo)+len(products)+len(geo)} rows extracted")

    if args.dry_run:
        print("\n🔍 DRY RUN — not writing to Railway")
        print("\nSample events_monthly:")
        print(events.head(10).to_string(index=False))
        print("\nSample sales_monthly:")
        print(sales[["sale_team","city","month","unique_orders","revenue_gross","avg_order_value"]].head(10).to_string(index=False))
        return

    # ── Load to Railway ──
    if not args.railway_url:
        print("\n✗ No Railway URL. Set RAILWAY_DATABASE_URL or use --railway-url")
        sys.exit(1)

    print(f"\n🚂 Connecting to Railway PostgreSQL...")
    try:
        railway_conn = psycopg2.connect(args.railway_url)
        print("  ✓ Connected\n")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        sys.exit(1)

    print("🏗️  Creating schema...")
    cur = railway_conn.cursor()
    cur.execute(SCHEMA_SQL)
    railway_conn.commit()
    print("  ✓ Schema created\n")

    print("📤 Loading data...")
    load_city_mapping(railway_conn)
    load_dataframe(railway_conn, "events_monthly", events, "month")
    load_dataframe(railway_conn, "sales_monthly", sales, "month")
    load_dataframe(railway_conn, "traffic_monthly", traffic, "month")
    load_dataframe(railway_conn, "customers_city", customers)
    load_dataframe(railway_conn, "demographics_temporal", demo_temporal)
    load_dataframe(railway_conn, "sales_demographics", sales_demo)
    load_dataframe(railway_conn, "product_trends", products)
    load_dataframe(railway_conn, "geo_coverage", geo)

    railway_conn.close()

    print(f"\n{'='*60}")
    print(f"  ✅ ETL Complete!")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
