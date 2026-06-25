"""Alembic structural invariants."""
import unittest
from pathlib import Path

def _script():
 from alembic.config import Config
 from alembic.script import ScriptDirectory
 root=Path(__file__).resolve().parent.parent
 return ScriptDirectory.from_config(Config(str(root/"alembic.ini")))

class TestAlembicSingleHead(unittest.TestCase):
 def test_exactly_one_head(self):self.assertEqual(len(_script().get_heads()),1)
 def test_known_head_revision(self):self.assertIn("a6c1d8e9f304",_script().get_heads())
 def test_exactly_one_base(self):self.assertEqual(len([r.revision for r in _script().walk_revisions() if r.down_revision is None]),1)
 def test_known_base_revision(self):self.assertIn("e48f13974bc8",[r.revision for r in _script().walk_revisions() if r.down_revision is None])
 def test_total_revision_count(self):self.assertEqual(sum(1 for _ in _script().walk_revisions()),49)
 def test_env_metadata_covers_all_tables(self):
  from db.base import Base
  import models  # noqa: F401
  expected={"places","cities","routes","route_places","route_sessions","route_session_points","route_drafts","route_draft_points","city_start_points","admin_audit_logs","place_verifications","place_images","telegram_user_contexts","user_signals","categories","tags","import_job_steps","place_field_confidence","place_photo_candidates","review_queue_items","bot_sessions","bot_events","taxonomy_mappings","taxonomy_conflicts","taxonomy_decisions","quality_rules","quality_issues","taxonomy_bulk_batches","workflow_operations","known_missing_poi"}
  self.assertEqual(expected-set(Base.metadata.tables),set())
