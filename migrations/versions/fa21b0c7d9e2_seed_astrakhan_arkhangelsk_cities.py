"""seed Astrakhan and Arkhangelsk cities

Revision ID: fa21b0c7d9e2
Revises: f9a2b3c4d5e6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fa21b0c7d9e2"
down_revision: Union[str, None] = "f9a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CITIES: tuple[dict[str, object], ...] = (
    {
        "slug": "astrakhan",
        "name": "Астрахань",
        "region": "Астраханская область",
        "country": "Россия",
        "timezone": "Europe/Astrakhan",
        "center_lat": 46.3497,
        "center_lng": 48.0408,
        "launch_status": "importing",
        "population_tier": "regional_center",
        "expected_places_count": 350,
        "is_active": True,
    },
    {
        "slug": "arkhangelsk",
        "name": "Архангельск",
        "region": "Архангельская область",
        "country": "Россия",
        "timezone": "Europe/Moscow",
        "center_lat": 64.5393,
        "center_lng": 40.5170,
        "launch_status": "importing",
        "population_tier": "regional_center",
        "expected_places_count": 350,
        "is_active": True,
    },
)


def upgrade() -> None:
    conn = op.get_bind()
    for city in _CITIES:
        conn.execute(
            sa.text(
                """
                INSERT INTO cities (
                    slug,
                    name,
                    region,
                    country,
                    timezone,
                    center_lat,
                    center_lng,
                    launch_status,
                    population_tier,
                    expected_places_count,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (
                    :slug,
                    :name,
                    :region,
                    :country,
                    :timezone,
                    :center_lat,
                    :center_lng,
                    :launch_status,
                    :population_tier,
                    :expected_places_count,
                    :is_active,
                    now(),
                    now()
                )
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    region = EXCLUDED.region,
                    country = EXCLUDED.country,
                    timezone = EXCLUDED.timezone,
                    center_lat = EXCLUDED.center_lat,
                    center_lng = EXCLUDED.center_lng,
                    population_tier = EXCLUDED.population_tier,
                    expected_places_count = EXCLUDED.expected_places_count,
                    is_active = EXCLUDED.is_active,
                    updated_at = now()
                """
            ),
            city,
        )


def downgrade() -> None:
    # Keep imported city data on downgrade. These rows may already have places/scopes attached.
    pass
