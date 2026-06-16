"""U2 orchestration service (domain core). Never calls grounding ``enforce`` (INV-1) —
the gateway seam (``discovery.api``) applies the injected hook between
``plan_and_retrieve`` and ``finalize``."""
