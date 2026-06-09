from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DocSuri"
    database_url: str

    aws_region: str = "ap-northeast-2"
    aws_profile: str | None = None

    anthropic_model: str = "anthropic.claude-opus-4-6-v1"
    anthropic_verifier_model: str = "anthropic.claude-haiku-4-5-20251001-v1:0"
    llm_max_tokens: int = 1800
    llm_temperature: float = 0.2

    embedding_model: str = "twelvelabs.marengo-embed-3-0-v1:0"
    retrieval_top_k: int = 8
    retrieval_query_max_chars: int = 2000

    paper_table: str = "papers"
    paper_chunk_table: str = "paper_chunks"
    paper_id_column: str = "id"
    paper_chunk_paper_id_column: str = "paper_id"
    paper_chunk_embedding_column: str = "embedding"

    text_columns: tuple[str, ...] = (
        "structured_markdown",
        "full_text",
        "extracted_text",
        "body_text",
        "abstract",
    )
    pdf_columns: tuple[str, ...] = ("pdf_bytes", "pdf", "raw_pdf", "file_bytes")
    title_columns: tuple[str, ...] = ("title", "paper_title", "name")
    chunk_text_columns: tuple[str, ...] = ("chunk_text", "content", "text", "body")
    chunk_anchor_columns: tuple[str, ...] = ("anchor", "section_anchor", "locator")
    chunk_order_columns: tuple[str, ...] = ("chunk_index", "position", "idx", "id")

    @model_validator(mode="after")
    def require_runtime_credentials(self) -> "Settings":
        missing = [
            name
            for name, value in {
                "DATABASE_URL": self.database_url,
                "ANTHROPIC_MODEL": self.anthropic_model,
                "ANTHROPIC_VERIFIER_MODEL": self.anthropic_verifier_model,
                "EMBEDDING_MODEL": self.embedding_model,
            }.items()
            if not value or not value.strip()
        ]
        if missing:
            raise ValueError(f"Missing required runtime settings: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
