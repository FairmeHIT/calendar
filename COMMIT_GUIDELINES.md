# Commit Guidelines

This project uses a simple, repeatable commit process to reduce mistakes.

## 1) Scope Rules

- Commit only files related to the current task.
- Do not commit local runtime artifacts:
  - `.venv/`
  - `__pycache__/`
  - `*.db`
  - `logs/`
- If there are unrelated changes, split commits or stash them first.

## 2) Commit Message Template

Use Conventional Commit style:

```text
<type>(<scope>): <short summary>
```

Examples:

- `feat(calendar): add drag-and-drop rescheduling`
- `fix(ui): correct day-cell hover state`
- `docs(readme): update startup instructions`

Recommended types:

- `feat` new feature
- `fix` bug fix
- `refactor` internal code change without behavior change
- `style` visual/style-only updates
- `docs` documentation updates
- `chore` maintenance/config

## 3) Pre-Push Checklist

Run in `personal-calendar`:

```bash
git status --short
python3 -m py_compile app.py
git log --oneline -n 3
```

Then verify remote and push:

```bash
git remote -v
git push origin main
```

## 4) Authentication Note

If push fails with credential errors:

- Prefer GitHub PAT (repo scope) with HTTPS, or
- Use SSH remote with a registered SSH key.

## 5) Safe Push Policy

- Normal case: `git push origin main`
- Use force push only when history rewrite is intentional and confirmed:
  - `git push --force-with-lease origin main`
