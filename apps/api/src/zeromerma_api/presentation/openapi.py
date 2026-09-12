from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from zeromerma_api.main import create_app


def canonical_openapi_bytes() -> bytes:
    return (json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n").encode("utf-8")


def export_openapi(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_openapi_bytes())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the ZeroMerma OpenAPI schema.")
    parser.add_argument("output", type=Path, help="Path where the OpenAPI JSON file is written.")
    args = parser.parse_args(argv)
    export_openapi(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
