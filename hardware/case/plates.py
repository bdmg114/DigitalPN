"""Bambu Lab A1(256 × 256 mm)용 출력판 STL을 만든다.

stl/의 부품 STL(이미 출력 방향으로 놓여 있음)을 판 단위로 묶어 stl/a1/에 쓴다.
재질과 서포트 설정이 같은 부품끼리 한 판에 모았다.

    python plates.py
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "stl")
OUT = os.path.join(SRC, "a1")
BED = 256.0
MARGIN = 10.0  # 판 가장자리에서 최소 거리

DT = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])


def load(name):
    d = open(os.path.join(SRC, name), "rb").read()
    n = int.from_bytes(d[80:84], "little")
    assert len(d) == 84 + 50 * n, f"{name}: binary STL이 아님"
    return np.frombuffer(d[84:], dtype=DT, count=n)["v"].astype(np.float64)


def place(tris, x, y, rot=0):
    """바닥(z 최소)을 0에 붙이고, 평면 중심을 (x, y)로 옮긴 뒤 rot도(90 단위) 돌린다."""
    t = tris.copy()
    lo, hi = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
    t -= [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]
    a = np.radians(rot)
    c, s = np.cos(a), np.sin(a)
    xy = t[..., :2].copy()
    t[..., 0] = c * xy[..., 0] - s * xy[..., 1] + x
    t[..., 1] = s * xy[..., 0] + c * xy[..., 1] + y
    return t


def save(name, parts):
    tris = np.concatenate([p for _, p in parts])
    v = tris.reshape(-1, 3)
    lo, hi = v.min(0), v.max(0)
    assert lo[0] >= MARGIN and lo[1] >= MARGIN and hi[0] <= BED - MARGIN and hi[1] <= BED - MARGIN, (name, lo, hi)
    # 부품끼리 겹치지 않는지 (외곽 상자 기준, 5 mm 이상 간격)
    boxes = [(n, p.reshape(-1, 3).min(0), p.reshape(-1, 3).max(0)) for n, p in parts]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (na, la, ha), (nb, lb, hb) = boxes[i], boxes[j]
            gap = max(lb[0] - ha[0], la[0] - hb[0], lb[1] - ha[1], la[1] - hb[1])
            assert gap >= 5, (name, na, nb, gap)
    e1, e2 = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    nrm = np.cross(e1, e2)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(tris), dtype=DT)
    rec["n"], rec["v"] = nrm, tris
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(f"DigitalPN A1 plate {name}".encode().ljust(80, b" "))
        f.write(len(tris).to_bytes(4, "little"))
        f.write(rec.tobytes())
    print(f"{name}: {len(parts)}개, {hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]:.1f} mm")


C = BED / 2

# 판 1 — PLA/PETG, 서포트 없음: 기준 케이스 앞판·뒷판 + 어깨 캡 2개
save("a1-1-pla-case.stl", [
    ("top", place(load("dpn-top.stl"), C - 10, C + 40)),
    ("bottom", place(load("dpn-bottom.stl"), C - 10, C - 40)),
    ("shoulder1", place(load("dpn-shoulder.stl"), C + 78, C + 8)),
    ("shoulder2", place(load("dpn-shoulder.stl"), C + 78, C - 8)),
])

# 판 2 — TPU 95A: 키매트 좌·우
save("a1-2-tpu-keymat.stl", [
    ("keymat_l", place(load("dpn-keymat_l.stl"), C - 32, C)),
    ("keymat_r", place(load("dpn-keymat_r.stl"), C + 32, C)),
])

# 판 3 (선택) — PLA/PETG, 서포트 필요: 손잡이형 앞판 + 뒷판 후보 G4·G7·G10
# 앞쪽(y 작은 쪽)부터 G4, G7, G10. 앞판은 오른쪽에 세로로 돌려 놓는다.
x0 = (BED - (142 + 10 + 70)) / 2
save("a1-3-pla-grip.stl", [
    ("gripG4", place(load("dpn-gripG4-bottom.stl"), x0 + 71, C - 78)),
    ("gripG7", place(load("dpn-gripG7-bottom.stl"), x0 + 71, C)),
    ("gripG10", place(load("dpn-gripG10-bottom.stl"), x0 + 71, C + 78)),
    ("grip-top", place(load("dpn-grip-top.stl"), x0 + 142 + 10 + 35, C, rot=90)),
])
