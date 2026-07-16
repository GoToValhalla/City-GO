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
 def test_known_head_revision(self):self.assertIn("a1f3c9d2e4b7",_script().get_heads())
 def test_exactly_one_base(self):self.assertEqual(len([r.revision for r in _script().walk_revisions() if r.down_revision is None]),1)
 def test_known_base_revision(self):self.assertIn("e48f13974bc8",[r.revision for r in _script().walk_revisions() if r.down_revision is None])
 def test_total_revision_count(self):self.assertEqual(sum(1 for _ in _script().walk_revisions()),71)
 def test_env_metadata_covers_all_tables(self):
  from db.base import Base
  import models  # noqa: F401
  expected={"places","cities","routes","route_places","route_sessions","route_session_points","route_drafts","route_draft_points","city_start_points","admin_audit_logs","place_verifications","place_images","telegram_user_contexts","user_signals","categories","tags","import_job_steps","place_field_confidence","place_photo_candidates","review_queue_items","bot_sessions","bot_events","taxonomy_mappings","taxonomy_conflicts","taxonomy_decisions","quality_rules","quality_issues","taxonomy_bulk_batches","workflow_operations","known_missing_poi","data_quality_issues","data_quality_candidates","destinations","destination_scopes","destination_place_memberships","destination_membership_conflicts","destination_data_pipeline_runs","debug_reports"}
  self.assertEqual(expected-set(Base.metadata.tables),set())
 def test_env_metadata_covers_user_foundation_tables(self):
  from db.base import Base
  import models  # noqa: F401
  expected={"users","anonymous_identities","external_identities","telegram_identities","identity_link_events","user_profiles","user_preferences","favorite_places","saved_routes","route_history","reviews","review_votes","place_rating_aggregates","user_photos","user_suggestions","moderation_items","abuse_reports","user_foundation_audit_logs"}
  self.assertEqual(expected-set(Base.metadata.tables),set())
