"""テスト共通のフィクスチャ。公式 STEP の読み込みは重いので、セッションで 1 回だけ行う。"""

from __future__ import annotations

from pathlib import Path

import cadquery as cq
import pytest

STEP = Path(__file__).resolve().parent.parent / "vendor" / "UltraArm_P340_3D_230918.stp"


@pytest.fixture(scope="session")
def step_solids() -> list[cq.Solid]:
    if not STEP.exists():
        pytest.skip(f"公式 STEP がない: {STEP}（README の手順で vendor/ に置く）")
    return cq.importers.importStep(str(STEP)).solids().vals()


@pytest.fixture(scope="session")
def receiver_measured(step_solids):
    from inspect_step import measure_receiver

    return measure_receiver(step_solids)


@pytest.fixture(scope="session")
def receiver_solid(step_solids, receiver_measured) -> cq.Solid:
    return step_solids[receiver_measured.solid_index]
