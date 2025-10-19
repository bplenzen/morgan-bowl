# Learning Log: SQL Injection Prevention

**Date**: October 19, 2025
**Topic**: Secure Database Queries with Parameterized Statements
**Effort**: ~1 hour
**Status**: ✅ Complete

---

## 🎯 Learning Objectives

1. Understand what SQL injection is and why it's dangerous
2. Learn how parameterized queries prevent SQL injection
3. Implement secure queries in Python with DuckDB
4. Write tests to verify security fixes

---

## 📚 The Problem: SQL Injection

### What is SQL Injection?

SQL injection is a security vulnerability where an attacker can inject malicious SQL code into your queries by manipulating user input.

### Vulnerable Code (BEFORE)

```python
# ❌ DANGEROUS - Using f-string to interpolate user input
week = request.get('week')  # Could be "1; DROP TABLE users; --"
matchups = conn.execute(f"""
    SELECT * FROM fct_matchups
    WHERE week = {week}
""").df()
```

**Why it's dangerous**:

- The `week` variable is directly inserted into the SQL string
- Attacker can inject any SQL they want
- No validation or escaping happens

**Example Attack**:

```python
week = "1; DROP TABLE fct_matchups; --"

# Results in this SQL being executed:
# SELECT * FROM fct_matchups WHERE week = 1; DROP TABLE fct_matchups; --
#                                           ^^^^^^^^^^^^^^^^^^^^^^^^
#                                           Malicious code executed!
```

---

## ✅ The Solution: Parameterized Queries

### Secure Code (AFTER)

```python
# ✅ SAFE - Using parameterized query
week = request.get('week')  # Even if malicious, can't inject SQL
matchups = conn.execute("""
    SELECT * FROM fct_matchups
    WHERE week = ?
""", [week]).df()
```

**Why it's safe**:

1. SQL structure is **fixed** - can't be modified by input
2. Parameters are **validated** by the database
3. Special characters are **automatically escaped**
4. Type checking happens **before execution**

**Same Attack Attempt**:

```python
week = "1; DROP TABLE fct_matchups; --"

# DuckDB tries to convert the string to INTEGER for the week column
# Fails with: "Conversion Error: Could not convert string to INT"
# The malicious SQL is never executed! ✅
```

---

## 🔧 Implementation Details

### DuckDB Parameterized Query Syntax

```python
# Single parameter
result = conn.execute("SELECT * FROM table WHERE id = ?", [123])

# Multiple parameters (order matters!)
result = conn.execute("""
    SELECT * FROM table
    WHERE wins >= ? AND points >= ?
""", [min_wins, min_points])

# Works with any type
result = conn.execute("""
    SELECT * FROM table
    WHERE name = ? AND date >= ?
""", ["Alice", datetime(2025, 1, 1)])
```

### Converting F-Strings to Parameters

**Pattern**: Look for `f"""..."""` or `f"..."`with SQL inside

```python
# BEFORE (vulnerable)
query = f"SELECT * FROM teams WHERE manager = '{manager_name}'"

# AFTER (secure)
query = "SELECT * FROM teams WHERE manager = ?"
params = [manager_name]
result = conn.execute(query, params)
```

---

## 🧪 Testing Strategy

### Test 1: Verify Protection Against Injection

```python
def test_rejects_sql_injection():
    malicious = "1; DROP TABLE users; --"

    # This should FAIL (not execute the DROP)
    with pytest.raises(Exception):
        conn.execute("SELECT * FROM table WHERE id = ?", [malicious])
```

### Test 2: Verify Normal Usage Still Works

```python
def test_parameterized_query_works():
    week = 1
    result = conn.execute("SELECT * FROM fct_matchups WHERE week = ?", [week])
    assert len(result.fetchall()) > 0
```

### Test 3: Type Safety

```python
def test_type_validation():
    # week column is INTEGER, passing a string should fail
    with pytest.raises(Exception):
        conn.execute("SELECT * FROM fct_matchups WHERE week = ?", ["not_a_number"])
```

---

## 📝 Changes Made

### File: `scripts/generate_report.py`

**Before**:

```python
matchups = conn.execute(f"""
    SELECT
        manager_name,
        round(points, 2) as points,
        opponent_manager_name,
        round(opponent_points, 2) as opponent_points,
        win_flag
    FROM main_analytics.fct_matchups
    WHERE week = {week}  # ❌ SQL injection risk
    ORDER BY points DESC
""").df()
```

**After**:

```python
matchups = conn.execute("""
    SELECT
        manager_name,
        round(points, 2) as points,
        opponent_manager_name,
        round(opponent_points, 2) as opponent_points,
        win_flag
    FROM main_analytics.fct_matchups
    WHERE week = ?  # ✅ Parameterized query
    ORDER BY points DESC
""", [week]).df()  # ✅ Pass week as parameter
```

### Files Created

- `tests/test_sql_injection.py` - Educational tests demonstrating the vulnerability
- `tests/test_generate_report_secure.py` - Integration tests for the fix

---

## 🎓 Key Takeaways

### What I Learned

1. **SQL Injection is Real**: Even small apps need to protect against it
2. **Parameterized Queries are Simple**: Just use `?` placeholders and pass parameters separately
3. **Database Type Checking**: DuckDB validates parameter types automatically
4. **Test-Driven Development**: Write tests first to prove the vulnerability, then fix it
5. **Defense in Depth**: Multiple layers of protection (type hints + parameterized queries + validation)

### Best Practices

✅ **DO**:

- Use parameterized queries for ALL external input (users, APIs, files)
- Let the database handle escaping and validation
- Write tests to verify security fixes
- Add comments explaining security measures

❌ **DON'T**:

- Use f-strings or string concatenation for SQL with external data
- Trust any input without validation
- Assume "only trusted users" will access your code
- Skip security because "it's just a small project"

### Modern DataOps Principles Applied

1. **Security by Default**: Treat all input as untrusted
2. **Fail Fast**: Database type checking catches bad input early
3. **Testability**: Write tests that prove security works
4. **Documentation**: Explain WHY code is written a certain way

---

## 🔄 What's Next

1. ✅ SQL injection vulnerability fixed
2. ⏭️ Next: Add error handling to dashboard.py (defensive programming)
3. ⏭️ Then: Parameterize hardcoded league size (configuration management)
4. ⏭️ Then: Auto-detect season year (dynamic configuration)

---

## 📚 Additional Resources

- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [DuckDB Parameter Binding](https://duckdb.org/docs/api/python/dbapi.html#parameterized-queries)
- [Bobby Tables: A Guide to Preventing SQL Injection](https://bobby-tables.com/)

---

**Lessons Completed**: 1/4 for v1.0.1
**Next Lesson**: Error Handling & Defensive Programming
