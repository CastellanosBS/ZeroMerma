from sqlalchemy import text

from zeromerma_api.db.engine import engine


def main() -> None:
    with engine.connect() as conn:
        value = conn.execute(text("SELECT 1")).scalar_one()
        print(f"DB ok: SELECT 1 -> {value}")


if __name__ == "__main__":
    main()
