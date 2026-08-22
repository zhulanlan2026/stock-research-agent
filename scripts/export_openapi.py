import json
from pathlib import Path

from stock_research.main import app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packages" / "shared-contracts" / "openapi" / "openapi.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
