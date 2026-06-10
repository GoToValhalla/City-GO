"""add city expansion registry and import state

Revision ID: 2b7f6a4d9c10
Revises: c2b8a9e1d4f3
Create Date: 2026-06-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "2b7f6a4d9c10"
down_revision: Union[str, None] = "c2b8a9e1d4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _registry_tables()
    _import_tables()
    _city_columns()
    _telegram_city_column()
    _seed_registry()
    _seed_city_scopes()


def downgrade() -> None:
    op.drop_column("telegram_user_contexts", "selected_city_slug")
    with op.batch_alter_table("cities") as batch_op:
        batch_op.drop_constraint("fk_cities_city_candidate_id_city_candidates", type_="foreignkey")
        batch_op.drop_constraint("fk_cities_region_id_regions", type_="foreignkey")
        batch_op.drop_constraint("fk_cities_country_id_countries", type_="foreignkey")
        batch_op.drop_column("launch_status")
        batch_op.drop_column("bbox")
        batch_op.drop_column("city_candidate_id")
        batch_op.drop_column("region_id")
        batch_op.drop_column("country_id")
    tuple(map(op.drop_table, (
        "place_scope_links", "place_source_presence", "place_discovery_requests",
        "source_observations", "city_scope_import_state", "import_batches",
        "city_import_jobs", "city_import_scopes", "city_candidates", "regions", "countries",
    )))


def _registry_tables() -> None:
    op.create_table("countries", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("code", sa.String(16), nullable=False, unique=True),
                    sa.Column("name", sa.String(255), nullable=False),
                    sa.Column("default_locale", sa.String(32)),
                    sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    op.create_table("regions", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("country_id", sa.Integer(), sa.ForeignKey("countries.id"), nullable=False),
                    sa.Column("code", sa.String(100), nullable=False, unique=True),
                    sa.Column("name", sa.String(255), nullable=False),
                    sa.Column("type", sa.String(64), nullable=False),
                    sa.Column("parent_region_id", sa.Integer(), sa.ForeignKey("regions.id")),
                    sa.Column("source_type", sa.String(64)), sa.Column("source_external_id", sa.String(128)),
                    sa.Column("timezone", sa.String(100)), sa.Column("center_lat", sa.Float()),
                    sa.Column("center_lng", sa.Float()), sa.Column("bbox", sa.JSON()),
                    sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    op.create_table("city_candidates", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("country_id", sa.Integer(), sa.ForeignKey("countries.id"), nullable=False),
                    sa.Column("region_id", sa.Integer(), sa.ForeignKey("regions.id")),
                    sa.Column("name", sa.String(255), nullable=False), sa.Column("normalized_name", sa.String(255), nullable=False),
                    sa.Column("slug", sa.String(100), nullable=False, unique=True), sa.Column("type", sa.String(64), nullable=False),
                    sa.Column("population", sa.Integer()), sa.Column("center_lat", sa.Float()), sa.Column("center_lng", sa.Float()),
                    sa.Column("bbox", sa.JSON()), sa.Column("source_type", sa.String(64)), sa.Column("source_external_id", sa.String(128)),
                    sa.Column("osm_id", sa.String(128)), sa.Column("wikidata_id", sa.String(128)), sa.Column("geonames_id", sa.String(128)),
                    sa.Column("status", sa.String(64), nullable=False), sa.Column("confidence", sa.Float()),
                    sa.Column("city_potential_score", sa.Float()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))


def _import_tables() -> None:
    op.create_table("city_import_scopes", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False), sa.Column("code", sa.String(100), nullable=False),
                    sa.Column("name", sa.String(255), nullable=False), sa.Column("bbox", sa.JSON()), sa.Column("polygon", sa.JSON()),
                    sa.Column("priority", sa.Integer(), nullable=False), sa.Column("status", sa.String(64), nullable=False),
                    sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("import_profile", sa.String(64), nullable=False),
                    sa.Column("coverage_targets", sa.JSON()), sa.Column("refresh_interval_hours", sa.Integer()),
                    sa.Column("last_imported_at", sa.DateTime()), sa.Column("next_run_at", sa.DateTime()), sa.Column("locked_at", sa.DateTime()),
                    sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    op.create_table("city_import_jobs", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
                    sa.Column("scope_id", sa.Integer(), sa.ForeignKey("city_import_scopes.id"), nullable=False),
                    sa.Column("job_type", sa.String(64), nullable=False), sa.Column("status", sa.String(64), nullable=False),
                    sa.Column("scheduled_for", sa.DateTime(), nullable=False), sa.Column("started_at", sa.DateTime()),
                    sa.Column("finished_at", sa.DateTime()), sa.Column("error", sa.String(1000)), sa.Column("created_at", sa.DateTime()))
    op.create_table("import_batches", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
                    sa.Column("scope_id", sa.Integer(), sa.ForeignKey("city_import_scopes.id")), sa.Column("source_type", sa.String(64), nullable=False),
                    sa.Column("mode", sa.String(64), nullable=False), sa.Column("started_at", sa.DateTime()), sa.Column("finished_at", sa.DateTime()),
                    sa.Column("raw_count", sa.Integer()), sa.Column("normalized_count", sa.Integer()), sa.Column("published_count", sa.Integer()),
                    sa.Column("needs_review_count", sa.Integer()), sa.Column("rejected_count", sa.Integer()), sa.Column("duplicate_count", sa.Integer()),
                    sa.Column("errors_count", sa.Integer()), sa.Column("status", sa.String(64), nullable=False), sa.Column("dry_run", sa.Boolean(), nullable=False),
                    sa.Column("diff_summary", sa.JSON()), sa.Column("rollback_available", sa.Boolean(), nullable=False),
                    sa.Column("protected_manual_overrides_count", sa.Integer()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    _audit_tables()


def _audit_tables() -> None:
    op.create_table("city_scope_import_state", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
                    sa.Column("scope_id", sa.Integer(), sa.ForeignKey("city_import_scopes.id"), nullable=False),
                    sa.Column("source_type", sa.String(64), nullable=False), sa.Column("import_profile", sa.String(64), nullable=False),
                    sa.Column("last_successful_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")),
                    sa.Column("last_attempted_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")),
                    sa.Column("last_started_at", sa.DateTime()), sa.Column("last_finished_at", sa.DateTime()),
                    sa.Column("last_status", sa.String(64), nullable=False), sa.Column("last_error", sa.String(1000)),
                    sa.Column("last_raw_count", sa.Integer()), sa.Column("last_normalized_count", sa.Integer()),
                    sa.Column("last_published_count", sa.Integer()), sa.Column("last_needs_review_count", sa.Integer()),
                    sa.Column("last_rejected_count", sa.Integer()), sa.Column("last_duplicate_count", sa.Integer()),
                    sa.Column("last_missing_from_source_count", sa.Integer()), sa.Column("coverage_status", sa.String(64), nullable=False),
                    sa.Column("coverage_score", sa.Float()), sa.Column("next_run_at", sa.DateTime()), sa.Column("created_at", sa.DateTime()),
                    sa.Column("updated_at", sa.DateTime()))
    op.create_table("source_observations", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("import_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id"), nullable=False),
                    sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
                    sa.Column("scope_id", sa.Integer(), sa.ForeignKey("city_import_scopes.id")),
                    sa.Column("source_type", sa.String(64), nullable=False), sa.Column("source_external_id", sa.String(128), nullable=False),
                    sa.Column("source_object_type", sa.String(64)), sa.Column("source_url", sa.String(1000)), sa.Column("raw_name", sa.String(255)),
                    sa.Column("raw_category", sa.String(128)), sa.Column("raw_lat", sa.Float()), sa.Column("raw_lng", sa.Float()),
                    sa.Column("raw_payload", sa.JSON()), sa.Column("payload_hash", sa.String(128), nullable=False), sa.Column("first_seen_at", sa.DateTime()),
                    sa.Column("last_seen_at", sa.DateTime()), sa.Column("seen_in_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")),
                    sa.Column("canonical_place_id", sa.Integer(), sa.ForeignKey("places.id")), sa.Column("match_status", sa.String(64), nullable=False),
                    sa.Column("normalization_status", sa.String(64), nullable=False), sa.Column("rejection_reason", sa.String(128)),
                    sa.Column("confidence", sa.Float()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    _place_support_tables()


def _place_support_tables() -> None:
    op.create_table("place_discovery_requests", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False), sa.Column("scope_id", sa.Integer(), sa.ForeignKey("city_import_scopes.id")),
                    sa.Column("submitted_by_user_id", sa.String(128)), sa.Column("submitted_by_telegram_user_id", sa.BigInteger()),
                    sa.Column("submitted_by_anonymous_user_id", sa.String(128)), sa.Column("submitted_by_role", sa.String(64)),
                    sa.Column("source_type", sa.String(64), nullable=False), sa.Column("source_payload", sa.JSON()), sa.Column("name", sa.String(255), nullable=False),
                    sa.Column("address", sa.String(500)), sa.Column("lat", sa.Float()), sa.Column("lng", sa.Float()), sa.Column("category_hint", sa.String(128)),
                    sa.Column("description", sa.String(1000)), sa.Column("website", sa.String(1000)), sa.Column("phone", sa.String(64)),
                    sa.Column("status", sa.String(64), nullable=False), sa.Column("confidence", sa.Float()),
                    sa.Column("duplicate_place_id", sa.Integer(), sa.ForeignKey("places.id")), sa.Column("review_notes", sa.String(1000)),
                    sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.Column("reviewed_at", sa.DateTime()))
    op.create_table("place_source_presence", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id")), sa.Column("source_observation_id", sa.Integer(), sa.ForeignKey("source_observations.id")),
                    sa.Column("source_type", sa.String(64), nullable=False), sa.Column("source_external_id", sa.String(128), nullable=False),
                    sa.Column("first_seen_at", sa.DateTime()), sa.Column("last_seen_at", sa.DateTime()), sa.Column("last_seen_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")),
                    sa.Column("consecutive_missing_count", sa.Integer(), nullable=False), sa.Column("last_missing_at", sa.DateTime()),
                    sa.Column("presence_status", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    op.create_table("place_scope_links", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=False),
                    sa.Column("scope_id", sa.Integer(), sa.ForeignKey("city_import_scopes.id"), nullable=False),
                    sa.Column("relation_type", sa.String(64), nullable=False), sa.Column("first_seen_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")),
                    sa.Column("last_seen_batch_id", sa.Integer(), sa.ForeignKey("import_batches.id")), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))


def _city_columns() -> None:
    with op.batch_alter_table("cities") as batch_op:
        batch_op.add_column(sa.Column("country_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("region_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("city_candidate_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("bbox", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("launch_status", sa.String(64), nullable=False, server_default="published"),
        )
        batch_op.create_foreign_key(
            "fk_cities_country_id_countries",
            "countries",
            ["country_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_cities_region_id_regions",
            "regions",
            ["region_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_cities_city_candidate_id_city_candidates",
            "city_candidates",
            ["city_candidate_id"],
            ["id"],
        )


def _telegram_city_column() -> None:
    op.add_column("telegram_user_contexts", sa.Column("selected_city_slug", sa.String(100), nullable=True))


def _seed_registry() -> None:
    op.execute("INSERT INTO countries (code, name, default_locale, created_at, updated_at) VALUES "
               "('RU','Россия','ru',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),('GE','Грузия','ka',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),('AM','Армения','hy',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
    op.execute("INSERT INTO regions (country_id, code, name, type, timezone, created_at, updated_at) "
               "SELECT id,'kaliningrad_oblast','Калининградская область','oblast','Europe/Kaliningrad',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM countries WHERE code='RU'")
    op.execute("INSERT INTO regions (country_id, code, name, type, timezone, created_at, updated_at) "
               "SELECT id,'khanty_mansi_autonomous_okrug_yugra','Ханты-Мансийский автономный округ — Югра','autonomous_okrug','Asia/Yekaterinburg',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM countries WHERE code='RU'")
    op.execute("INSERT INTO regions (country_id, code, name, type, timezone, created_at, updated_at) "
               "SELECT id,'imereti','Имерети','region','Asia/Tbilisi',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM countries WHERE code='GE'")
    op.execute("INSERT INTO regions (country_id, code, name, type, timezone, created_at, updated_at) "
               "SELECT id,'yerevan','Ереван','capital','Asia/Yerevan',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM countries WHERE code='AM'")
    _seed_cities()


def _seed_cities() -> None:
    _seed_candidates()
    op.execute("UPDATE cities SET country_id=(SELECT id FROM countries WHERE code='RU'), "
               "region_id=(SELECT id FROM regions WHERE code='kaliningrad_oblast'), "
               "city_candidate_id=(SELECT id FROM city_candidates WHERE slug='zelenogradsk'), "
               "region='Калининградская область', country='Россия', timezone='Europe/Kaliningrad', "
               "launch_status='published' WHERE slug='zelenogradsk'")
    op.execute("INSERT INTO cities (slug,name,region,country,timezone,center_lat,center_lng,is_active,launch_status,created_at,updated_at,country_id,region_id) "
               "SELECT 'kutaisi','Кутаиси','Имерети','Грузия','Asia/Tbilisi',42.2676,42.7180,true,'draft',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,c.id,r.id FROM countries c, regions r "
               "WHERE c.code='GE' AND r.code='imereti'")
    op.execute("INSERT INTO cities (slug,name,region,country,timezone,center_lat,center_lng,is_active,launch_status,created_at,updated_at,country_id,region_id) "
               "SELECT 'yerevan','Ереван','Ереван','Армения','Asia/Yerevan',40.1792,44.4991,true,'draft',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,c.id,r.id FROM countries c, regions r "
               "WHERE c.code='AM' AND r.code='yerevan'")
    op.execute("INSERT INTO cities (slug,name,region,country,timezone,center_lat,center_lng,is_active,launch_status,created_at,updated_at,country_id,region_id) "
               "SELECT 'khanty-mansiysk','Ханты-Мансийск','ХМАО-Югра','Россия','Asia/Yekaterinburg',61.0042,69.0019,true,'draft',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,c.id,r.id FROM countries c, regions r "
               "WHERE c.code='RU' AND r.code='khanty_mansi_autonomous_okrug_yugra'")
    op.execute("UPDATE cities SET city_candidate_id=(SELECT id FROM city_candidates WHERE city_candidates.slug=cities.slug) "
               "WHERE slug IN ('kutaisi','yerevan','khanty-mansiysk')")


def _seed_candidates() -> None:
    rows = (
        ("zelenogradsk", "Зеленоградск", "zelenogradsk", "RU", "kaliningrad_oblast", "published", 54.96, 20.48),
        ("kutaisi", "Кутаиси", "kutaisi", "GE", "imereti", "candidate", 42.2676, 42.7180),
        ("yerevan", "Ереван", "yerevan", "AM", "yerevan", "candidate", 40.1792, 44.4991),
        ("khanty-mansiysk", "Ханты-Мансийск", "khanty-mansiysk", "RU", "khanty_mansi_autonomous_okrug_yugra", "candidate", 61.0042, 69.0019),
    )
    tuple(map(lambda row: _insert_candidate(*row), rows))


def _insert_candidate(slug: str, name: str, normalized: str, country: str, region: str,
                      status: str, lat: float, lng: float) -> None:
    op.execute("INSERT INTO city_candidates "
               "(country_id,region_id,name,normalized_name,slug,type,status,center_lat,center_lng,created_at,updated_at) "
               f"SELECT c.id,r.id,'{name}','{normalized}','{slug}','city','{status}',{lat},{lng},CURRENT_TIMESTAMP,CURRENT_TIMESTAMP "
               f"FROM countries c, regions r WHERE c.code='{country}' AND r.code='{region}'")


def _seed_city_scopes() -> None:
    scopes = {"zelenogradsk": "tourist_core,center,seafront,food_area,parks,useful_services",
              "kutaisi": "tourist_core,center,old_town,food_area,parks,transport_hubs,useful_services",
              "yerevan": "tourist_core,center,cascade_opera_republic_square,kond_old_district,food_area,parks,transport_hubs,useful_services",
              "khanty-mansiysk": "tourist_core,center,riverfront,culture,parks,food_area,transport_hubs,useful_services"}
    tuple(map(lambda item: _insert_scopes(item[0], item[1].split(",")), scopes.items()))


def _insert_scopes(city_slug: str, codes: list[str]) -> None:
    tuple(map(lambda code: op.execute(
        "INSERT INTO city_import_scopes (city_id, code, name, priority, status, enabled, import_profile, created_at, updated_at) "
        f"SELECT id, '{code}', '{code}', 100, 'draft', false, 'tourist_core', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM cities WHERE slug='{city_slug}'"
    ), codes))
