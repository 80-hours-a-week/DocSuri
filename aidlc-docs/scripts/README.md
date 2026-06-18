# aidlc-docs scripts

Tooling that mirrors the AI-DLC source of truth (`aidlc-docs/`) into GitHub.
**One-way: aidlc-docs is the SSOT, GitHub mirrors it.** Don't hand-edit issues
expecting them to flow back — edit the docs and re-sync.

## `sync_stories_to_issues.py`

Upserts one GitHub issue per user story in
`aidlc-docs/inception/user-stories/stories.md`. Idempotent: matches existing
issues by the `US-XX` title prefix, so it updates in place instead of
duplicating. **Create/update only — it never closes issues** (closing a shipped
story is a human call).

```bash
# from the repo root
python3 aidlc-docs/scripts/sync_stories_to_issues.py            # dry-run (preview)
python3 aidlc-docs/scripts/sync_stories_to_issues.py --apply    # create/update via gh
```

Runs automatically via `.github/workflows/sync-stories.yml` on any push to
`develop` that touches `stories.md`, plus a manual **Run workflow** button.

Not handled by the script (deliberately, one-time human calls): closing issues
for shipped stories, board status, and `unit:*` labels.
