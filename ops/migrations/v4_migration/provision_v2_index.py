import sys
from opensearchpy import OpenSearch
from docsuri_ingestion.settings import IngestionSettings
from docsuri_shared.vector_spec import DIMENSIONS

INDEX_BODY = {
    "settings": {"index": {"knn": True}},
    "mappings": {
        "properties": {
            "chunkId": {"type": "keyword"},
            "paperId": {"type": "keyword"},
            "version": {"type": "integer"},
            "vector": {
                "type": "knn_vector",
                "dimension": DIMENSIONS,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "lucene",
                },
            },
            "section": {"type": "keyword"},
            "lexicalTerms": {"type": "text"},
            "title": {"type": "text"},
            "authors": {"type": "keyword"},
            "year": {"type": "integer"},
            "arxivId": {"type": "keyword"},
            "abstract": {"type": "text"},
            "abstractSnippet": {"type": "text"},
            "arxivUrl": {"type": "keyword"},
            "categories": {"type": "keyword"},
        }
    },
}

def main():
    settings = IngestionSettings.from_env()
    if not settings.opensearch_endpoint:
        print("Missing DOCSURI_OPENSEARCH_ENDPOINT")
        return 1
        
    client = OpenSearch(
        hosts=[settings.opensearch_endpoint],
        use_ssl=False, verify_certs=False
    )
    v2_index = settings.opensearch_index_v2
    
    if not client.indices.exists(index=v2_index):
        client.indices.create(index=v2_index, body=INDEX_BODY)
        print(f"Created {v2_index}")
    else:
        print(f"{v2_index} already exists")
    return 0

if __name__ == "__main__":
    sys.exit(main())
