"""Diagnostic-only entrypoint until a verified device adapter is installed."""

import argparse
from pathlib import Path

import uvicorn

from zeromerma_api.core.runtime_secrets import read_private_secret
from zeromerma_api.local_hardware.runtime import LocalHardwareBridge
from zeromerma_api.local_hardware.server import create_bridge_app


def main() -> None:
    parser = argparse.ArgumentParser(description="ZeroMerma local hardware bridge diagnostics")
    parser.add_argument("--pairing-key-file", type=Path, required=True)
    parser.add_argument("--spool", type=Path, required=True)
    parser.add_argument("--pos-origin", required=True)
    parser.add_argument("--port", type=int, default=17651)
    args = parser.parse_args()
    # Empty registry is intentional: no device is supported merely because it
    # resembles a protocol. Production requires a certified adapter registration.
    key = bytes.fromhex(read_private_secret(args.pairing_key_file))
    bridge = LocalHardwareBridge(args.spool, key, devices=[])
    try:
        uvicorn.run(
            create_bridge_app(bridge, [args.pos_origin]),
            host="127.0.0.1",
            port=args.port,
            access_log=False,
            log_level="warning",
        )
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
