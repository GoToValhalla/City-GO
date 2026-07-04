from __future__ import annotations

import json

from db.session import SessionLocal
from scripts.bootstrap_admin_read_models import bootstrap_admin_read_models
from services.admin_read_model_v2 import refresh_all


def main() -> None:
    bootstrap = bootstrap_admin_read_models()
    db = SessionLocal()
    try:
        result = refresh_all(db)
        print(json.dumps({"bootstrap": bootstrap, "refresh": result}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
