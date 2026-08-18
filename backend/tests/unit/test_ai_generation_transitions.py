"""The AI generation state machine's allowlist (AI-002).

`CANONICAL_PROJECT_SPEC.md` §9.2 fixes the legal transitions and states that
"No direct `generated -> published` transition is allowed." These tests pin
the allowlist itself as the thing that enforces that, rather than a guard
somewhere in the publish endpoint: the pair is simply absent, so *every*
caller is refused, including any future one nobody has written yet.

Pure logic, so this is a unit test. The database-level behavior it implies
(locking, concurrent reviewers, no duplicate published rows) is covered by
the PostgreSQL integration suite.
"""

from itertools import product

import pytest

from app.core.exceptions import AppException
from app.models.ai_generation import AI_JOB_STATUSES
from app.services.ai_generation_service import (
    ALLOWED_TRANSITIONS,
    AIGenerationService,
)

ILLEGAL_TRANSITIONS = sorted(
    pair
    for pair in product(AI_JOB_STATUSES, AI_JOB_STATUSES)
    if pair not in ALLOWED_TRANSITIONS
)


@pytest.mark.unit
def test_the_allowlist_is_exactly_the_approved_state_machine():
    assert ALLOWED_TRANSITIONS == frozenset(
        {
            ("requested", "processing"),
            ("requested", "failed"),
            ("processing", "generated"),
            ("processing", "failed"),
            ("generated", "awaiting_review"),
            ("generated", "failed"),
            ("awaiting_review", "approved"),
            ("awaiting_review", "rejected"),
            ("approved", "published"),
        }
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "pair", sorted(ALLOWED_TRANSITIONS), ids=lambda p: f"{p[0]}_to_{p[1]}"
)
def test_every_legal_transition_is_accepted(pair):
    AIGenerationService.assert_transition_allowed(*pair)


@pytest.mark.unit
@pytest.mark.parametrize(
    "pair", ILLEGAL_TRANSITIONS, ids=lambda p: f"{p[0]}_to_{p[1]}"
)
def test_every_other_transition_is_refused(pair):
    with pytest.raises(AppException) as excinfo:
        AIGenerationService.assert_transition_allowed(*pair)
    assert excinfo.value.error_code == "AI_JOB_INVALID_TRANSITION"
    assert excinfo.value.status_code == 409


@pytest.mark.unit
def test_generated_cannot_publish_without_passing_through_review():
    """The single most important refusal, named so a regression is obvious.

    Publishing straight from `generated` would skip approval entirely, which
    is the exact bypass the review state exists to close.
    """
    assert ("generated", "published") not in ALLOWED_TRANSITIONS

    with pytest.raises(AppException) as excinfo:
        AIGenerationService.assert_transition_allowed("generated", "published")
    assert excinfo.value.error_code == "AI_JOB_INVALID_TRANSITION"

    # The only route to `published` is from `approved`.
    published_sources = {
        before for before, after in ALLOWED_TRANSITIONS if after == "published"
    }
    assert published_sources == {"approved"}


@pytest.mark.unit
@pytest.mark.parametrize("status", AI_JOB_STATUSES)
def test_no_status_may_transition_to_itself(status):
    """Blocks re-publish/re-approve at the state machine rather than a guard.

    A second `publish` on an already-published job asks for
    `published -> published`, which is absent, so it is refused without any
    separate "already published" check that could drift out of sync.
    """
    with pytest.raises(AppException) as excinfo:
        AIGenerationService.assert_transition_allowed(status, status)
    assert excinfo.value.error_code == "AI_JOB_INVALID_TRANSITION"


@pytest.mark.unit
@pytest.mark.parametrize("terminal", ["published", "rejected", "failed"])
def test_terminal_states_have_no_outbound_transitions(terminal):
    assert not [pair for pair in ALLOWED_TRANSITIONS if pair[0] == terminal]
