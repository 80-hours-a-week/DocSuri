"""Backend modules namespace (deploy unit ①).

Each subpackage is a clean-lane module owned by a track and mounted by the app-shell:

- ``backend.modules.accounts`` — U3 Accounts/Auth (Track 2, @revenantonthemission)
- ``backend.modules.library``  — U4 Library/History (Track 2, @revenantonthemission)
- ``backend.modules.discovery`` — U2 Discovery (Track 3, @kyjness) — note: discovery is a
  self-contained ``docsuri-discovery`` package under ``modules/discovery/src/discovery``,
  imported as the top-level ``discovery`` package, NOT as ``backend.modules.discovery``.

This ``__init__`` is app-shell glue (CODEOWNERS `/backend/`); module code stays in each
module's own lane.
"""

from __future__ import annotations
