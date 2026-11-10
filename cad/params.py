"""寸法パラメータ。

座標系はすべて「受け口基準」で書く。
- 原点: 受け口の縦穴の上面（開口部）の中心
- +X: 前方（ベースから遠ざかる向き）
- +Z: 上
- +Y: 右手系で残る向き（前方を向いて左）

STEP の座標系へは Z 軸まわりに 180° 回して平行移動すれば重なる（`RECEIVER.to_step_location`）。
受け口の寸法は README の「計測値」節にある値で、`tests/test_coupon.py` が STEP と照合する。
"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True)
class Receiver:
    """ultraArm P340 先端の受け口（STEP から計測した値。単位は mm）。"""

    pocket_width: float = 8.00  # 縦穴の前後方向（X）
    pocket_length: float = 30.00  # 縦穴の左右方向（Y）
    pocket_depth: float = 17.90  # 縦穴の深さ（Z）
    pocket_chamfer: float = 1.00  # 縦穴の鉛直の稜の面取り
    front_wall_thickness: float = 5.80  # 前面から縦穴までの壁厚
    notch_width: float = 8.00  # 前壁の切り欠きの幅（Y）
    height: float = 22.00  # 受け口の上面から下面まで

    # STEP 座標系での縦穴上面の中心（受け口基準の原点）
    step_origin: tuple[float, float, float] = (-89.51, -48.09, 180.00)

    @property
    def front_face_x(self) -> float:
        """受け口基準での前面の X 座標。"""
        return self.pocket_width / 2 + self.front_wall_thickness

    def to_step_location(self) -> cq.Location:
        """受け口基準の形状を STEP 座標系へ移す変換。"""
        return cq.Location(cq.Vector(*self.step_origin), cq.Vector(0, 0, 1), 180)


RECEIVER = Receiver()


@dataclass(frozen=True)
class Params:
    """アダプタの設計パラメータ（単位は mm）。値は試作で確定させる。"""

    fit_clearance: float = 0.2  # 受け口と差し込み部の片側のすきま
    # 差し込み部の前端からホルダー取り付け面までの水平距離。
    # つまみねじは取り付け面の後ろから通すので、ねじの頭（D リングで厚さ約 10）と
    # 指を入れる余地で決まる。前腕との干渉には効かない（スマホは取り付け面より前に出る）。
    beam_length: float = 30.0
    beam_thickness: float = 6.0  # 梁の厚さ
    mount_plate_thickness: float = 5.0  # ホルダー取り付け面の板厚
    mount_plate_width: float = 30.0  # ホルダー取り付け面の幅（Y）
    mount_plate_height: float = 34.0  # ホルダー取り付け面の高さ（底面から）
    screw_hole_diameter: float = 6.6  # 1/4 インチのつまみねじを通す穴の径
    screw_hole_height: float = 22.0  # ねじ穴の中心の高さ（底面から）
    gusset_size: float = 12.0  # 梁と取り付け面をつなぐ三角リブの辺の長さ
    gusset_thickness: float = 3.0  # 三角リブの厚さ
    steel_pin_diameter: float = 3.0  # 舌片の底に圧入する鋼製平行ピンの径
    steel_pin_length: float = 20.0  # 同じく長さ
    steel_pin_press_fit: float = 0.1  # 圧入のための溝幅の詰め代

    # 差し込み部の本体（受け口の前面の外側に出る板）
    body_thickness: float = 5.0  # 前後方向（X）の厚さ
    body_width: float = 30.0  # 左右方向（Y）の幅


PARAMS = Params()
