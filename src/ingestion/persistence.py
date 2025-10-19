from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping

import duckdb
import polars as pl
import structlog

logger = structlog.get_logger("morgan_bowl.persistence")

# Valid table/schema name pattern (alphanumeric, underscore only)
_VALID_SQL_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifier(name: str, identifier_type: str = "identifier") -> None:
    """Validate SQL identifier to prevent injection attacks.

    Args:
        name: The identifier to validate
        identifier_type: Type of identifier (for error messages)

    Raises:
        ValueError: If identifier contains invalid characters
    """
    if not _VALID_SQL_IDENTIFIER.match(name):
        raise ValueError(
            f"Invalid {identifier_type}: '{name}'. "
            f"Must contain only alphanumeric characters and underscores, "
            f"and start with a letter or underscore."
        )


class DataStore:
    """Single data store for fantasy football data using DuckDB.

    Note on connection management:
    We create a new connection for each operation rather than maintaining
    a persistent connection because:
    1. DuckDB connections are cheap (embedded database)
    2. Avoids threading issues if used from multiple contexts
    3. Ensures clean state for each operation
    4. File-based DB means no connection pooling needed

    For high-throughput scenarios, consider refactoring to use a single
    connection with proper lock management.
    """

    def __init__(self, database_path: Path | str, schema: str = "staging") -> None:
        """Initialize the data store.

        Args:
            database_path: Path to DuckDB database file
            schema: Schema name for tables (default: staging)

        Raises:
            ValueError: If schema name is invalid
        """
        _validate_identifier(schema, "schema name")

        self.database_path = Path(database_path)
        self.schema = schema

        # Ensure parent directory exists
        if self.database_path.parent != Path("."):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database and schema
        with self.connect() as conn:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")

        logger.info(
            "data_store_initialized",
            database=str(database_path),
            schema=schema,
        )

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get a DuckDB connection.

        Creates a new connection to the database file. Safe for concurrent
        use as each connection is independent.

        Returns:
            DuckDB connection object
        """
        return duckdb.connect(str(self.database_path))

    def write_table(
        self,
        name: str,
        records: Iterable[Mapping],
        *,
        mode: str = "replace",
    ) -> None:
        """Write records to a table.

        Args:
            name: Table name (alphanumeric and underscores only)
            records: Records to write
            mode: Write mode - 'replace' or 'append'

        Raises:
            ValueError: If table name is invalid or mode is unsupported
            RuntimeError: If database operation fails
        """
        _validate_identifier(name, "table name")

        if mode not in ("replace", "append"):
            raise ValueError(f"Invalid mode: '{mode}'. Must be 'replace' or 'append'")

        frame = pl.DataFrame(records)
        if frame.is_empty():
            logger.warning("no_data_to_write", table=name)
            return

        quoted_table = f'"{self.schema}"."{name}"'

        try:
            with self.connect() as conn:
                # Register the polars dataframe with a unique name to avoid collisions
                view_name = f"_tmp_pl_frame_{id(frame)}"
                conn.register(view_name, frame)

                try:
                    if mode == "replace":
                        conn.execute(f"DROP TABLE IF EXISTS {quoted_table}")
                        conn.execute(
                            f"CREATE TABLE {quoted_table} AS SELECT * FROM {view_name}"
                        )
                    else:  # append
                        # Create table if it doesn't exist
                        conn.execute(
                            f"CREATE TABLE IF NOT EXISTS {quoted_table} AS SELECT * FROM {view_name} LIMIT 0"
                        )
                        # Append data
                        conn.execute(
                            f"INSERT INTO {quoted_table} SELECT * FROM {view_name}"
                        )
                finally:
                    # Clean up the temporary view
                    conn.unregister(view_name)

            logger.info(
                "table_written",
                table=name,
                mode=mode,
                rows=len(frame),
            )

        except Exception as e:
            logger.error(
                "table_write_failed",
                table=name,
                mode=mode,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(
                f"Failed to write table '{name}' in mode '{mode}': {e}"
            ) from e
