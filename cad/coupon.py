"""差し込み部だけの試験片。受け口へのはまり具合と磁石の吸着を、全体を印刷する前に確かめる。

本体を上面より少し高くし、つまんで抜き差しできるようにする。
"""

from __future__ import annotations

import cadquery as cq

from cad.insert import insert
from cad.params import PARAMS, RECEIVER, Params, Receiver

GRIP_HEIGHT = 8.0  # 本体が受け口の上面から突き出す高さ（つまみ）


def coupon(p: Params = PARAMS, r: Receiver = RECEIVER) -> cq.Workplane:
    return insert(p, r, body_top=GRIP_HEIGHT)
