from __future__ import annotations

from models.user_signal import UserSignal


def test_post_route_feedback_new_stores_signal(client, db_session) -> None:
    response = client.post(
        "/route-feedback/",
        json={"route_id": "route-1", "rating": 5, "source": "web"},
    )

    assert response.status_code == 200, response.text
    signal = db_session.query(UserSignal).filter(UserSignal.entity_id == "route-1").one()
    assert signal.signal_type == "route_feedback"
    assert signal.entity_type == "route"
    assert signal.payload["rating"] == 5
    assert signal.dedup_key


def test_post_route_feedback_new_validates_rating(client, db_session) -> None:
    response = client.post(
        "/route-feedback/",
        json={"route_id": "route-1", "rating": 6},
    )

    assert response.status_code == 422
    assert db_session.query(UserSignal).count() == 0


def test_route_feedback_with_a_real_client_user_id_uses_it_for_dedup_new(client, db_session) -> None:
    """Defect #9 fix: a caller-supplied identity (e.g. a real Telegram
    user id) must be used as the dedup subject, never collapsed into a
    shared "anonymous" constant."""
    response = client.post(
        "/route-feedback/",
        json={"route_id": "route-1", "rating": 5, "user_id": "telegram-user-42"},
    )
    assert response.status_code == 200, response.text
    signal = db_session.query(UserSignal).filter(UserSignal.entity_id == "route-1").one()
    assert signal.user_id == "telegram-user-42"


def test_two_anonymous_callers_with_no_identity_never_suppress_each_others_feedback_new(client, db_session) -> None:
    """Defect #9 fix (the core regression): two independent anonymous
    submissions (no user_id, no anonymous session header) for the exact
    same route/rating must both be stored as independent signals -- the
    old shared "anonymous" constant would have deduplicated the second
    one away as if it were the first caller's repeat submission."""
    first = client.post("/route-feedback/", json={"route_id": "route-1", "rating": 4})
    second = client.post("/route-feedback/", json={"route_id": "route-1", "rating": 4})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    signals = db_session.query(UserSignal).filter(UserSignal.entity_id == "route-1").all()
    assert len(signals) == 2
    assert signals[0].user_id != signals[1].user_id


def test_repeated_submission_from_the_same_anonymous_session_header_is_deduplicated_new(client, db_session) -> None:
    """The anonymous-identity branch of _dedup_subject (used when a client
    sends X-Anonymous-Session but no user_id) must dedupe repeats from the
    SAME anonymous session, while test_two_anonymous_callers_... above
    proves two DIFFERENT anonymous sessions never collide. Together these
    prove the anonymous_subject branch is symmetric with the user_id
    branch, not just an inert fallback."""
    headers = {"X-Anonymous-Session": "a-stable-anonymous-session-token-1234"}
    payload = {"route_id": "route-1", "rating": 3, "comment": "same anon comment"}

    first = client.post("/route-feedback/", json=payload, headers=headers)
    second = client.post("/route-feedback/", json=payload, headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    signals = db_session.query(UserSignal).filter(UserSignal.entity_id == "route-1").all()
    assert len(signals) == 1
    assert signals[0].user_id.startswith("anon:")

    other_session_headers = {"X-Anonymous-Session": "a-totally-different-anonymous-session-5678"}
    third = client.post("/route-feedback/", json=payload, headers=other_session_headers)
    assert third.status_code == 200, third.text
    signals_after = db_session.query(UserSignal).filter(UserSignal.entity_id == "route-1").all()
    assert len(signals_after) == 2
    assert signals_after[0].user_id != signals_after[1].user_id


def test_repeated_submission_from_the_same_identity_is_deduplicated_new(client, db_session) -> None:
    """Defect #10 (paired with #9): the SAME identity submitting the
    exact same feedback twice within the same fixed dedup bucket (see
    routers/route_feedback.py::_dedup_key) must be deduplicated -- this
    proves dedup still works once identity is fixed, it is not simply
    disabled. Both requests here run back-to-back and land in the same
    bucket; this does not exercise the boundary-straddling case."""
    payload = {"route_id": "route-1", "rating": 3, "user_id": "stable-user-1", "comment": "same comment"}
    first = client.post("/route-feedback/", json=payload)
    second = client.post("/route-feedback/", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    signals = db_session.query(UserSignal).filter(UserSignal.entity_id == "route-1", UserSignal.user_id == "stable-user-1").all()
    assert len(signals) == 1


def test_concurrent_duplicate_submissions_from_the_same_identity_produce_one_row_new(db_session) -> None:
    """Defect #10 fix: the dedup boundary must be enforced atomically at
    the database level (a unique index + INSERT ... ON CONFLICT DO
    NOTHING), not via a check-then-insert read followed by a write. This
    proves the SAME dedup_key can be targeted by two separate INSERT
    statements without raising an IntegrityError and without producing a
    second row -- the exact guarantee a real concurrent race relies on
    (a check-then-insert implementation would either raise on the second
    INSERT's unique-constraint violation, or -- without a constraint at
    all, as before this fix -- silently insert a duplicate row)."""
    from datetime import datetime

    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    from routers.route_feedback import _dedup_key, _dedup_subject

    subject = _dedup_subject(None, "race-user")
    now = datetime.utcnow()
    signal_payload = {
        "rating": 5,
        "comment": None,
        "source": "web",
        "liked_place_ids": [],
        "disliked_place_ids": [],
        "skipped_place_ids": [],
        "problem_types": [],
    }
    dedup_key = _dedup_key(subject=subject, route_id="route-race", signal_payload=signal_payload, now=now)

    values = {
        "user_id": subject,
        "signal_type": "route_feedback",
        "entity_type": "route",
        "entity_id": "route-race",
        "payload": signal_payload,
        "dedup_key": dedup_key,
        "created_at": now,
    }

    for _ in range(2):
        statement = sqlite_insert(UserSignal).values(**values).on_conflict_do_nothing(
            index_elements=[UserSignal.dedup_key]
        )
        db_session.execute(statement)
        db_session.commit()

    rows = db_session.query(UserSignal).filter(UserSignal.dedup_key == dedup_key).all()
    assert len(rows) == 1
