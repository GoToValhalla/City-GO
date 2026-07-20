from services.ai_dictionaries import INTENT_KEYWORDS
from services.ai_service import PUBLIC_AI_INTENTS, process_ai_query


def test_registered_public_ai_intents_are_explicitly_classified_new() -> None:
    assert set(INTENT_KEYWORDS) <= set(PUBLIC_AI_INTENTS)
    assert set(PUBLIC_AI_INTENTS) == {
        "place_detail", "places_filtered", "collections", "routes", "open_now", "nearby",
    }
    assert all(item.public_reader for item in PUBLIC_AI_INTENTS.values())
    assert all(item.publication_gate for item in PUBLIC_AI_INTENTS.values())
    assert all(item.returned_schema for item in PUBLIC_AI_INTENTS.values())


def test_unknown_ai_intent_fails_closed_new(db_session) -> None:
    result = process_ai_query("совершенно неизвестный сценарий", db_session)
    assert result["status"] == "rejected"
    assert result["results"] == []


def test_public_ai_classification_forbids_admin_fields_new() -> None:
    forbidden = {"is_active", "is_published", "internal_status", "publication_status"}
    assert all(forbidden.isdisjoint(item.returned_schema) for item in PUBLIC_AI_INTENTS.values())
