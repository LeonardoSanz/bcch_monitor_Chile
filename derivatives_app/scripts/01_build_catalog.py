from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.io.bcch_api import BCCHClient, save_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Baja catálogo oficial BCCh BDE por frecuencia.")
    parser.add_argument("--frequency", nargs="+", default=["MONTHLY", "DAILY"], help="DAILY MONTHLY QUARTERLY ANNUAL")
    parser.add_argument("--out-dir", default="data/catalog")
    args = parser.parse_args()

    client = BCCHClient.from_env()
    paths = save_catalog(client, args.frequency, ROOT / args.out_dir)
    for path in paths:
        print(f"OK -> {path}")


if __name__ == "__main__":
    main()
