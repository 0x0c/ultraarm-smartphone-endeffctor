"""差し込み部（受け口に差し込む部分）の形状。試験片とアダプタ全体の両方が使う。

差し込み部は 3 つの部分からなる。
- 舌片: 受け口の縦穴に入る板。底面に鋼製ピンを圧入する溝を持つ
- 首: 前壁の切り欠きを通り、舌片と本体をつなぐ
- 本体: 受け口の前面の外側に出る板。アダプタではここから梁が前方へ伸びる

すべて受け口基準の座標系（`cad.params` の説明を参照）で組み立てる。
底面は縦穴の底と同じ高さ（Z = -pocket_depth）にそろえ、そのまま造形面に置いて印刷できるようにする。
"""

from __future__ import annotations

import cadquery as cq

from cad.params import PARAMS, RECEIVER, Params, Receiver


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
        .translate((x0, y0, z0))
    )


def tongue(p: Params = PARAMS, r: Receiver = RECEIVER) -> cq.Workplane:
    c = p.fit_clearance
    hx, hy = r.pocket_width / 2 - c, r.pocket_length / 2 - c
    t = _box(-hx, hx, -hy, hy, -r.pocket_depth, 0.0)
    # 縦穴の鉛直の稜は面取りで埋まっているので、舌片の稜も同じ量だけ面取りして逃がす。
    return t.edges("|Z").chamfer(r.pocket_chamfer)


def neck(p: Params = PARAMS, r: Receiver = RECEIVER) -> cq.Workplane:
    c = p.fit_clearance
    hy = r.notch_width / 2 - c
    # 舌片に食い込ませて一体にし、前面の外側まで通す。
    x0 = r.pocket_width / 2 - c - r.pocket_chamfer
    x1 = r.front_face_x + c
    return _box(x0, x1, -hy, hy, -r.pocket_depth, 0.0)


def body(p: Params = PARAMS, r: Receiver = RECEIVER, top: float = 0.0) -> cq.Workplane:
    x0 = r.front_face_x + p.fit_clearance
    hy = p.body_width / 2
    return _box(x0, x0 + p.body_thickness, -hy, hy, -r.pocket_depth, top)


def steel_pin_slot(p: Params = PARAMS, r: Receiver = RECEIVER) -> cq.Workplane:
    """舌片の底面に開く、鋼製ピンを下から圧入する溝。ピンの表面は底面とそろう。"""
    w = p.steel_pin_diameter - p.steel_pin_press_fit
    length = p.steel_pin_length + 0.4  # ピンの端面と溝の端の逃げ
    z0 = -r.pocket_depth
    return _box(-w / 2, w / 2, -length / 2, length / 2, z0 - 0.1, z0 + p.steel_pin_diameter)


def insert(p: Params = PARAMS, r: Receiver = RECEIVER, body_top: float = 0.0) -> cq.Workplane:
    solid = tongue(p, r).union(neck(p, r)).union(body(p, r, body_top))
    return solid.cut(steel_pin_slot(p, r))
