"""Strict schemas for AI place enrichment candidates."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


DraftDescriptionField = Literal["short_description", "atmosphere", "inside", "best_for"]
DraftDescriptionSkipReason = Literal[
    "INSUFFICIENT_DATA",
    "INFRASTRUCTURE_ONLY",
    "GEOGRAPHICAL_OBJECT",
    "CONTRADICTORY_DATA",
    "ALREADY_ENRICHED",
    "PROMPT_INJECTION_ONLY",
]


class ExtractedFact(BaseModel):
    target_field: DraftDescriptionField
    source_snippet: str = Field(min_length=1, max_length=500)
    used_fact: str = Field(min_length=1, max_length=500)


class AIEnrichmentResult(BaseModel):
    extracted_facts: list[ExtractedFact] = Field(default_factory=list, max_length=16)
    should_skip: bool
    skip_reason: DraftDescriptionSkipReason | None = None
    short_description: str | None = Field(default=None, max_length=220)
    atmosphere: str | None = Field(default=None, max_length=180)
    inside: str | None = Field(default=None, max_length=180)
    best_for: str | None = Field(default=None, max_length=180)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    fact_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_consistency(self) -> "AIEnrichmentResult":
        filled_fields = {
            field
            for field in ("short_description", "atmosphere", "inside", "best_for")
            if getattr(self, field)
        }
        fact_fields = {fact.target_field for fact in self.extracted_facts}
        if self.fact_count < len(self.extracted_facts):
            raise ValueError("fact_count_less_than_extracted_facts")
        if self.should_skip:
            if self.skip_reason is None:
                raise ValueError("skip_reason_required")
            if filled_fields:
                raise ValueError("skipped_result_must_not_have_descriptive_fields")
            return self
        if self.skip_reason is not None:
            raise ValueError("skip_reason_must_be_null_when_not_skipped")
        if not self.short_description:
            raise ValueError("short_description_required")
        if sum(1 for fact in self.extracted_facts if fact.target_field == "short_description") < 2:
            raise ValueError("short_description_requires_two_facts")
        missing_evidence = filled_fields - fact_fields
        if missing_evidence:
            raise ValueError(f"field_without_evidence:{','.join(sorted(missing_evidence))}")
        return self
