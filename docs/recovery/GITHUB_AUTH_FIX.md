# GITHUB AUTH FIX

Date: 2026-05-09
Scope: local RC1 release workflow

## Current situation
- `git remote -v` has no configured remote in this repository.
- Push was not attempted because no remote URL exists.

## Safe authentication workflow (without exposing tokens)
1. Configure remote:
   ```bash
   git remote add origin https://github.com/<USER>/<REPO>.git
   ```
2. Authenticate with GitHub CLI (recommended):
   ```bash
   gh auth login
   ```
3. Verify auth:
   ```bash
   gh auth status
   ```
4. Push branch and tags:
   ```bash
   git push -u origin master
   git push origin v0.1.0-rc1-foundation
   ```

## Security notes
- Do not paste tokens in shell history.
- Prefer `gh auth login` or Git credential manager.
- Never commit `.env` real files or secrets.
