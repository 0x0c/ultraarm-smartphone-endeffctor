"""開発環境の疎通確認。CadQuery の幾何カーネルが読み込めて、立体を作れることを確かめる。"""

import cadquery as cq


def test_cadquery_builds_solid():
    box = cq.Workplane("XY").box(10, 20, 30).val()
    assert box.isValid()
    assert abs(box.Volume() - 6000) < 1e-6
