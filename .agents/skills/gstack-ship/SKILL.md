---
name: gstack-ship
description: Safe PR shipping workflow. Merges the base branch, executes tests, bumps version, generates CHANGELOG, and creates a pull request.
triggers:
  - ship
  - deploy
  - create pull request
  - open pr
---

# Safe PR Shipping Workflow

You are acting as the **Release Engineer**. Your goal is to guide the branch through testing, verification, versioning, documentation updates, and PR creation.

---

## Step 1: Pre-flight Checks
1. **Branch Check**: Run `git branch --show-current`. If on `main` or the default base branch, abort: **"You're on the base branch. Ship from a feature branch."**
2. **Diff Check**: Run `git diff origin/main --stat` (or against base). If there is no diff, abort.
3. **Status Check**: Run `git status` to ensure all intended changes are tracked.

---

## Step 2: Merge Base Branch
Fetch and merge the latest base branch into your feature branch to ensure tests run against the integrated state:
```bash
git fetch origin main && git merge origin/main --no-edit
```
If there are merge conflicts, stop and show them to the user.

---

## Step 3: Test Execution
1. Detect the project's test framework (check `CLAUDE.md`, `package.json`, `Gemfile`, `requirements.txt`, etc.).
2. Run the test suite:
   - For Node: `npm test` or `npm run test`
   - For Rails: `bundle exec rspec` or `rails test`
   - For Python: `pytest`
3. If tests fail, report the failures. Pre-existing failures are noted, but new failures block shipping.

---

## Step 4: Plan Completion Audit
1. Search for active design/plan documents in `.agents/designs/`.
2. Map planned items vs implemented changes in the diff.
3. Report any discrepancies (unimplemented features, untested files).
4. If crucial plan requirements are missing, ask the user whether to proceed anyway or pause and complete them.

---

## Step 5: Version Bump
If the project utilizes semantic versioning:
1. Locate the version file (`package.json`, `Cargo.toml`, or `VERSION` file).
2. Bump the patch version (e.g. `1.0.0` -> `1.0.1`).
3. Commit the change: `git commit -am "chore: bump version to X.Y.Z"`

---

## Step 6: Changelog Update
1. Read `CHANGELOG.md` if it exists.
2. Read the branch's git commits using `git log origin/main..HEAD --oneline`.
3. Format and append a new changelog entry with the date, version, and a list of changes.
4. Commit the change: `git commit -am "docs: update CHANGELOG"`

---

## Step 7: Push and Open PR
1. Run `git push origin [current-branch]`.
2. Check if the `gh` (GitHub CLI) or `glab` (GitLab CLI) is available:
   - **GitHub**: Run `gh pr create --fill` or `gh pr create --title "[PR Title]" --body "[PR Description]"`
   - **GitLab**: Run `glab mr create --fill`
   - **Fallback**: Output the git push link and instructions for the user to create the PR manually on their hosting platform.
3. Output the final PR URL or instructions.
```
SHIP SUCCESSFUL
══════════════════════════════
Branch: [branch]
Version: [version]
PR URL: [URL or manual push instructions]
══════════════════════════════
```
