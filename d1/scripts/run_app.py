from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nifty200_pipeline.util import add_venv_site_packages  # noqa: E402

add_venv_site_packages(PROJECT_ROOT)

from nifty200_pipeline.pipeline import build_final_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Nifty 200 historical weekly panel.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    outputs = build_final_dataset(Path(args.project_root))
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
