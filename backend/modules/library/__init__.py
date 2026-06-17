"""U4 Library module — saved searches, personal library, search history (owner-private).

Track 2 (@revenantonthemission), deploy unit ① (the modular-monolith backend). Synchronous CRUD
+ an at-least-once history event consumer. Mounted by the app-shell (``backend/wiring.py``) with
the mock-first in-memory adapters by default; the SQL adapters swap in for production.
"""

__version__ = "0.1.0"
