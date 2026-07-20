from pathlib import Path

import yaml


COMPOSE = Path(__file__).parents[1] / "docker-compose.yml"


def test_compose_security_contract_new() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    config = yaml.safe_load(text)
    services = config["services"]
    password = services["db"]["environment"]["POSTGRES_PASSWORD"]
    healthcheck = " ".join(services["backend"]["healthcheck"]["test"])
    migrate_command = " ".join(services["migrate"]["command"])

    assert password == "${POSTGRES_PASSWORD}"
    assert "DELETE" not in migrate_command.upper()
    assert "alembic_version" not in migrate_command
    assert "/ready" in healthcheck
    assert "/health" not in healthcheck
