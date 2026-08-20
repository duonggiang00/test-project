"""`DemoDataManager._assert_revision` (DATA-DEMO-002).

The manifest field changed from an exact `alembic_head` pin -- which went
stale three migrations after it was last updated, since nothing forced it to
track new heads -- to `minimum_alembic_revision`, checked two ways: the
database must sit at the repository's *actual* current head (computed live
from the Alembic scripts, never trusted from a stored value), and that head
must be reachable from the manifest's minimum revision by walking
`down_revision` with no branch point.

These tests exercise the branch/stale/divergent failure paths directly
against a fake session and a monkeypatched `ScriptDirectory`, rather than
building a real multi-head Alembic history -- constructing a genuine
divergent-heads repository just to test this one guard would be far more
machinery than the guard itself.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.demo_data import loader as loader_module
from app.demo_data.loader import DemoDataManager


class FakeSession:
    """Returns a fixed `alembic_version` value; nothing else is called."""

    def __init__(self, current_revision: str | None):
        self._current_revision = current_revision

    def scalar(self, _statement):
        return self._current_revision


def _fake_revision(revision_id: str, down_revision):
    return SimpleNamespace(down_revision=down_revision)


def _manager(current_revision: str | None, minimum_revision: str = "rev-a"):
    fixture = SimpleNamespace(manifest=SimpleNamespace(minimum_alembic_revision=minimum_revision))
    manager = object.__new__(DemoDataManager)
    manager.fixture = fixture
    manager.session = FakeSession(current_revision)
    manager.storage = None
    return manager


def _patch_script_directory(monkeypatch, *, heads, revisions: dict[str, object]):
    """`revisions` maps a revision id to its `down_revision` (or a tuple for a merge)."""
    fake_script = MagicMock()
    fake_script.get_heads.return_value = heads
    fake_script.get_revision.side_effect = lambda rev_id: _fake_revision(
        rev_id, revisions[rev_id]
    )
    monkeypatch.setattr(
        loader_module.ScriptDirectory, "from_config", lambda _config: fake_script
    )


@pytest.mark.unit
def test_database_at_head_descending_from_minimum_revision_passes(monkeypatch):
    # head -> rev-b -> rev-a (minimum) -> None
    _patch_script_directory(
        monkeypatch,
        heads=["head"],
        revisions={"head": "rev-b", "rev-b": "rev-a", "rev-a": None},
    )
    manager = _manager(current_revision="head", minimum_revision="rev-a")
    manager._assert_revision()  # must not raise


@pytest.mark.unit
def test_minimum_revision_equal_to_head_passes(monkeypatch):
    _patch_script_directory(monkeypatch, heads=["head"], revisions={"head": None})
    manager = _manager(current_revision="head", minimum_revision="head")
    manager._assert_revision()


@pytest.mark.unit
def test_a_stale_database_behind_the_repository_head_is_refused(monkeypatch):
    _patch_script_directory(
        monkeypatch,
        heads=["head"],
        revisions={"head": "rev-a", "rev-a": None},
    )
    manager = _manager(current_revision="rev-a", minimum_revision="rev-a")
    with pytest.raises(loader_module.DemoDataError, match="not the repository's current"):
        manager._assert_revision()


@pytest.mark.unit
def test_a_database_ahead_of_or_off_the_known_head_is_refused(monkeypatch):
    """Equally a mismatch even if `current` is not literally 'behind'."""
    _patch_script_directory(
        monkeypatch,
        heads=["head"],
        revisions={"head": None},
    )
    manager = _manager(current_revision="some-other-branch-tip")
    with pytest.raises(loader_module.DemoDataError, match="not the repository's current"):
        manager._assert_revision()


@pytest.mark.unit
def test_diverged_repository_history_is_refused_before_checking_the_database(monkeypatch):
    """Two heads in the scripts directory means the repo's own history is
    broken; refuse before even comparing against the database's revision."""
    _patch_script_directory(monkeypatch, heads=["head-a", "head-b"], revisions={})
    manager = _manager(current_revision="head-a")
    with pytest.raises(loader_module.DemoDataError, match="diverged heads"):
        manager._assert_revision()


@pytest.mark.unit
def test_a_minimum_revision_that_is_not_an_ancestor_of_head_is_refused(monkeypatch):
    _patch_script_directory(
        monkeypatch,
        heads=["head"],
        revisions={"head": "rev-b", "rev-b": None},
    )
    manager = _manager(current_revision="head", minimum_revision="rev-never-reached")
    with pytest.raises(loader_module.DemoDataError, match="is not an ancestor of"):
        manager._assert_revision()


@pytest.mark.unit
def test_a_merge_point_between_head_and_the_minimum_revision_is_refused(monkeypatch):
    """A branch/merge point makes the fixture's compatibility with the
    post-merge side unproven, so the walk refuses rather than picking a
    side to trust."""
    _patch_script_directory(
        monkeypatch,
        heads=["head"],
        revisions={"head": ("rev-a", "rev-b")},
    )
    manager = _manager(current_revision="head", minimum_revision="rev-a")
    with pytest.raises(loader_module.DemoDataError, match="multiple parents"):
        manager._assert_revision()
