import sys
from docsuri_ingestion.settings import IngestionSettings
from docsuri_ingestion.adapters.arxiv import ArxivHttpSource
from docsuri_ingestion.adapters.aws import BedrockCohereEmbeddingPort, OpenSearchVectorIndex
from docsuri_ingestion.processors import FetchParseProcessor, Chunker, IndexRecordAssembler
from docsuri_ingestion.domain.models import EmbeddingBatch, CategoryFilter
from docsuri_ingestion.config import CORPUS_START, CORPUS_END, CORPUS_SLICE_CATEGORIES

def main():
    settings = IngestionSettings.from_env()
    model_id = settings.bedrock_model_id_v2
    index_name = settings.opensearch_index_v2
    if not model_id or not index_name:
        print("Missing DOCSURI_BEDROCK_MODEL_ID_V2 or DOCSURI_OPENSEARCH_INDEX_V2")
        return 1

    arxiv = ArxivHttpSource(timeout_seconds=30.0, rate_limiter=None)
    embedder = BedrockCohereEmbeddingPort(model_id=model_id, region_name=settings.aws_region)
    os_index = OpenSearchVectorIndex(endpoint=settings.opensearch_endpoint or "", index_name=index_name)
    
    parser = FetchParseProcessor()
    chunker = Chunker()
    assembler = IndexRecordAssembler()

    filter_ = CategoryFilter(
        categories=CORPUS_SLICE_CATEGORIES,
        updated_after=CORPUS_START,
        updated_before=CORPUS_END,
    )
    
    count = 0
    for metadata in arxiv.harvest_seed(filter_):
        print(f"Backfilling {metadata.arxiv_ref}...")
        try:
            full_metadata = arxiv.fetch_metadata(metadata.arxiv_ref)
            raw_text = arxiv.fetch_full_text(full_metadata)
            paper = parser.parse(raw_text)
            if paper.withdrawal_detected:
                continue
            
            chunks = chunker.chunk(paper)
            vectors = embedder.embed_documents([c.text for c in chunks.chunks])
            embeddings = EmbeddingBatch(
                chunk_ids=tuple(c.chunk_id for c in chunks.chunks),
                vectors=tuple(tuple(v) for v in vectors),
            )
            batch = assembler.assemble(paper, chunks, embeddings)
            os_index.bulk_upsert(batch)
            count += 1
        except Exception as e:
            print(f"Failed {metadata.arxiv_ref}: {e}")
            
    print(f"Backfill complete: {count} papers processed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
