"""_oai_set maps arXiv categories to OAI-PMH setSpecs.

Regression guard for the harvest bug: a dotted ``set=cs.LG`` is rejected by arXiv OAI-PMH
(``badArgument: Set does not exist``, HTTP 200 → 0 records). Valid sets use the colon
hierarchy ``<archive>:<archive>:<CATEGORY>`` (verified against oaipmh.arxiv.org).
"""

from docsuri_ingestion.adapters.arxiv import _oai_set, parse_oai_records


def test_dotted_category_maps_to_colon_setspec():
    assert _oai_set("cs.LG") == "cs:cs:LG"
    assert _oai_set("cs.AI") == "cs:cs:AI"
    assert _oai_set("cs.CL") == "cs:cs:CL"
    assert _oai_set("cs.CV") == "cs:cs:CV"
    assert _oai_set("stat.ML") == "stat:stat:ML"


def test_archive_only_category_passes_through():
    assert _oai_set("cs") == "cs"


# Minimal real-shape OAI-PMH ListRecords envelope: one valid record (nested <authors>) +
# one malformed record (missing <abstract>) that must be skipped, not fatal.
_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
 <ListRecords>
  <record><metadata>
   <arXiv xmlns="http://arxiv.org/OAI/arXiv/">
    <id>2202.09848</id>
    <created>2025-12-11</created>
    <updated>2025-12-15</updated>
    <authors>
     <author><keyname>Nikoloutsopoulos</keyname><forenames>Sotirios</forenames></author>
     <author><keyname>Titsias</keyname><forenames>Michalis K.</forenames></author>
    </authors>
    <title>Personalized Federated Learning</title>
    <categories>cs.LG cs.AI</categories>
    <abstract>We propose an SGD-type algorithm.</abstract>
   </arXiv>
  </metadata></record>
  <record><metadata>
   <arXiv xmlns="http://arxiv.org/OAI/arXiv/">
    <id>9999.00000</id>
    <created>2025-12-11</created>
    <title>No abstract here</title>
    <categories>cs.LG</categories>
   </arXiv>
  </metadata></record>
 </ListRecords>
</OAI-PMH>"""


def test_parse_oai_records_nested_authors_and_skips_malformed():
    records = parse_oai_records(_SAMPLE)
    assert len(records) == 1  # malformed (missing abstract) skipped, harvest not aborted
    r = records[0]
    assert r.arxiv_ref == "2202.09848"
    assert r.authors == ("Sotirios Nikoloutsopoulos", "Michalis K. Titsias")
    assert r.categories == ("cs.LG", "cs.AI")
