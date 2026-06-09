from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DocSuri"
    database_url: str | None = None
    local_paper_dir: str = "local_papers"

    llm_provider: Literal["anthropic", "mock"] = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_verifier_model: str = "claude-haiku-4-5-20251001"
    llm_max_tokens: int = 1800
    llm_temperature: float = 0.2

    embedding_provider: Literal["openai", "none"] = "none"
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    retrieval_top_k: int = 8
    retrieval_query_max_chars: int = 6000

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

    @property
    def use_anthropic(self) -> bool:
        return self.llm_provider == "anthropic" and bool(self.anthropic_api_key)

    @property
    def use_embeddings(self) -> bool:
        return self.embedding_provider == "openai" and bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
