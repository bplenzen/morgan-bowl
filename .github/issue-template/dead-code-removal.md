---

### `.github/ISSUE_TEMPLATE/dead-code-removal.md`

```md
---
name: Dead / Deprecated Code Removal
about: Remove unused modules, functions, flags, and dependencies safely
labels: refactor, cleanup
---

## Candidate(s) for Removal

- File/symbol(s):
- How identified: vulture/deptry/grep

## Evidence of Unused

- Search results (paste):
- Last reference (if any):

## Risk & Rollback

- Risk assessment:
- Rollback plan:

## Tasks

- [ ] Remove symbols/paths
- [ ] Update imports
- [ ] Delete/adjust tests
- [ ] Run static analysis (vulture/deptry)
- [ ] Full test/dbt build passes

## Validation Commands

```bash
vulture morgan_bowl tests
deptry .
pytest -q --maxfail=1
cd dbt_morgan_bowl && dbt build --fail-fast
