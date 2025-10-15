"""Tests for the persistence module."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from ingestion.persistence import DataStore, _validate_identifier


class TestValidateIdentifier:
    """Tests for SQL identifier validation."""

    def test_valid_identifiers(self):
        """Valid identifiers should not raise."""
        valid_names = [
            "table_name",
            "Table123",
            "_private",
            "camelCase",
            "SCREAMING_SNAKE",
            "a1b2c3",
        ]
        for name in valid_names:
            _validate_identifier(name)  # Should not raise

    def test_invalid_identifiers(self):
        """Invalid identifiers should raise ValueError."""
        invalid_names = [
            "table-name",  # hyphen
            "table name",  # space
            "table.name",  # dot
            "table;DROP",  # semicolon (SQL injection attempt)
            "123table",    # starts with number
            "",            # empty
            "table'name",  # quote
        ]
        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid"):
                _validate_identifier(name)


class TestDataStore:
    """Tests for DataStore class."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Provide a temporary database path."""
        return tmp_path / "test.duckdb"

    @pytest.fixture
    def store(self, temp_db_path: Path) -> DataStore:
        """Provide a DataStore instance."""
        return DataStore(temp_db_path, schema="test_schema")

    def test_init_creates_schema(self, temp_db_path: Path):
        """DataStore should create the schema on init."""
        store = DataStore(temp_db_path, schema="my_schema")
        
        with store.connect() as conn:
            schemas = conn.execute(
                "SELECT schema_name FROM information_schema.schemata"
            ).fetchall()
            schema_names = [s[0] for s in schemas]
            assert "my_schema" in schema_names

    def test_init_with_invalid_schema_name(self, temp_db_path: Path):
        """DataStore should reject invalid schema names."""
        with pytest.raises(ValueError, match="Invalid schema name"):
            DataStore(temp_db_path, schema="bad-schema")

    def test_write_table_replace_mode(self, store: DataStore):
        """write_table should replace existing table in replace mode."""
        records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        
        store.write_table("users", records, mode="replace")
        
        with store.connect() as conn:
            result = conn.execute('SELECT * FROM test_schema.users ORDER BY id').fetchall()
            assert len(result) == 2
            assert result[0] == (1, "Alice")
            assert result[1] == (2, "Bob")

    def test_write_table_replace_overwrites(self, store: DataStore):
        """write_table in replace mode should overwrite existing data."""
        store.write_table("items", [{"id": 1, "value": "old"}], mode="replace")
        store.write_table("items", [{"id": 2, "value": "new"}], mode="replace")
        
        with store.connect() as conn:
            result = conn.execute('SELECT * FROM test_schema.items').fetchall()
            assert len(result) == 1
            assert result[0] == (2, "new")

    def test_write_table_append_mode(self, store: DataStore):
        """write_table should append to existing table in append mode."""
        store.write_table("logs", [{"msg": "first"}], mode="replace")
        store.write_table("logs", [{"msg": "second"}], mode="append")
        
        with store.connect() as conn:
            result = conn.execute('SELECT msg FROM test_schema.logs ORDER BY msg').fetchall()
            assert len(result) == 2
            assert result[0][0] == "first"
            assert result[1][0] == "second"

    def test_write_table_empty_records(self, store: DataStore):
        """write_table should handle empty records gracefully."""
        store.write_table("empty", [], mode="replace")
        
        # Should not create table
        with store.connect() as conn:
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'test_schema'"
            ).fetchall()
            assert ("empty",) not in tables

    def test_write_table_invalid_name(self, store: DataStore):
        """write_table should reject invalid table names."""
        with pytest.raises(ValueError, match="Invalid table name"):
            store.write_table("bad-table", [{"id": 1}])

    def test_write_table_invalid_mode(self, store: DataStore):
        """write_table should reject invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode"):
            store.write_table("test", [{"id": 1}], mode="upsert")

    def test_write_table_database_error(self, store: DataStore):
        """write_table should handle schema mismatches gracefully."""
        # DuckDB is actually very flexible with schema changes in append mode
        # It will add columns as needed, so this test verifies that behavior
        store.write_table("flexible", [{"id": 1, "name": "test"}], mode="replace")
        
        # DuckDB allows appending with different columns - it adds NULL for missing columns
        store.write_table("flexible", [{"id": 2, "age": 25}], mode="append")
        
        with store.connect() as conn:
            result = conn.execute("SELECT * FROM test_schema.flexible ORDER BY id").fetchall()
            # First row has name, second has age (with NULLs for missing columns)
            assert len(result) == 2
            assert result[0][0] == 1  # id from first row
            assert result[1][0] == 2  # id from second row

    def test_connect_returns_connection(self, store: DataStore):
        """connect should return a DuckDB connection."""
        conn = store.connect()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        
        # Should be able to execute queries
        result = conn.execute("SELECT 1 as test").fetchone()
        assert result == (1,)
        conn.close()

    def test_multiple_stores_same_db(self, temp_db_path: Path):
        """Multiple DataStore instances should work with same database."""
        store1 = DataStore(temp_db_path, schema="schema1")
        store2 = DataStore(temp_db_path, schema="schema2")
        
        store1.write_table("data", [{"value": 1}])
        store2.write_table("data", [{"value": 2}])
        
        with duckdb.connect(str(temp_db_path)) as conn:
            result1 = conn.execute("SELECT value FROM schema1.data").fetchone()
            result2 = conn.execute("SELECT value FROM schema2.data").fetchone()
            
            assert result1 == (1,)
            assert result2 == (2,)
