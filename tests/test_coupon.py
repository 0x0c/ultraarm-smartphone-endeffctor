"""試験片（差し込み部）の形状と、公式 STEP の受け口との干渉を確かめる。"""

from __future__ import annotations

from dataclasses import replace

import cadquery as cq
import pytest

from cad.coupon import coupon
from cad.params import PARAMS, RECEIVER

# 干渉とみなす体積の下限（mm^3）
INTERFERENCE_TOL = 1e-3
# 舌片の底は縦穴の底に接触させている。共有面はブーリアン演算の誤差で厚さゼロの
# 薄片として残るので、どの方向の厚さもこの値（mm）未満のものは接触とみなす。
CONTACT_THICKNESS = 0.01


def _as_solid(wp: cq.Workplane) -> cq.Shape:
    return wp.val()


def _interference(part: cq.Shape, receiver: cq.Solid) -> float:
    placed = part.moved(RECEIVER.to_step_location())
    total = 0.0
    for s in placed.intersect(receiver).Solids():
        b = s.BoundingBox()
        if min(b.xlen, b.ylen, b.zlen) >= CONTACT_THICKNESS:
            total += s.Volume()
    return total


def test_coupon_is_single_valid_solid():
    shape = _as_solid(coupon())
    assert shape.isValid()
    assert len(shape.Solids()) == 1


def test_coupon_sits_flat_on_bed():
    """底面が 1 つの高さにそろい、そのまま造形面に置ける。"""
    bb = _as_solid(coupon()).BoundingBox()
    assert bb.zmin == pytest.approx(-RECEIVER.pocket_depth, abs=1e-6)


def test_receiver_params_match_step(receiver_measured):
    """params.py に書いた受け口の寸法が、STEP からの計測値と一致する。"""
    m, r = receiver_measured, RECEIVER
    assert m.pocket_width == pytest.approx(r.pocket_width, abs=0.01)
    assert m.pocket_length == pytest.approx(r.pocket_length, abs=0.01)
    assert m.pocket_depth == pytest.approx(r.pocket_depth, abs=0.01)
    assert m.front_wall_thickness == pytest.approx(r.front_wall_thickness, abs=0.01)
    assert m.notch_width == pytest.approx(r.notch_width, abs=0.01)
    cx = (m.pocket_x[0] + m.pocket_x[1]) / 2
    cy = (m.pocket_y[0] + m.pocket_y[1]) / 2
    assert (cx, cy, m.top_z) == pytest.approx(r.step_origin, abs=0.01)


def test_coupon_does_not_interfere_with_receiver(receiver_solid):
    assert _interference(_as_solid(coupon()), receiver_solid) < INTERFERENCE_TOL


def test_interference_check_detects_overlap(receiver_solid):
    """すきまを負にした試験片は干渉と判定される（検査が干渉を見逃さないことの確認）。"""
    tight = replace(PARAMS, fit_clearance=-0.2)
    assert _interference(_as_solid(coupon(tight)), receiver_solid) > 1.0


def test_tongue_reaches_pocket_floor(receiver_solid):
    """舌片の底が縦穴の底に届き、磁石の真上に鋼製ピンが来る。"""
    placed = _as_solid(coupon()).moved(RECEIVER.to_step_location())
    bb = placed.BoundingBox()
    floor_z = RECEIVER.step_origin[2] - RECEIVER.pocket_depth
    assert bb.zmin == pytest.approx(floor_z, abs=1e-6)
