import json

from app.main import app


def main() -> None:
    print(json.dumps(app.openapi(), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
