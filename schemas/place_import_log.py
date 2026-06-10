from pydantic import BaseModel


class PlaceImportLogSummary(BaseModel):
    total_imports: int = 0
    total_created: int = 0
    total_updated: int = 0
    total_invalid: int = 0
    dry_run_count: int = 0
    last_import_at: str | None = None
