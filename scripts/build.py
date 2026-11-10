"""印刷用の STL と確認用の STEP を build/ に書き出す。

使い方:
    uv run python scripts/build.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cadquery as cq  # noqa: E402

from cad.coupon import coupon  # noqa: E402

PARTS = {
    "coupon": coupon,
}


def main() -> int:
    out = ROOT / "build"
    out.mkdir(exist_ok=True)
    for name, make in PARTS.items():
        wp = make()
        for ext in ("stl", "step"):
            path = out / f"{name}.{ext}"
            cq.exporters.export(wp, str(path))
            print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
