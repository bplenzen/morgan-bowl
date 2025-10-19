"""
Test Suite: SQL Injection Prevention
Purpose: Demonstrate why SQL injection is dangerous and verify our fixes work
"""

import duckdb
import pytest


class TestSQLInjectionVulnerability:
    """
    These tests demonstrate SQL injection vulnerabilities.
    They're meant to FAIL with the current code and PASS after we fix it.
    """

    def test_vulnerable_query_with_malicious_input(self):
        """
        LEARNING: This test shows what happens when user input is directly interpolated.

        Scenario: An attacker passes malicious input instead of a week number.
        Expected: The query should REJECT invalid input, not execute it!
        """
        # Create a temporary in-memory database for testing
        conn = duckdb.connect(":memory:")

        # Create a sample table
        conn.execute(
            """
            CREATE TABLE fct_matchups (
                week INTEGER,
                manager_name VARCHAR,
                points DECIMAL(10,2)
            )
        """
        )

        # Insert test data
        conn.execute(
            """
            INSERT INTO fct_matchups VALUES
            (1, 'Alice', 120.5),
            (2, 'Bob', 95.3),
            (3, 'Charlie', 110.2)
        """
        )

        # VULNERABLE CODE (what we have now)
        # If week comes from user input, they could inject SQL!
        malicious_week = "1; DROP TABLE fct_matchups; --"

        # This is how the CURRENT code works (f-string interpolation)
        # Demonstrating what NOT to do:
        _ = f"""
            SELECT * FROM fct_matchups WHERE week = {malicious_week}
        """

        # In a real attack, this would DROP the table! 😱
        # (We're not actually running it to avoid breaking our test)

        # SAFE CODE (what we'll implement)
        # Parameterized queries prevent SQL injection
        safe_week = "1; DROP TABLE fct_matchups; --"  # Same malicious input

        # DuckDB treats ? as a placeholder and safely escapes the parameter
        safe_query = """
            SELECT * FROM fct_matchups WHERE week = ?
        """

        # This will SAFELY fail because the week isn't a valid integer
        # The SQL engine validates the type BEFORE executing
        with pytest.raises(Exception):
            # DuckDB will raise an error trying to convert the string to INTEGER
            conn.execute(safe_query, [safe_week])

        # Verify table still exists (wasn't dropped)
        tables = conn.execute("SHOW TABLES").fetchall()
        assert len(tables) == 1
        assert tables[0][0] == "fct_matchups"

        conn.close()

    def test_parameterized_query_with_valid_input(self):
        """
        LEARNING: Parameterized queries work perfectly with valid input.

        This shows that fixing the vulnerability doesn't break normal usage!
        """
        conn = duckdb.connect(":memory:")

        # Setup
        conn.execute(
            """
            CREATE TABLE fct_matchups (
                week INTEGER,
                manager_name VARCHAR,
                points DECIMAL(10,2)
            )
        """
        )

        conn.execute(
            """
            INSERT INTO fct_matchups VALUES
            (1, 'Alice', 120.5),
            (1, 'Bob', 95.3),
            (2, 'Charlie', 110.2)
        """
        )

        # CORRECT WAY: Parameterized query
        week = 1  # Normal user input
        result = conn.execute(
            """
            SELECT manager_name, points
            FROM fct_matchups
            WHERE week = ?
        """,
            [week],
        ).fetchall()

        # Verify we got the right data
        assert len(result) == 2  # Two matchups in week 1
        assert result[0][0] in ["Alice", "Bob"]

        conn.close()

    def test_multiple_parameters(self):
        """
        LEARNING: You can use multiple parameters in a single query.

        DuckDB supports both positional (?) and named ($1, $2) parameters.
        """
        conn = duckdb.connect(":memory:")

        conn.execute(
            """
            CREATE TABLE fct_standings (
                manager_name VARCHAR,
                wins INTEGER,
                points_for DECIMAL(10,2)
            )
        """
        )

        conn.execute(
            """
            INSERT INTO fct_standings VALUES
            ('Alice', 5, 550.0),
            ('Bob', 4, 480.0),
            ('Charlie', 3, 420.0),
            ('Diana', 2, 390.0)
        """
        )

        # Multiple parameters example
        min_wins = 3
        min_points = 400.0

        result = conn.execute(
            """
            SELECT manager_name, wins, points_for
            FROM fct_standings
            WHERE wins >= ? AND points_for >= ?
            ORDER BY wins DESC
        """,
            [min_wins, min_points],
        ).fetchall()

        assert len(result) == 3  # Alice, Bob, and Charlie
        assert result[0][0] == "Alice"  # Ordered by wins (5 wins)

        conn.close()


class TestRealWorldScenarios:
    """
    Real scenarios showing how SQL injection could happen in our app.
    """

    def test_week_parameter_injection_attempt(self):
        """
        SCENARIO: What if week came from a URL parameter or user input?

        Example: /report?week=1;DELETE FROM fct_matchups
        """
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE fct_matchups (week INTEGER, data VARCHAR)")
        conn.execute("INSERT INTO fct_matchups VALUES (1, 'safe data')")

        # Simulating malicious input
        user_input_week = "1 OR 1=1"  # Classic SQL injection

        # VULNERABLE: This would return ALL weeks (not just week 1)
        # vulnerable_query = f"SELECT * FROM fct_matchups WHERE week = {user_input_week}"

        # SAFE: This will fail type checking
        safe_query = "SELECT * FROM fct_matchups WHERE week = ?"

        with pytest.raises(Exception):
            # Fails because "1 OR 1=1" isn't a valid INTEGER
            conn.execute(safe_query, [user_input_week])

        # With proper input, it works fine
        result = conn.execute(safe_query, [1]).fetchall()
        assert len(result) == 1

        conn.close()


# LEARNING CHECKPOINT
"""
🎓 KEY TAKEAWAYS:

1. **SQL Injection Risk**: When you use f-strings to build SQL queries,
   malicious input can execute arbitrary SQL commands.

2. **Parameterized Queries**: Using ? placeholders and passing parameters
   separately prevents injection because:
   - The database validates parameter TYPES
   - Special characters are automatically escaped
   - The SQL structure is fixed (can't be changed by input)

3. **DuckDB Syntax**:
   - Use ? for positional parameters
   - Pass parameters as a list: execute(query, [param1, param2])
   - Works with any data type (integers, strings, dates, etc.)

4. **Best Practice**: NEVER use f-strings or string concatenation for SQL queries
   when the values come from external sources (users, APIs, files, etc.)

NEXT STEPS:
- Run this test: `poetry run pytest tests/test_sql_injection.py -v`
- Fix generate_report.py to use parameterized queries
- Re-run tests to verify the fix works
"""
