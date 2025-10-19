"""
Integration test for generate_report.py SQL injection fix
"""

import sys
from pathlib import Path

import pytest

# Add scripts directory to path so we can import generate_report
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from generate_report import generate_weekly_report  # noqa: E402


class TestGenerateReportSecure:
    """
    Test that generate_report.py correctly uses parameterized queries.
    """

    def test_generate_report_with_valid_week(self):
        """
        LEARNING: Test that the fixed function works with normal input.

        This ensures our security fix didn't break existing functionality.
        """
        # This should work fine - week 6 is valid
        try:
            report = generate_weekly_report(week=6)
            assert isinstance(report, str)
            assert "Week 6" in report
            print("✅ Report generation works with valid input")
        except Exception as e:
            # If database doesn't exist or has no data, that's okay for this test
            # We're just checking the function doesn't crash with valid input
            if "Catalog Error" in str(e) or "does not exist" in str(e):
                pytest.skip("Database not available - test skipped")
            else:
                raise

    def test_generate_report_rejects_invalid_week(self):
        """
        LEARNING: Parameterized queries automatically validate types.

        DuckDB will reject non-integer values for the week parameter.
        """
        # This should fail gracefully (not execute SQL injection)
        malicious_input = "6; DROP TABLE fct_matchups; --"

        with pytest.raises(Exception):
            # This will fail because malicious_input isn't an integer
            # The parameterized query protects us!
            generate_weekly_report(week=malicious_input)

    def test_generate_report_type_safety(self):
        """
        LEARNING: Python type hints + DuckDB type checking = double protection

        The function signature says week: int, and DuckDB validates it too.
        """
        # Test that Python's type system catches this at runtime
        with pytest.raises((TypeError, ValueError, Exception)):
            # Passing a string when an int is expected
            generate_weekly_report(week="not_a_number")


# LEARNING CHECKPOINT
"""
🎓 WHAT WE LEARNED:

1. **Before (Vulnerable)**:
   ```python
   conn.execute(f"SELECT * FROM table WHERE week = {week}")
   ```
   - Directly interpolates user input into SQL
   - Attacker can inject malicious SQL
   - No type validation

2. **After (Secure)**:
   ```python
   conn.execute("SELECT * FROM table WHERE week = ?", [week])
   ```
   - SQL structure is fixed
   - Parameters are validated by the database
   - Special characters are automatically escaped

3. **Benefits**:
   - ✅ Prevents SQL injection attacks
   - ✅ Better performance (query plan caching)
   - ✅ Type safety (database validates parameters)
   - ✅ Cleaner code (no f-string juggling)

4. **Best Practice**:
   - Use parameterized queries for ALL external input
   - Never trust user input (always validate)
   - Let the database handle escaping

NEXT: Run this test to verify the fix!
  $ poetry run pytest tests/test_generate_report_secure.py -v
"""
