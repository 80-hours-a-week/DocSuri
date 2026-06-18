#!/usr/bin/env python3
"""Sync aidlc-docs user stories -> GitHub issues. Idempotent upsert keyed by US-id title prefix.

Run from the repo root:
    python3 aidlc-docs/scripts/sync_stories_to_issues.py            # dry-run: print plan, touch nothing
    python3 aidlc-docs/scripts/sync_stories_to_issues.py --apply    # create/update issues via gh

aidlc-docs is the SSOT; issues mirror it one-way. Re-run safe: matches existing issues by
'US-XX' title prefix, so editing a story + re-running --apply refreshes its issue in place.
Requires the `gh` CLI authenticated against the target repo (inferred from cwd).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

DOC = Path("aidlc-docs/inception/user-stories/stories.md")
STORY_LABEL = "type:story"
EPIC_RE = re.compile(r"^## (에픽 .+)$")
STORY_RE = re.compile(r"^### (US-[A-Z]+\d+)\s*—\s*(.+?)\s*$")
ID_RE = re.compile(r"^(US-[A-Z]+\d+)\b")  # match issue title -> story id


def parse_stories(text):
    """Yield dicts: {id, title, epic, body}. Body = lines under the ### heading."""
    stories, epic, cur = [], "", None
    for line in text.splitlines():
        if m := EPIC_RE.match(line):
            epic = m.group(1)
            continue
        if m := STORY_RE.match(line):
            cur = {"id": m.group(1),
                   "title": re.sub(r"\s*\*\(.*?\)\*\s*$", "", m.group(2)),
                   "epic": epic, "body_lines": []}
            stories.append(cur)
            continue
        if line.startswith("## ") or line.strip() == "---":
            cur = None  # left the story block
            continue
        if cur is not None:
            cur["body_lines"].append(line)
    for s in stories:
        s["body"] = "\n".join(s.pop("body_lines")).strip()
    return stories


def issue_title(s):
    return f"{s['id']} — {s['title']}"


def issue_body(s):
    return (f"{s['body']}\n\n---\n"
            f"**Epic**: {s['epic']}\n"
            f"**Source**: `{DOC}`\n"
            f"<!-- aidlc:{s['id']} -->\n")


def gh(*args, capture=True):
    return subprocess.run(["gh", *args], check=True, text=True,
                          capture_output=capture).stdout


def existing_issues():
    """Map story-id -> issue number, parsed from title prefix."""
    raw = gh("issue", "list", "--state", "all", "--limit", "300",
             "--json", "number,title")
    out = {}
    for it in json.loads(raw):
        if m := ID_RE.match(it["title"]):
            out[m.group(1)] = it["number"]
    return out


def main():
    apply = "--apply" in sys.argv[1:]
    if not DOC.exists():
        sys.exit(f"missing {DOC} — run from repo root")
    stories = parse_stories(DOC.read_text(encoding="utf-8"))
    existing = existing_issues()
    print(f"{len(stories)} stories parsed · {len(existing)} matching issues exist · "
          f"mode={'APPLY' if apply else 'DRY-RUN'}\n")
    for s in stories:
        title, body = issue_title(s), issue_body(s)
        num = existing.get(s["id"])
        action = "UPDATE" if num else "CREATE"
        print(f"  {action:6} {title}  ({s['epic']})" + (f"  -> #{num}" if num else ""))
        if not apply:
            continue
        if num:
            gh("issue", "edit", str(num), "--title", title, "--body", body)
        else:
            url = gh("issue", "create", "--title", title, "--body", body,
                     "--label", STORY_LABEL).strip()
            print(f"         {url}")
    if not apply:
        print("\n(dry-run — re-run with --apply to create/update)")


if __name__ == "__main__":
    main()
