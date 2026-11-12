"""アダプタ全体の形状。差し込み部、梁、ホルダー取り付け面を一体で造形する。

受け口基準の座標系（`cad.params` の説明を参照）で組み立てる。
- 差し込み部: `cad.insert` と同じもの。本体の前面は X = 前面 + すきま + 本体の厚さ
- 梁: 本体の前面から前方へ伸びる底板。底面は差し込み部の底面とそろえる
- ホルダー取り付け面: 梁の先端に立つ鉛直の板。1/4 インチのねじ穴は X 方向に貫通する
- 三角リブ: 梁と取り付け面の角を左右で補強する。取り付け面の上端まで届かせ、
  積層をまたいで曲げを受ける取り付け面を支える。中央はつまみねじを回す指のために空ける
- 内側の角の丸め: 梁と本体、梁と取り付け面の角に入れ、応力の集中を和らげる

部品全体の底面が 1 つの平面にそろうので、そのまま造形面に置いて印刷できる。
"""

from __future__ import annotations

import cadquery as cq

from cad.insert import insert
from cad.params import PARAMS, RECEIVER, Params, Receiver


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def body_front_x(p: Params = PARAMS, r: Receiver = RECEIVER) -> float:
    """差し込み部の本体の前面の X 座標。梁はここから始まる。"""
    return r.front_face_x + p.fit_clearance + p.body_thickness


def mount_plate_x(p: Params = PARAMS, r: Receiver = RECEIVER) -> tuple[float, float]:
    """ホルダー取り付け面の後面と前面の X 座標。"""
    x0 = body_front_x(p, r) + p.beam_length
    return x0, x0 + p.mount_plate_thickness


def screw_axis(p: Params = PARAMS, r: Receiver = RECEIVER) -> tuple[float, float, float]:
    """ねじ穴の中心（取り付け面の前面上）。ホルダーはここに付く。"""
    z0 = -r.pocket_depth
    return mount_plate_x(p, r)[1], 0.0, z0 + p.screw_hole_height


def adapter(p: Params = PARAMS, r: Receiver = RECEIVER) -> cq.Workplane:
    z0 = -r.pocket_depth
    bx = body_front_x(p, r)
    mx0, mx1 = mount_plate_x(p, r)
    hb = p.body_width / 2
    hm = p.mount_plate_width / 2

    beam = _box(bx - 0.5, mx0 + 0.5, -hb, hb, z0, z0 + p.beam_thickness)
    plate = _box(mx0, mx1, -hm, hm, z0, z0 + p.mount_plate_height)

    # 三角リブ: XZ 平面の直角三角形を Y 方向に押し出し、左右の縁に置く。
    g = p.gusset_size
    zt = z0 + p.beam_thickness
    tri = (
        cq.Workplane("XZ")
        .polyline([(mx0 + 0.5, zt - 0.5), (mx0 - g, zt - 0.5), (mx0 + 0.5, zt + p.gusset_height)])
        .close()
        .extrude(p.gusset_thickness)  # XZ 平面の押し出しは -Y 方向
    )
    gussets = tri.translate((0, hm, 0)).union(tri.translate((0, -hm + p.gusset_thickness, 0)))

    sx, _, sz = screw_axis(p, r)
    hole = (
        cq.Workplane("YZ", origin=(mx0 - 1, 0, sz))
        .circle(p.screw_hole_diameter / 2)
        .extrude(p.mount_plate_thickness + 2)
    )

    hw = min(hb, hm)
    fillets = _inner_fillet(bx, zt, +1, p.fillet_radius, hw).union(
        _inner_fillet(mx0, zt, -1, p.fillet_radius, hw)
    )

    return insert(p, r).union(beam).union(plate).union(gussets).union(fillets).cut(hole)


def _inner_fillet(x: float, z: float, sign: int, radius: float, half_width: float) -> cq.Workplane:
    """鉛直の面（X = x）と梁の上面（Z = z）がなす内側の角を埋める丸め。

    sign は角が開いている向きで、+1 なら面の前方（+X）、-1 なら後方に丸めを置く。
    """
    x0, x1 = (x, x + radius) if sign > 0 else (x - radius, x)
    block = _box(x0, x1, -half_width, half_width, z - 0.01, z + radius)
    cx = x + sign * radius
    cut = (
        cq.Workplane("XZ", origin=(0, half_width + 1, 0))
        .center(cx, z + radius)
        .circle(radius)
        .extrude(2 * half_width + 2)
    )
    return block.cut(cut)
