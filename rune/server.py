from __future__ import annotations

import argparse

from .adapters.ollama import OllamaModel
from .api import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RUNE local API")
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--db", default="data/rune.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    from .runtime import RUNERuntime

    serve(
        host=args.host,
        port=args.port,
        runtime=RUNERuntime(OllamaModel(model=args.model), db_path=args.db),
    )


if __name__ == "__main__":
    main()
