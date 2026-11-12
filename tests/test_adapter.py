"""アダプタ全体の形状、公式 STEP との干渉、印刷のしやすさを確かめる。"""

from __future__ import annotations

import cadquery as cq
import pytest

from cad.adapter import adapter, body_front_x, mount_plate_x, screw_axis
from cad.params import PARAMS, RECEIVER

INTERFERENCE_TOL = 1e-3
CONTACT_THICKNESS = 0.01  # 接触面に残る厚さゼロの薄片は干渉とみなさない（test_coupon と同じ）
BUILD_VOLUME = 200.0  # 一般的な FDM プリンタの造形範囲（mm 角）


@pytest.fixture(scope="module")
def shape() -> cq.Shape:
    return adapter().val()


def _interference(part: cq.Shape, other: cq.Shape) -> float:
    total = 0.0
    for s in part.intersect(other).Solids():
        b = s.BoundingBox()
        if min(b.xlen, b.ylen, b.zlen) >= CONTACT_THICKNESS:
            total += s.Volume()
    return total


def _placed(shape: cq.Shape, lift: float = 0.0) -> cq.Shape:
    return shape.moved(RECEIVER.to_step_location() * cq.Location(cq.Vector(0, 0, lift)))


def test_adapter_is_single_valid_solid(shape):
    assert shape.isValid()
    assert len(shape.Solids()) == 1


def test_adapter_fits_build_volume(shape):
    bb = shape.BoundingBox()
    assert max(bb.xlen, bb.ylen, bb.zlen) < BUILD_VOLUME


def test_adapter_sits_flat_on_bed(shape):
    """底面が 1 つの高さにそろい、支えなしで造形面に置ける。"""
    bb = shape.BoundingBox()
    z0 = -RECEIVER.pocket_depth
    assert bb.zmin == pytest.approx(z0, abs=1e-6)
    bottom = [f for f in shape.Faces() if f.geomType() == "PLANE"
              and f.normalAt().z < -0.999 and abs(f.Center().z - z0) < 1e-6]
    assert sum(f.Area() for f in bottom) > 0.5 * bb.xlen * bb.ylen


def test_adapter_does_not_interfere_with_receiver(shape, receiver_solid):
    assert _interference(_placed(shape), receiver_solid) < INTERFERENCE_TOL


def test_adapter_does_not_interfere_with_arm(shape, step_solids, receiver_measured):
    """STEP の姿勢で、受け口以外のアームの部品（前腕、平行リンクなど）とも干渉しない。"""
    placed = _placed(shape)
    hits = {
        i: v for i, s in enumerate(step_solids)
        if i != receiver_measured.solid_index and (v := _interference(placed, s)) >= INTERFERENCE_TOL
    }
    assert hits == {}


@pytest.mark.parametrize("lift", [2.0, 6.0, 10.0, 14.0, 18.0, 22.0])
def test_adapter_can_be_lifted_straight_out(shape, receiver_solid, lift):
    """真上に持ち上げる途中のどの高さでも受け口に引っかからない（装着と取り外しの経路）。"""
    assert _interference(_placed(shape, lift), receiver_solid) < INTERFERENCE_TOL


def test_screw_hole_goes_through_mount_plate(shape):
    """ねじ穴が取り付け面を前後に貫通している。"""
    x0, x1 = mount_plate_x()
    _, y, z = screw_axis()
    probe = cq.Solid.makeCylinder(PARAMS.screw_hole_diameter / 2 - 0.05, x1 - x0 + 2,
                                  cq.Vector(x0 - 1, y, z), cq.Vector(1, 0, 0))
    assert _interference(shape, probe) < INTERFERENCE_TOL


def test_screw_hole_has_wall_around_it():
    """ねじ穴のまわりに、取り付け面の縁まで 3 mm 以上の肉が残る。"""
    _, _, z = screw_axis()
    r = PARAMS.screw_hole_diameter / 2
    z0 = -RECEIVER.pocket_depth
    top = z0 + PARAMS.mount_plate_height
    bottom = z0 + PARAMS.beam_thickness
    assert top - (z + r) >= 3.0
    assert (z - r) - bottom >= 3.0
    assert PARAMS.mount_plate_width / 2 - r >= 3.0


def _section_area(shape: cq.Shape, z: float, t: float = 0.02) -> float:
    slab = cq.Solid.makeBox(400, 400, t, cq.Vector(-200, -200, z))
    return shape.intersect(slab).Volume() / t


def test_ribs_support_mount_plate_at_screw_height(shape):
    """三角リブがねじ穴の高さまで届き、積層をまたいで曲げを受ける取り付け面を支える。"""
    _, _, z = screw_axis()
    plate_only = (PARAMS.mount_plate_width - PARAMS.screw_hole_diameter) * PARAMS.mount_plate_thickness
    assert _section_area(shape, z) > 1.1 * plate_only


def test_ribs_leave_room_for_screw_head():
    """左右のリブの間に、つまみねじの頭（D リングで直径 20 程度）を回す幅が残る。"""
    assert PARAMS.mount_plate_width - 2 * PARAMS.gusset_thickness >= 22.0


@pytest.mark.parametrize("corner", ["body", "plate"])
def test_inner_corners_are_filleted(shape, corner):
    """梁と本体、梁と取り付け面の内側の角が丸めで埋まっている。"""
    zt = -RECEIVER.pocket_depth + PARAMS.beam_thickness
    rad = PARAMS.fillet_radius
    x, sign = (body_front_x(), 1) if corner == "body" else (mount_plate_x()[0], -1)
    near = cq.Vector(x + sign * 0.15 * rad, 0, zt + 0.15 * rad)
    far = cq.Vector(x + sign * 0.95 * rad, 0, zt + 0.95 * rad)
    assert shape.isInside(near)
    assert not shape.isInside(far)
