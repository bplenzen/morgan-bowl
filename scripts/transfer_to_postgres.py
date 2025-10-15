import duckdb
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to DuckDB
duck = duckdb.connect('/Users/benlenzen/Codebase/morganbowl/data/processed/warehouse.duckdb')

# Connect to PostgreSQL
pg = psycopg2.connect(
    dbname='lightdash',
    user='lightdash',
    password='lightdash',
    host='localhost',
    port='5432'
)
pg.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create staging schema
with pg.cursor() as cur:
    cur.execute('CREATE SCHEMA IF NOT EXISTS staging;')

# Get list of tables from DuckDB
tables = duck.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='staging'").fetchall()

# Transfer each table
for (table,) in tables:
    print(f"Transferring table: {table}")
    
    # Get table data as CSV
    duck.execute(f"COPY (SELECT * FROM staging.{table}) TO '__temp.csv' (HEADER TRUE, DELIMITER ',');")
    
    # Get column definitions
    columns = duck.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema='staging' AND table_name='{table}'
    """).fetchall()
    
    # Create table in PostgreSQL
    column_defs = [f"{col} {dtype}" for col, dtype in columns]
    create_sql = f"CREATE TABLE IF NOT EXISTS staging.{table} ({', '.join(column_defs)})"
    
    with pg.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS staging.{table}")
        cur.execute(create_sql)
        
        # Load data from CSV
        with open('__temp.csv', 'r') as f:
            cur.copy_expert(f"COPY staging.{table} FROM STDIN WITH CSV HEADER", f)

print("Data transfer complete!")