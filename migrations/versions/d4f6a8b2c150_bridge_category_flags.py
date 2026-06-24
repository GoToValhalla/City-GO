"""bridge missing category flags

Revision ID: d4f6a8b2c150
Revises: d4e6f8a2c101
"""
from alembic import op
import sqlalchemy as sa
revision="d4f6a8b2c150";down_revision="d4e6f8a2c101";branch_labels=None;depends_on=None
COLUMNS=(("is_route_eligible",sa.Boolean(),True),("is_catalog_visible",sa.Boolean(),True),("is_default_enabled",sa.Boolean(),True),("is_spam_category",sa.Boolean(),False))

def upgrade()->None:
 existing={column["name"] for column in sa.inspect(op.get_bind()).get_columns("categories")}
 with op.batch_alter_table("categories") as batch:
  for name,type_,default in COLUMNS:
   if name not in existing:batch.add_column(sa.Column(name,type_,nullable=False,server_default=sa.true() if default else sa.false()))

def downgrade()->None:
 existing={column["name"] for column in sa.inspect(op.get_bind()).get_columns("categories")}
 with op.batch_alter_table("categories") as batch:
  for name,_,_ in reversed(COLUMNS):
   if name in existing:batch.drop_column(name)
