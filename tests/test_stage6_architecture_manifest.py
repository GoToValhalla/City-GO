from __future__ import annotations

import models  # noqa: F401
import models.admin_read_snapshot  # noqa: F401

from architecture.manifest import ARCHITECTURE_MANIFEST
from db.base import Base


TABLE_TYPES = {"mutable", "append-only", "projection", "reference", "operational"}


def test_manifest_owns_every_declared_table_exactly_once() -> None:
    declared = [row["name"] for row in ARCHITECTURE_MANIFEST["tables"]]

    assert len(declared) == 139
    assert len(declared) == len(set(declared))
    assert set(declared) == set(Base.metadata.tables)


def test_every_table_declares_complete_ownership() -> None:
    contexts = {row["name"] for row in ARCHITECTURE_MANIFEST["contexts"]}

    for table in ARCHITECTURE_MANIFEST["tables"]:
        assert table["owner"] in contexts
        assert table["type"] in TABLE_TYPES
        assert table["writer"].startswith("services.")
        assert table["readers"]
        assert len(table["readers"]) == len(set(table["readers"]))


def test_mutable_tables_have_one_authorized_writer() -> None:
    mutable = [row for row in ARCHITECTURE_MANIFEST["tables"] if row["type"] == "mutable"]

    assert mutable
    assert all(isinstance(row["writer"], str) and row["writer"] for row in mutable)


def test_required_dependency_directions_are_explicit() -> None:
    dependencies = {
        row["name"]: set(row["allowed_dependencies"])
        for row in ARCHITECTURE_MANIFEST["contexts"]
    }

    assert "routing" not in dependencies["search"]
    assert "search" not in dependencies["routing"]
    assert "routing" in dependencies["route_sessions"]
    assert "route_sessions" not in dependencies["routing"]


def test_canonical_writer_invariants_are_explicit() -> None:
    invariants = ARCHITECTURE_MANIFEST["invariants"]

    assert invariants["publication_state_writer"] == "services.publication_state_writer"
    assert invariants["projection_writer"] == "projection_infrastructure"
    assert invariants["open_now_reader"] == "services.open_now_service"
