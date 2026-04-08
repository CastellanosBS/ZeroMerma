from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from zeromerma_api.main import create_app


def export_openapi(output_path: Path) -> None:
    app = create_app()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the ZeroMerma OpenAPI schema.")
    parser.add_argument("output", type=Path, help="Path where the OpenAPI JSON file is written.")
    args = parser.parse_args(argv)
    export_openapi(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
