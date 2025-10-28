---

### Optional: `.github/ISSUE_TEMPLATE/security-check.md`

```md
---
name: Security & Secrets Scan
about: Proactively check for secrets, unsafe calls, and weak configs
labels: security
---

## Scope

- Areas touched:
- Recent changes:

## Checklist

- [ ] No secrets in code, .env committed, or dbt profiles
- [ ] No `shell=True` or unsafe eval/exec
- [ ] Parameterized SQL used
- [ ] Logs don’t leak sensitive data

## Commands

```bash
poetry export -f requirements.txt -o /tmp/reqs.txt
pip-audit -r /tmp/reqs.txt || true
# or:
poetry export -f requirements.txt | safety check --stdin || true
