"""_oai_set maps arXiv categories to OAI-PMH setSpecs.

Regression guard for the harvest bug: a dotted ``set=cs.LG`` is rejected by arXiv OAI-PMH
(``badArgument: Set does not exist``, HTTP 200 → 0 records). Valid sets use the colon
hierarchy ``<archive>:<archive>:<CATEGORY>`` (verified against oaipmh.arxiv.org).
"""

from docsuri_ingestion.adapters.arxiv import _oai_set


def test_dotted_category_maps_to_colon_setspec():
    assert _oai_set("cs.LG") == "cs:cs:LG"
    assert _oai_set("cs.AI") == "cs:cs:AI"
    assert _oai_set("cs.CL") == "cs:cs:CL"
    assert _oai_set("cs.CV") == "cs:cs:CV"
    assert _oai_set("stat.ML") == "stat:stat:ML"


def test_archive_only_category_passes_through():
    assert _oai_set("cs") == "cs"
