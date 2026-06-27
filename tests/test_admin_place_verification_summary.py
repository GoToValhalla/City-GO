from datetime import datetime


def test_admin_place_verification_summary_matches_frontend_contract(client, db_session, city_factory, place_factory):
    city = city_factory(slug="summary-city", name="Summary City")
    now = datetime.utcnow()

    needs_recheck = place_factory(
        slug="summary-needs-recheck",
        title="Needs Recheck",
        city_id=city.id,
        category="museum",
    )
    needs_recheck.verification_status = "needs_recheck"
    needs_recheck.existence_confidence_score = 20
    needs_recheck.existence_confidence_level = "low"

    unverified = place_factory(
        slug="summary-unverified",
        title="Unverified",
        city_id=city.id,
        category="park",
    )
    unverified.verification_status = "unverified"
    unverified.existence_confidence_score = 0
    unverified.existence_confidence_level = "unknown"

    verified_today = place_factory(
        slug="summary-verified-today",
        title="Verified Today",
        city_id=city.id,
        category="attraction",
    )
    verified_today.verification_status = "verified"
    verified_today.verified_at = now
    verified_today.existence_confidence_score = 100
    verified_today.existence_confidence_level = "verified"

    db_session.commit()

    response = client.get("/admin/place-verifications/summary", params={"city_slug": city.slug})

    assert response.status_code == 200
    assert response.json() == {
        "queue_total": 2,
        "needs_recheck": 1,
        "unverified": 1,
        "low_confidence": 2,
        "verified_today": 1,
    }
