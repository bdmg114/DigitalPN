"""목업 출력용: 손에 닿는 바깥 면에 미끄럼 방지 오돌토돌 질감을 입힌 뒷판 STL을 만든다.

case.scad 에서 뽑은 뒷판 STL을 읽어 메시를 잘게 나눈 뒤, 손에 닿는 바깥 면(뒷면·손잡이 곡면, 뒷면 가장자리 말림,
옆벽)의 점들을 바깥쪽으로만 무작위 돌기 높이만큼 밀어낸다. 벽은 얇아지지 않는다.
앞판과 맞닿는 윗부분(z > -1.8), USB·어깨 버튼 구멍, 안쪽 면은 매끈하게 둔다.

출력 방향: 두 부품 모두 열린 쪽을 바닥에 (질감 면이 위를 향해 깨끗하게 출력됨, 안쪽 바닥면 아래 서포트 필요).

얇은 기본형은 뒷면의 동심 호 홈(grip_grooves)을 빼고 질감만 입힌다 (둘 다 미끄럼 방지라 겹치면 홈이 뭉개진다).

사용: python texture.py  → stl/mockup/dpn-gripG7-bottom-textured.stl, stl/mockup/dpn-bottom-textured.stl
      원본 뒷판은 OpenSCAD로 직접 뽑는다 (환경 변수 OPENSCAD 또는 기본 설치 경로).
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import manifold3d as mf
import pyvista as pv

HERE = Path(__file__).parent
BOT_Z = -8.2                  # 뒷판 바깥 바닥 (dpn_core.scad: -(pcb_t + back_depth + floor_t))
OUT_W, OUT_H, OUT_R = 142.0, 70.0, 14.0
AMP = 0.4                     # 돌기 높이 (mm)
CELL = 1.4                    # 돌기 간격 (mm)
EDGE = 0.45                   # 메시를 나누는 최대 변 길이 (mm)
Z_TOP = -1.8                  # 이보다 위(앞판과 맞닿는 쪽)는 매끈하게
SEED = 7


def outline_dist(x, y):
    """둥근 사각형 외곽에서 안쪽으로의 거리 (밖이면 음수)."""
    qx = np.abs(x) - (OUT_W / 2 - OUT_R)
    qy = np.abs(y) - (OUT_H / 2 - OUT_R)
    out = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)
    return OUT_R - out


def noise(p, cell, seed):
    """3차원 값 잡음 (0~1), 격자 간격 cell, 부드러운 보간."""
    rng = np.random.default_rng(seed)
    lat = rng.random((64, 64, 64))
    g = p / cell
    i = np.floor(g).astype(int)
    f = g - i
    f = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * lat[(i[:, 0] + dx) % 64, (i[:, 1] + dy) % 64, (i[:, 2] + dz) % 64]
    return out


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def texture(src, dst, to_assembly):
    m = pv.read(src).triangulate().clean()
    v = to_assembly(np.asarray(m.points, float))
    f = m.faces.reshape(-1, 4)[:, 1:]
    solid = mf.Manifold(mf.Mesh(vert_properties=v.astype(np.float32), tri_verts=f.astype(np.uint32)))
    assert solid.status() == mf.Error.NoError, solid.status()
    solid = solid.refine_to_length(EDGE)
    mesh = solid.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3].astype(float)
    F = np.asarray(mesh.tri_verts)
    # 정점 법선 (넓이 가중)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    x, y, z = V.T
    d = outline_dist(x, y)
    # 바깥 법선 방향: 외곽에서 가장 가까운 쪽 (근사: 중심에서 바깥으로, 직선 구간에서는 축 방향)
    qx, qy = np.abs(x) - (OUT_W / 2 - OUT_R), np.abs(y) - (OUT_H / 2 - OUT_R)
    ox = np.where(qx > 0, np.sign(x) * np.maximum(qx, 0), 0.0)
    oy = np.where(qy > 0, np.sign(y) * np.maximum(qy, 0), 0.0)
    corner = (qx > 0) & (qy > 0)
    ox = np.where(~corner & (qx >= qy), np.sign(x), ox)
    oy = np.where(~corner & (qy > qx), np.sign(y), oy)
    o = np.stack([ox, oy], 1)
    o /= np.linalg.norm(o, axis=1, keepdims=True) + 1e-12
    side = (N[:, :2] * o).sum(1)                       # 옆벽 바깥을 향하는 정도
    down = -N[:, 2]                                    # 뒷면(아래)을 향하는 정도
    mask = np.maximum(smooth((down - 0.25) / 0.3), smooth((side - 0.6) / 0.25) * smooth((1.0 - d) / 0.6))
    mask *= smooth((Z_TOP - z) / 0.8)                  # 앞판과 맞닿는 쪽은 매끈하게
    h = AMP * np.clip(0.7 * noise(V, CELL, SEED) + 0.3 * noise(V + 31.7, CELL / 2, SEED + 1), 0, 1)
    h = smooth((h / AMP - 0.25) / 0.6) * AMP           # 돌기 사이에 평평한 바닥이 생기게 대비를 높임
    V2 = V + (mask * h)[:, None] * N
    out = mf.Manifold(mf.Mesh(vert_properties=V2.astype(np.float32), tri_verts=F.astype(np.uint32)))
    assert out.status() == mf.Error.NoError, out.status()
    om = out.to_mesh()
    P = np.asarray(om.vert_properties)[:, :3].astype(float)
    P[:, 1:] *= -1                                     # 열린 쪽이 바닥으로 (x축 180° 회전)
    P[:, 2] -= P[:, 2].min()
    T = np.asarray(om.tri_verts)
    pm = pv.PolyData(P, np.c_[np.full(len(T), 3), T].ravel())
    pm.save(dst, binary=True)
    b = pm.bounds
    print("%s: %d 삼각형, %.1f x %.1f x %.1f mm, 질감 면 %.0f%%, manifold %s" % (
        dst.name, pm.n_cells, b[1] - b[0], b[3] - b[2], b[5] - b[4], 100 * (mask > 0.5).mean(), pm.is_manifold))


def openscad(dst, *defs):
    exe = os.environ.get("OPENSCAD") or shutil.which("openscad") or r"C:\Program Files\OpenSCAD\openscad.com"
    args = [exe, "-o", str(dst)] + [x for d in defs for x in ("-D", d)] + [str(HERE / "case.scad")]
    subprocess.run(args, check=True, capture_output=True)


if __name__ == "__main__":
    out = HERE / "stl" / "mockup"
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        openscad(src / "grip.stl", 'style="grip"', 'grip_variant="G7"', 'part="bottom"')
        openscad(src / "slim.stl", 'part="bottom"', "grip=false")
        # 손잡이형: case.scad 가 x축 180° 회전으로 놓았다 → 되돌림
        texture(src / "grip.stl", out / "dpn-gripG7-bottom-textured.stl", lambda p: p * np.array([1, -1, -1]))
        # 얇은 기본형: 뒷면이 바닥에 오도록 z를 -bot_z 만큼 올렸다 → 되돌림
        texture(src / "slim.stl", out / "dpn-bottom-textured.stl", lambda p: p + np.array([0, 0, BOT_Z]))
