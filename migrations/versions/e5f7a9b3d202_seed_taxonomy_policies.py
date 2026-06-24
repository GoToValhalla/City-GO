"""seed taxonomy policies

Revision ID: e5f7a9b3d202
Revises: d4e6f8a2c101
"""
from alembic import op

revision="e5f7a9b3d202"
down_revision="d4e6f8a2c101"
branch_labels=None
depends_on=None

MAPPINGS=(
 ("osm","amenity","pharmacy","pharmacy",300,0.99),("osm","shop","mall","shopping_mall",300,0.99),
 ("osm","amenity","bank","bank",300,0.99),("osm","amenity","atm","atm",300,0.99),
 ("osm","tourism","museum","museum",300,0.99),("osm","leisure","park","park",300,0.98),
 ("osm","amenity","cafe","coffee",200,0.72),("legacy","legacy_category","services","service",100,0.70),
)

def upgrade()->None:
 op.execute("UPDATE categories SET route_policy='always_allowed' WHERE code IN ('museum','attraction','walk','park','beach')")
 op.execute("UPDATE categories SET route_policy='allowed_by_context' WHERE code IN ('coffee','food','bar','shopping_mall')")
 op.execute("UPDATE categories SET route_policy='useful_only', is_route_eligible=0 WHERE code IN ('pharmacy','bank','atm','parking','transport','bus_stop','toilets','information')")
 op.execute("UPDATE categories SET route_policy='forbidden', is_route_eligible=0 WHERE code IN ('hospital','police','shelter')")
 op.execute("UPDATE categories SET route_policy='manual_review', is_route_eligible=0 WHERE code IN ('service','unknown')")
 for source,key,value,target,priority,confidence in MAPPINGS:
  op.execute(f"INSERT INTO taxonomy_mappings (source,source_key,source_value,target_category_id,priority,confidence,active,conditions,conditions_hash,fallback,comment,created_by,created_at,updated_at) SELECT '{source}','{key}','{value}',id,{priority},{confidence},1,'{{}}','seed-{source}-{key}-{value}',0,'Базовое сопоставление City GO','migration',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP FROM categories WHERE code='{target}' AND NOT EXISTS (SELECT 1 FROM taxonomy_mappings WHERE source='{source}' AND source_key='{key}' AND source_value='{value}')")

def downgrade()->None:
 op.execute("DELETE FROM taxonomy_mappings WHERE created_by='migration' AND comment='Базовое сопоставление City GO'")
