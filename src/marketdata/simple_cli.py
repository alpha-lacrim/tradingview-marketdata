"""Native setup and serving, without Docker, reverse-proxy routing or separate DB roles."""

import argparse
import asyncio
import os

import uvicorn

from marketdata.simple_store import initialize


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "serve"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "init":
        url = os.environ.get("DATABASE_URL")
        if not url:
            parser.error("set DATABASE_URL to a new company PostgreSQL database")
        asyncio.run(initialize(url))
        print("Native market-data tables are ready.")
    else:
        uvicorn.run(
            "marketdata.simple_api:create_app", factory=True, host=args.host, port=args.port
        )


if __name__ == "__main__":
    main()
