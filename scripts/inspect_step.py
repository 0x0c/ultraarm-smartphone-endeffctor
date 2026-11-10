"""公式 STEP から、ultraArm P340 先端の受け口の寸法と平行リンクの構成を読み取る。

使い方:
    uv run python scripts/inspect_step.py [vendor/UltraArm_P340_3D_230918.stp] [--json]

STEP の座標系は Z が上、ベースは +X 側にあり、アームは -X 方向（前方）へ伸びている。
受け口は「X の最小値がもっとも小さい立体」として特定する。寸法は面の位置から求め、
値を埋め込まない（STEP が更新されても同じ規則で読み直せるようにするため）。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cadquery as cq

DEFAULT_STEP = Path(__file__).resolve().parent.parent / "vendor" / "UltraArm_P340_3D_230918.stp"
TOL = 1e-3


@dataclass
class PlaneFace:
    axis: str  # "x" / "y" / "z"
    sign: int  # 法線の向き（+1 / -1）
    pos: float
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float
    area: float


@dataclass
class Pivot:
    x: float
    z: float
    radius: float


@dataclass
class ReceiverDims:
    solid_index: int
    outer_x: tuple[float, float]
    outer_y: tuple[float, float]
    outer_z: tuple[float, float]
    top_z: float
    pocket_x: tuple[float, float]
    pocket_y: tuple[float, float]
    pocket_floor_z: float
    pocket_width: float
    pocket_length: float
    pocket_depth: float
    front_face_x: float
    front_wall_thickness: float
    notch_y: tuple[float, float]
    notch_width: float
    magnet_recess_x: tuple[float, float]
    magnet_recess_y: tuple[float, float]
    magnet_recess_z: tuple[float, float]
    magnet_skin: float
    pivots: list[Pivot]


def axis_planes(solid: cq.Solid) -> list[PlaneFace]:
    out = []
    for f in solid.Faces():
        if f.geomType() != "PLANE":
            continue
        n = f.normalAt().toTuple()
        for i, ax in enumerate("xyz"):
            if abs(abs(n[i]) - 1) < TOL:
                b = f.BoundingBox()
                out.append(
                    PlaneFace(ax, 1 if n[i] > 0 else -1, f.Center().toTuple()[i],
                              b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax, f.Area())
                )
    return out


def y_pivots(solid: cq.Solid, max_radius: float = 4.5) -> list[Pivot]:
    """Y 軸に平行な円筒面（リンクのピン穴）の中心を重複なく返す。

    角の丸み（フィレット）も円筒面なので、同じ軸と半径を持つ面の角度範囲を合計し、
    ほぼ一周（270 度以上）するものだけをピン穴とみなす。
    """
    span: dict[tuple[float, float, float], float] = {}
    for f in solid.Faces():
        if f.geomType() != "CYLINDER":
            continue
        cyl = f._geomAdaptor().Cylinder()
        d, p = cyl.Axis().Direction(), cyl.Axis().Location()
        if abs(abs(d.Y()) - 1) < TOL and cyl.Radius() <= max_radius:
            key = (round(p.X(), 2), round(p.Z(), 2), round(cyl.Radius(), 2))
            umin, umax, _, _ = f._uvBounds()
            span[key] = span.get(key, 0.0) + (umax - umin)
    return [Pivot(*k) for k, s in span.items() if s >= 1.5 * math.pi]


def close(a: float, b: float, tol: float = 0.05) -> bool:
    return abs(a - b) < tol


def measure_receiver(solids: list[cq.Solid]) -> ReceiverDims:
    idx = min(range(len(solids)), key=lambda i: solids[i].BoundingBox().xmin)
    s = solids[idx]
    bb = s.BoundingBox()
    planes = axis_planes(s)

    # 縦穴の底: 下面より上にある上向き面のうち、もっとも低いもの。
    ups = [p for p in planes if p.axis == "z" and p.sign > 0 and p.pos > bb.zmin + 1]
    floor = min(ups, key=lambda p: p.pos)
    # 縦穴の側壁: 底の高さから立ち上がる面。
    walls = [p for p in planes if p.axis != "z" and close(p.zmin, floor.pos)]
    # X 方向の壁: +X 向き（前壁の内面）は小さい側、-X 向きは大きい側。面積最大のものを採る。
    px_lo = max((p for p in walls if p.axis == "x" and p.sign > 0), key=lambda p: p.area).pos
    px_hi = max((p for p in walls if p.axis == "x" and p.sign < 0), key=lambda p: p.area).pos
    # Y 方向の壁: 縦穴の範囲内（X が px_lo〜px_hi）にあるもの。
    in_pocket = [p for p in walls if p.axis == "y" and p.xmin >= px_lo - 1.01 and p.xmax <= px_hi + TOL]
    py_lo = max(p.pos for p in in_pocket if p.sign > 0)
    py_hi = min(p.pos for p in in_pocket if p.sign < 0)
    # 前壁の切り欠き: 縦穴より前（X が px_lo より小さい）にある Y 方向の壁。
    notch = [p for p in walls if p.axis == "y" and p.xmax <= px_lo - 0.5]
    ny_lo = max(p.pos for p in notch if p.sign > 0)
    ny_hi = min(p.pos for p in notch if p.sign < 0)
    # 上面: 縦穴を囲む上向き面のうち、もっとも高いもの。
    top = max((p for p in ups if p.xmin <= px_lo and p.xmax >= px_hi), key=lambda p: p.pos)
    # 前面: -X 向きでもっとも小さい X。
    front = min((p for p in planes if p.axis == "x" and p.sign < 0), key=lambda p: p.pos)
    # 磁石の凹み: 下面より上にある下向き面のうち、もっとも低いもの（下から掘り込まれた凹みの天井）。
    downs = [p for p in planes if p.axis == "z" and p.sign < 0 and p.pos > bb.zmin + TOL]
    recess = min(downs, key=lambda p: p.pos)

    return ReceiverDims(
        solid_index=idx,
        outer_x=(bb.xmin, bb.xmax),
        outer_y=(bb.ymin, bb.ymax),
        outer_z=(bb.zmin, bb.zmax),
        top_z=top.pos,
        pocket_x=(px_lo, px_hi),
        pocket_y=(py_lo, py_hi),
        pocket_floor_z=floor.pos,
        pocket_width=px_hi - px_lo,
        pocket_length=py_hi - py_lo,
        pocket_depth=top.pos - floor.pos,
        front_face_x=front.pos,
        front_wall_thickness=px_lo - front.pos,
        notch_y=(ny_lo, ny_hi),
        notch_width=ny_hi - ny_lo,
        magnet_recess_x=(recess.xmin, recess.xmax),
        magnet_recess_y=(recess.ymin, recess.ymax),
        magnet_recess_z=(bb.zmin, recess.pos),
        magnet_skin=floor.pos - recess.pos,
        pivots=y_pivots(s),
    )


def find_parallelogram(solids: list[cq.Solid], rec: ReceiverDims) -> dict:
    """受け口の 2 本のピンと同じ相対位置にピンの組を持つ別の立体を探す。

    見つかれば、受け口とその立体は平行四辺形リンクでつながり、互いの姿勢が等しく保たれる。
    """
    rp = sorted(rec.pivots, key=lambda p: p.z)
    if len(rp) < 2:
        return {"found": False}
    a, b = rp[0], rp[-1]
    vec = (b.x - a.x, b.z - a.z)
    for i, s in enumerate(solids):
        if i == rec.solid_index:
            continue
        ps = y_pivots(s)
        for p in ps:
            for q in ps:
                if close(q.x - p.x, vec[0]) and close(q.z - p.z, vec[1]) and close(p.z, a.z):
                    return {
                        "found": True,
                        "receiver_pivots": [asdict(a), asdict(b)],
                        "partner_solid_index": i,
                        "partner_pivots": [asdict(p), asdict(q)],
                        "pivot_vector_xz": vec,
                        "link_length": p.x - a.x,
                    }
    return {"found": False}


def links_at(solids: list[cq.Solid], index: int, exclude: set[int]) -> list[dict]:
    """立体 index のピン位置を共有する他の立体（リンク）と、その反対側のピン位置を返す。

    肘の部品が水平に保たれるかを、後ろ側のリンク構成から人が判断するための材料にする。
    リンクの太いピン穴も拾うため、半径の上限を広げて探す。
    """
    own = {(p.x, p.z) for p in y_pivots(solids[index], max_radius=8)}
    out = []
    for i, s in enumerate(solids):
        if i == index or i in exclude:
            continue
        pts = {(p.x, p.z) for p in y_pivots(s, max_radius=8)}
        shared = pts & own
        if shared:
            others = sorted(pts - own)
            out.append({"solid_index": i, "shared": sorted(shared), "other_ends": others})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", nargs="?", type=Path, default=DEFAULT_STEP)
    ap.add_argument("--json", action="store_true", help="JSON で出力する")
    args = ap.parse_args(argv)
    if not args.step.exists():
        print(f"STEP が見つからない: {args.step}", file=sys.stderr)
        return 1

    solids = cq.importers.importStep(str(args.step)).solids().vals()
    rec = measure_receiver(solids)
    par = find_parallelogram(solids, rec)
    elbow_links = (
        links_at(solids, par["partner_solid_index"], {rec.solid_index}) if par["found"] else []
    )

    if args.json:
        print(json.dumps({"receiver": asdict(rec), "parallelogram": par, "elbow_links": elbow_links},
                         indent=2, ensure_ascii=False))
        return 0

    r = rec
    f = lambda t: f"[{t[0]:.2f}, {t[1]:.2f}]"  # noqa: E731
    print(f"受け口の立体: #{r.solid_index}  外形 X{f(r.outer_x)} Y{f(r.outer_y)} Z{f(r.outer_z)}")
    print(f"縦穴: 幅(X) {r.pocket_width:.2f}  長さ(Y) {r.pocket_length:.2f}  深さ(Z) {r.pocket_depth:.2f}")
    print(f"      X{f(r.pocket_x)} Y{f(r.pocket_y)} 底 Z={r.pocket_floor_z:.2f} 上面 Z={r.top_z:.2f}")
    print(f"前面: X={r.front_face_x:.2f}  前壁の厚さ {r.front_wall_thickness:.2f}")
    print(f"前壁の切り欠き: 幅(Y) {r.notch_width:.2f}  Y{f(r.notch_y)}")
    print(f"磁石の凹み（下面から）: X{f(r.magnet_recess_x)} Y{f(r.magnet_recess_y)} Z{f(r.magnet_recess_z)}"
          f"  縦穴の底までの肉厚 {r.magnet_skin:.2f}")
    for p in r.pivots:
        print(f"ピン穴: X={p.x:.2f} Z={p.z:.2f} r={p.radius:.2f}")
    if par["found"]:
        print(f"平行リンク: 立体 #{par['partner_solid_index']} が同じピン間ベクトル "
              f"{tuple(round(v, 2) for v in par['pivot_vector_xz'])} を持ち、"
              f"リンク長 {par['link_length']:.2f} で平行四辺形をなす")
        for link in elbow_links:
            fmt = lambda pts: ", ".join(f"({x:.2f}, {z:.2f})" for x, z in pts)  # noqa: E731
            print(f"  肘の部品 #{par['partner_solid_index']} につながるリンク #{link['solid_index']}: "
                  f"共有ピン {fmt(link['shared'])} → 反対側 {fmt(link['other_ends']) or 'なし'}")
    else:
        print("平行リンク: 対になるピンの組が見つからない")
    return 0


if __name__ == "__main__":
    sys.exit(main())
