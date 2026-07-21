"""Alembic structural invariants."""
import ast
import unittest
from collections import defaultdict
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _script():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(Config(str(_root() / "alembic.ini")))


def _declared_revision_ids() -> dict[str, list[str]]:
    declared: dict[str, list[str]] = defaultdict(list)
    versions_dir = _root() / "migrations" / "versions"
    for path in sorted(versions_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            target = node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else getattr(node, "target", None)
            value = node.value
            if isinstance(target, ast.Name) and target.id == "revision" and isinstance(value, ast.Constant) and isinstance(value.value, str):
                declared[value.value].append(path.name)
                break
    return dict(declared)


class TestAlembicSingleHead(unittest.TestCase):
    def test_revision_ids_are_unique(self):
        duplicates = {
            revision: filenames
            for revision, filenames in _declared_revision_ids().items()
            if len(filenames) > 1
        }
        self.assertEqual(duplicates, {})

    def test_exactly_one_head(self):
        self.assertEqual(len(_script().get_heads()), 1)

    def test_known_head_revision(self):
        self.assertIn("d3f8a1c6b4e9", _script().get_heads())

    def test_exactly_one_base(self):
        bases = [revision.revision for revision in _script().walk_revisions() if revision.down_revision is None]
        self.assertEqual(len(bases), 1)

    def test_known_base_revision(self):
        bases = [revision.revision for revision in _script().walk_revisions() if revision.down_revision is None]
        self.assertIn("e48f13974bc8", bases)

    def test_total_revision_count(self):
        self.assertEqual(sum(1 for _ in _script().walk_revisions()), 85)

    def test_env_metadata_covers_all_tables(self):
        from db.base import Base
        import models  # noqa: F401

        expected = {
            "places", "cities", "routes", "route_places", "route_sessions",
            "route_session_points", "route_drafts", "route_draft_points",
            "city_start_points", "admin_audit_logs", "place_verifications",
            "place_images", "telegram_user_contexts", "user_signals", "categories",
            "tags", "import_job_steps", "place_field_confidence",
            "place_photo_candidates", "review_queue_items", "bot_sessions",
            "bot_events", "taxonomy_mappings", "taxonomy_conflicts",
            "taxonomy_decisions", "quality_rules", "quality_issues",
            "taxonomy_bulk_batches", "workflow_operations", "known_missing_poi",
            "data_quality_issues", "data_quality_candidates", "destinations",
            "destination_scopes", "destination_place_memberships",
            "destination_membership_conflicts", "destination_data_pipeline_runs",
            "debug_reports",
        }
        self.assertEqual(expected - set(Base.metadata.tables), set())

    def test_env_metadata_covers_user_foundation_tables(self):
        from db.base import Base
        import models  # noqa: F401

        expected = {
            "users", "anonymous_identities", "external_identities",
            "telegram_identities", "identity_link_events", "user_profiles",
            "user_preferences", "favorite_places", "saved_routes", "route_history",
            "reviews", "review_votes", "place_rating_aggregates", "user_photos",
            "user_suggestions", "moderation_items", "abuse_reports",
            "user_foundation_audit_logs",
        }
        self.assertEqual(expected - set(Base.metadata.tables), set())
