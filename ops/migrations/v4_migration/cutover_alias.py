import sys
from opensearchpy import OpenSearch
from docsuri_ingestion.settings import IngestionSettings

def main():
    settings = IngestionSettings.from_env()
    if not settings.opensearch_endpoint:
        print("Missing DOCSURI_OPENSEARCH_ENDPOINT")
        return 1
        
    client = OpenSearch(
        hosts=[settings.opensearch_endpoint],
        use_ssl=False, verify_certs=False
    )
    alias_name = "docsuri-corpus"
    v1_index = settings.opensearch_index
    v2_index = settings.opensearch_index_v2
    
    actions = [
        {"remove": {"index": v1_index, "alias": alias_name}},
        {"add": {"index": v2_index, "alias": alias_name}}
    ]
    
    try:
        client.indices.update_aliases(body={"actions": actions})
        print(f"Successfully swapped {alias_name} from {v1_index} to {v2_index}")
    except Exception as e:
        print(f"Failed to cutover: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
