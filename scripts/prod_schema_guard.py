from __future__ import annotations

from sqlalchemy import inspect, text

from db.session import engine


PLACE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("canonical_category", "VARCHAR(100)"),
    ("lifecycle_status", "VARCHAR(32)"),
    ("quality_tier", "VARCHAR(32)"),
    ("quality_score", "INTEGER"),
    ("completeness_score", "INTEGER"),
    ("photo_score", "INTEGER"),
    ("description_score", "INTEGER"),
    ("confidence_score", "INTEGER"),
    ("freshness_score", "INTEGER"),
    ("is_spam_poi", "BOOLEAN"),
    ("is_duplicate_suspected", "BOOLEAN"),
    ("geo_precision", "VARCHAR(32)"),
    ("critical_field_expired", "BOOLEAN"),
    ("existence_confidence_score", "INTEGER"),
    ("existence_confidence_level", "VARCHAR(32)"),
    ("verification_status", "VARCHAR(32)"),
    ("verification_source", "VARCHAR(64)"),
    ("verification_method", "VARCHAR(64)"),
    ("verified_at", "TIMESTAMP"),
    ("verified_by", "VARCHAR(255)"),
    ("needs_recheck_at", "TIMESTAMP"),
    ("verification_comment", "VARCHAR(1000)"),
    ("is_published", "BOOLEAN"),
    ("is_visible_in_catalog", "BOOLEAN"),
    ("is_route_eligible", "BOOLEAN"),
    ("is_searchable", "BOOLEAN"),
    ("publication_status", "VARCHAR(32)"),
    ("publication_comment", "VARCHAR(1000)"),
    ("published_at", "TIMESTAMP"),
    ("unpublished_at", "TIMESTAMP"),
)


def main() -> None:
    inspector = inspect(engine)
    created: list[str] = []
    altered: list[str] = []
    with engine.begin() as connection:
        tables = set(inspector.get_table_names())
        if "feature_toggles" not in tables:
            connection.execute(text("""
                CREATE TABLE feature_toggles (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(128) NOT NULL,
                    scope VARCHAR(32) NOT NULL,
                    scope_id VARCHAR(128),
                    value_bool BOOLEAN NOT NULL DEFAULT FALSE,
                    description VARCHAR(500),
                    updated_by VARCHAR(255),
                    change_reason VARCHAR(1000),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            created.append("feature_toggles")
        if "places" in tables:
            existing = {column["name"] for column in inspector.get_columns("places")}
            for name, ddl_type in PLACE_COLUMNS:
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE places ADD COLUMN "{name}" {ddl_type}'))
                    altered.append(f"places.{name}")
    print({"created": created, "altered": altered})


if __name__ == "__main__":
    main()
