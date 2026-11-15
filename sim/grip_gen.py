"""절차적 손잡이 생성: 모양을 미리 정하지 않고, 한 손 쥐기 시뮬레이션이 뒷면 곡면 자체를 만든다.

grip.py는 "높이·마루 위치·비탈 폭" 네 값으로 된 정해진 융기 틀 안에서 104개를 비교했다.
여기서는 틀이 없다. 뒷면(한쪽, 좌우 대칭)을 8 × 6개의 B-스플라인 제어점으로 된 자유 높이장으로 두고,
진화 전략(CMA-ES)이 시뮬레이션 점수만 보고 제어점을 바꿔 가며 곡면을 길러 낸다.

손 모델 (grip.py의 7개 고정 접촉점 대신)
  - 손가락 넷은 각각 세 마디(첫마디·중간마디·끝마디) 관절 사슬이다. 길이는 손 길이에 대한 인체 비율, 굵기는 캡슐 반지름.
  - 손바닥은 옆 모서리에 붙고, 손허리손가락관절(MCP)은 뒷면 가장자리 근처의 정해진 위치에 놓인다.
  - 손가락은 펴진 상태에서 마디마다 차례로 굽혀 곡면에 닿으면 멈춘다(로봇 손이 물체를 감싸는 방식).
    그래서 접촉점의 위치·개수·면 방향이 곡면 모양에서 나온다. 평평한 뒷면에서는 손가락이 펴진 채 눕고,
    융기가 있으면 마루를 감아쥔다.
  - 엄지는 앞면을 누르고, 엄지두덩은 옆 모서리를 민다.
힘 계산
  - 중력이 여러 방향에서 걸릴 때(기기를 어떤 자세로 들든) 힘·돌림힘 평형을 이루면서,
    "관절이 낼 수 있는 최대 토크 대비 실제로 써야 하는 토크의 비율" 중 가장 큰 값 t를 최소화한다(선형계획).
    손가락 관절(MCP·PIP·DIP)의 굽힘·폄 토크, 손가락 옆으로 버티는 힘, 엄지 누르는 힘에 각각 한계가 있다.
  - t가 작을수록 같은 기기를 더 적은 힘의 비율로 쥔다. 지렛대(접촉점이 관절에서 얼마나 먼가)와
    면 방향(마찰에 기대지 않고 걸쳐 버틸 수 있는가)이 바로 반영되므로 grip.py의 "쥐는 폭" 가정 곡선이 필요 없다.
  - 손은 쥐는 위치(MCP 위치 4 × 세로 위치 2)를 스스로 가장 편하게 고른다. 손 크기 3종, 마찰 0.3·0.15.
제약 (생성되는 모양이 지켜야 하는 것)
  - 높이 예산 hmax (주머니 두께와의 타협, 예산별로 따로 생성)
  - 모든 경계에서 높이·기울기 0 (본체와 접선으로 이어짐), 안테나 금지 구역에서는 높이 0
  - 볼록한 곳 곡률 반경 10 mm 이상, 오목한 곳 12 mm 이상, 경사 50° 이하

사용: python grip_gen.py [반복 수]  → grip_gen.json, ../hardware/case/grip_fields.scad, ../docs/img/grip-gen*.png
      python grip_gen.py --report   → 저장된 결과로 그림·표만 다시 만듦
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import linprog

import grip as G

HERE = Path(__file__).parent
ROOT = HERE.parent
W = 142.0
Z_FRONT, Z_BACK = 4.1, -8.2
T = Z_FRONT - Z_BACK                     # 기본 두께 12.3
EDGE_H, A0 = 6.0, 4.0                    # 뒷면 가장자리가 말려 올라가는 높이와 폭
AMAX, YMAX = 66.0, 31.0                  # 생성 영역: 옆 모서리에서 4~66 mm, 세로 ±31 mm (평평한 뒷면 전체)
KEEPOUT = (71 - 46, 71 - 30, 25.0, 33.0)  # 안테나 금지 구역 (a0, a1, y0, y1), dpn_core.scad ant_keepout
FA = np.arange(A0, AMAX + 1e-6, 1.0)
FY = np.arange(-YMAX, YMAX + 1e-6, 1.0)
NCA, NCY = 8, 6                          # 제어점 격자
BASE_MASS, GRAV = 0.095, 9.81
COM = np.array([0.0, 0.0, -2.5])
HANDS, HW = G.HANDS, G.WEIGHTS
MU_SEL = (0.3, 0.15)                     # 생성 점수에 쓰는 마찰 (보통, 미끄러운 손)
MUS = (0.5, 0.3, 0.15)                   # 최종 보고
BUDGETS = (4.0, 7.0, 10.0)               # 높이 예산 (mm)
R_VEX, R_CAVE, SLOPE_MAX = 10.0, 12.0, 50.0

# 손가락 비율 (손 길이 대비, Buchholz 등): [첫마디, 중간마디, 끝마디(끝까지)]
SEG = {"index": (0.245, 0.143, 0.097), "middle": (0.266, 0.170, 0.108),
       "ring": (0.244, 0.165, 0.107), "little": (0.204, 0.117, 0.094)}
RADII = (0.052, 0.046, 0.040)            # 마디 굵기(반지름) / 손 길이
FINGER_STR = {"index": 1.0, "middle": 1.05, "ring": 0.8, "little": 0.6}
TAU_FLEX = (3000.0, 1500.0, 600.0)       # 보통 손 검지 기준 최대 굽힘 토크 N·mm (MCP, PIP, DIP)
EXT_RATIO = 0.35                         # 폄 토크 / 굽힘 토크
F_ABD = 8.0                              # 손가락 하나가 옆으로 버티는 힘 N
F_THUMB = 45.0                           # 엄지 누르는 힘 N
TOL = 1.5                                # 이만큼 가까우면 닿은 것으로 본다 (살이 눌림)
LIMS = ((-40.0, 35.0), (-20.0, 100.0), (-15.0, 80.0))   # 첫마디는 절대각, 나머지는 앞 마디에 대한 굽힘각 (도)
PLACE_A = (-6.0, 0.0, 6.0, 12.0)         # MCP 위치 (옆 모서리에서 안쪽, 음수면 모서리 밖)
PLACE_Y = (-4.0, 4.0)


# ── 곡면 표현 ────────────────────────────────────────
def basis(x, lo, hi, n, k=3):
    t = np.r_[[lo] * k, np.linspace(lo, hi, n - k + 1), [hi] * k]
    return BSpline.design_matrix(np.clip(x, lo, hi - 1e-9), t, k).toarray()


def window(A, Y):
    s = G.smooth
    w = s((A - A0) / 10) * s((AMAX - A) / 10) * s((YMAX - np.abs(Y)) / 9)
    a0, a1, y0, y1 = KEEPOUT
    m = s((A - a0 + 4) / 4) * s((a1 + 4 - A) / 4) * s((Y - y0 + 4) / 4) * s((y1 + 4 - Y) / 4)
    return w * (1 - m)


BA, BY = basis(FA, A0, AMAX, NCA), basis(FY, -YMAX, YMAX, NCY)
WIN = window(FA[:, None], FY[None, :])


def field(c, hmax):
    """제어점 (0~1) → 높이장 H[a, y] (mm). B-스플라인 볼록 껍질 성질로 0 ≤ H ≤ hmax."""
    C = np.clip(np.asarray(c, float).reshape(NCA, NCY), 0, 1)
    return hmax * WIN * (BA @ C @ BY.T)


def analytic_field(shape):
    """grip.py의 정해진 융기 틀 (비교용)."""
    A, Y = np.meshgrid(FA, FY, indexing="ij")
    return G.height(A, Y, *shape) if shape[0] else np.zeros_like(A)


def penalties(H):
    Ha, Hy = np.gradient(H, FA, axis=0), np.gradient(H, FY, axis=1)
    Haa, Hay = np.gradient(Ha, FA, axis=0), np.gradient(Ha, FY, axis=1)
    Hyy = np.gradient(Hy, FY, axis=1)
    g2 = 1 + Ha ** 2 + Hy ** 2
    m, d = (Haa + Hyy) / 2, np.sqrt(((Haa - Hyy) / 2) ** 2 + Hay ** 2)
    vex = float(np.max(-(m - d) / g2 ** 1.5))     # 손 쪽으로 볼록 (마루)
    cave = float(np.max((m + d) / g2 ** 1.5))     # 오목 (골)
    slope = float(np.degrees(np.arctan(np.sqrt(np.max(Ha ** 2 + Hy ** 2)))))
    relu = lambda x: max(0.0, x)
    pen = 40 * relu(vex * R_VEX - 1) ** 2 + 40 * relu(cave * R_CAVE - 1) ** 2 + 40 * relu(slope / SLOPE_MAX - 1) ** 2
    return pen, dict(r_vex=round(1 / vex, 1) if vex > 0 else None, r_cave=round(1 / cave, 1) if cave > 0 else None,
                     slope_deg=round(slope, 1))


def swell_mass(H):
    return 2 * H.sum() * 1.0 * 1.0 * 1e-9 * 1250 * 0.35    # 양쪽, PLA × (외벽 + 채움 어림), kg


# ── 단면 (손가락 하나가 놓이는 세로 위치에서 자른 기기 외곽) ──
class Section:
    """y 위치에서의 외곽선. 좌표 (a, v): a = 옆 모서리에서 안쪽 거리, v = 뒷면 평면에서 손 쪽으로 잰 거리.
    기기는 v가 작은 쪽에 있다."""

    def __init__(self, H, Ha, Hy, y):
        j = float(np.clip(y + YMAX, 0, len(FY) - 1.0001))
        j0, f = int(j), j - int(j)
        h, ha, hy = [(1 - f) * M[:, j0] + f * M[:, j0 + 1] for M in (H, Ha, Hy)]
        self.h = h
        ab = np.arange(A0, 112.0, 0.5)
        hb = np.interp(ab, FA, h, 0, 0) + np.interp(W - ab, FA, h, 0, 0)
        hab = np.interp(ab, FA, ha, 0, 0) - np.interp(W - ab, FA, ha, 0, 0)
        hyb = np.interp(ab, FA, hy, 0, 0) + np.interp(W - ab, FA, hy, 0, 0)
        th = np.linspace(0, np.pi / 2, 14)[:-1]
        wall_v = np.arange(-T + 1, -EDGE_H, 0.5)
        a = np.r_[np.zeros_like(wall_v), A0 - A0 * np.cos(th), ab]
        v = np.r_[wall_v, -EDGE_H + EDGE_H * np.sin(th), hb]
        na = np.r_[np.ones_like(wall_v), EDGE_H * np.cos(th), hab]          # 기기 안쪽을 향하는 법선 (2D)
        nv = np.r_[np.zeros_like(wall_v), -A0 * np.sin(th), -np.ones_like(ab)]
        ny = np.r_[np.zeros_like(wall_v), np.zeros_like(th), hyb]
        s = np.hypot(na, nv)
        na, nv = na / s, nv / s
        n3 = np.stack([-na, ny * -nv, -nv], 1)          # 기기 좌표 (x = W/2 - a, z = Z_BACK - v)
        self.P = np.stack([a, v], 1)
        self.N3 = n3 / np.linalg.norm(n3, axis=1, keepdims=True)
        self.ab, self.hb = ab, hb

    def vsurf(self, a):
        out = np.full_like(a, -np.inf)
        e = (a >= 0) & (a < A0)
        out[e] = -EDGE_H + EDGE_H * np.sqrt(1 - ((A0 - a[e]) / A0) ** 2)
        b = a >= A0
        out[b] = np.interp(a[b], self.ab, self.hb)
        return out

    def sd(self, S):
        """점들에서 외곽까지의 부호 있는 거리 (기기 안이면 음수)와 가장 가까운 외곽 점 번호."""
        d2 = ((S[:, None, :] - self.P[None, :, :]) ** 2).sum(-1)
        i = d2.argmin(1)
        d = np.sqrt(d2[np.arange(len(S)), i])
        inside = (S[:, 0] >= 0) & (S[:, 1] > -T) & (S[:, 1] < self.vsurf(S[:, 0]))
        return np.where(inside, -d, d), i


def seg_pts(J, phi, L):
    s = np.linspace(0, L, max(4, int(L / 1.5)))[:, None]
    return J + s * np.array([math.cos(phi), -math.sin(phi)])


def close_finger(sec, a_m, lens, radii):
    """MCP를 a_m에 두고 손가락을 마디마다 굽혀 곡면을 감싼다. 반환: 관절 위치 [MCP, PIP, DIP, 끝], 각도, 닿은 점.
    MCP는 곡면에 붙을 수 있는 가장 가까운 곳에 두고, 손가락이 곡면을 피할 수 없으면 손을 조금씩 띄워 다시 쥔다."""
    for v in np.arange(-4.0, 30.0, 0.5):
        if sec.sd(np.array([[a_m, v]]))[0][0] >= radii[0]:
            break
    for lift in np.arange(0.0, 16.0, 1.0):
        res = _close(sec, np.array([a_m, v + lift]), lens, radii)
        if res is not None:
            return res
    return None


def _close(sec, mcp, lens, radii):
    J = [mcp]
    phis = []
    for i, (L, r) in enumerate(zip(lens, radii)):
        base = 0.0 if i == 0 else phis[-1]
        lo, hi = (math.radians(x) for x in LIMS[i])
        gap = lambda ph: sec.sd(seg_pts(J[-1], ph, L)[1:])[0].min() - r
        start = base + (lo if i == 0 else 0.0)
        if gap(start) < 0:                              # 펴진 자세에서 이미 닿으면 조금 젖혀 본다
            ok = [ph for ph in base + np.radians(np.arange(-2, LIMS[i][0] - 0.1, -2)) if gap(ph) >= 0]
            if not ok:
                return None
            phis.append(ok[0])
        else:
            ph, step, prev = start, math.radians(3), start
            while ph < base + hi and gap(ph) >= 0:
                prev, ph = ph, min(ph + step, base + hi)
                if ph == base + hi and gap(ph) >= 0:
                    prev = ph
                    break
            if gap(ph) < 0:
                lo_, hi_ = prev, ph
                for _ in range(6):
                    mid = (lo_ + hi_) / 2
                    lo_, hi_ = (mid, hi_) if gap(mid) >= 0 else (lo_, mid)
                prev = lo_
            phis.append(prev)
        J.append(J[-1] + L * np.array([math.cos(phis[-1]), -math.sin(phis[-1])]))
    touch = []
    for i, (L, r) in enumerate(zip(lens, radii)):
        S = seg_pts(J[i], phis[i], L)
        d, idx = sec.sd(S)
        k = np.where(d - r < TOL)[0]
        if len(k) == 0:
            continue
        pick = {k[0], k[-1]} if np.hypot(*(S[k[-1]] - S[k[0]])) > 4 else {k[np.argmin(d[k])]}
        touch += [(i, idx[q]) for q in pick]
    return J, phis, touch


# ── 쥐기 (접촉 + 관절) ───────────────────────────────
def to3(sec_y, a, v):
    return np.array([W / 2 - a, sec_y, Z_BACK - v])


def grasp(surf, hl, place):
    """한 쥐는 법의 접촉 목록. 각 접촉: (위치, 법선, 종류, 손가락 번호, 마디)."""
    H, Ha, Hy, cache = surf
    a_m, y_off = place
    s = hl / 178.0
    pitch = 0.105 * hl
    contacts, fingers = [], []
    for k, name in enumerate(SEG):
        y = float(np.clip(-1 + y_off + (1.5 - k) * pitch, -30, 30))   # 검지가 위
        key = round(y * 2) / 2
        if key not in cache:
            cache[key] = Section(H, Ha, Hy, key)
        sec = cache[key]
        lens = [f * hl for f in SEG[name]]
        res = close_finger(sec, a_m, lens, [f * hl for f in RADII])
        if res is None:
            return None
        J, phis, touch = res
        joints = [to3(key, *j) for j in J[:3]]
        fingers.append(dict(name=name, y=key, joints=joints, J2=J, phis=phis,
                            tau=[t * FINGER_STR[name] * s * s for t in TAU_FLEX]))
        for seg, iv in touch:
            contacts.append((to3(key, *sec.P[iv]), sec.N3[iv], "finger", k, seg))
    # 엄지 (앞면), 엄지두덩 (옆 모서리), 손바닥 (가장자리 곡면)
    contacts.append((np.array([W / 2 - 0.13 * hl, -4 + y_off, Z_FRONT]), np.array([0, 0, -1.0]), "thumb", -1, -1))
    contacts.append((np.array([W / 2, -8 + y_off, -1.0]), np.array([-1.0, 0, 0]), "palm", -1, -1))
    sec = cache[min(cache, key=lambda q: abs(q - (-6 + y_off)))]
    ap = float(np.clip(a_m - 6, 1.5, None))
    iv = int(np.argmin(np.abs(sec.P[:, 0] - ap) + 50 * (sec.P[:, 0] < 0.5)))
    contacts.append((to3(-6 + y_off, *sec.P[iv]), sec.N3[iv], "palm", -1, -1))
    return dict(contacts=contacts, fingers=fingers, s=s)


def solve(gr, mu, gdir, mass, full=False):
    """최대 토크 비율 t를 최소화. 반환 t (불가능하면 10), full이면 (t, 접촉별 힘)."""
    cols, owner = [], []
    for ci, (p, n, kind, fk, seg) in enumerate(gr["contacts"]):
        for e in G.cone(n, mu):
            cols.append(e)
            owner.append(ci)
    E = np.array(cols)
    P = np.array([gr["contacts"][c][0] for c in owner])
    nv = len(E)
    Aeq = np.zeros((6, nv + 1))
    Aeq[:3, :nv] = E.T
    Aeq[3:, :nv] = np.cross(P, E).T / 50.0
    F = mass * GRAV * gdir
    beq = -np.r_[F, np.cross(COM, F) / 50.0]
    rows, s = [], gr["s"]
    owner = np.array(owner)
    kinds = [gr["contacts"][c][2] for c in owner]
    fk = np.array([gr["contacts"][c][3] for c in owner])
    sg = np.array([gr["contacts"][c][4] for c in owner])
    for k, f in enumerate(gr["fingers"]):
        mine = fk == k
        if not mine.any():
            continue
        for j in range(3):
            m = mine & (sg >= j) & np.array([kd == "finger" for kd in kinds])
            tau = np.where(m, np.cross(P - f["joints"][j], E)[:, 1], 0.0)
            rows.append(np.r_[tau, -f["tau"][j]])
            rows.append(np.r_[-tau, -EXT_RATIO * f["tau"][j]])
        lat = np.where(mine, E[:, 1], 0.0)
        rows.append(np.r_[lat, -F_ABD * s * s])
        rows.append(np.r_[-lat, -F_ABD * s * s])
    th = np.array([kd == "thumb" for kd in kinds], float)
    rows.append(np.r_[th, -F_THUMB * s * s])
    c = np.r_[np.full(nv, 1e-4), 1.0]
    r = linprog(c, A_ub=np.array(rows), b_ub=np.zeros(len(rows)), A_eq=Aeq, b_eq=beq,
                bounds=(0, None), method="highs")
    if r.status != 0:
        return (10.0, None) if full else 10.0
    t = float(r.x[-1])
    if not full:
        return t
    forces = np.zeros((len(gr["contacts"]), 3))
    np.add.at(forces, owner, r.x[:nv, None] * E)
    return t, forces


def agg(ts):
    ts = np.asarray(ts)
    return float(ts.mean() + 0.5 * ts.max())


def evaluate(H, final=False):
    """높이장 하나의 쥐기 점수. final이면 26방향 × 마찰 3종으로 자세히."""
    surf = (H, np.gradient(H, FA, axis=0), np.gradient(H, FY, axis=1), {})
    mass = BASE_MASS + swell_mass(H)
    out = {}
    for name, hl in HANDS.items():
        best = (math.inf, None, None)
        for place in [(a, y) for a in PLACE_A for y in PLACE_Y]:
            gr = grasp(surf, hl, place)
            if gr is None:
                continue
            sc = agg([solve(gr, MU_SEL[0], d, mass) for d in AXES])
            if sc < best[0]:
                best = (sc, place, gr)
        _, place, gr = best
        if gr is None:
            out[name] = dict(score=99.0)
            continue
        dirs = G.DIRS if final else G.DIRS_FAST
        rec = dict(place=list(place), angles=[[round(math.degrees(p), 1) for p in f["phis"]] for f in gr["fingers"]],
                   contacts=sum(1 for c in gr["contacts"] if c[2] == "finger"))
        for mu in (MUS if final else MU_SEL):
            ts = [solve(gr, mu, d, mass) for d in dirs]
            rec[str(mu)] = dict(mean=float(np.mean(ts)), worst=float(np.max(ts)), score=agg(ts),
                                **{k: solve(gr, mu, v, mass) for k, v in G.NAMED.items()})
        rec["score"] = rec[str(MU_SEL[0])]["score"] + 0.5 * rec[str(MU_SEL[1])]["score"]
        out[name] = rec
    total = sum(HW[h] * out[h]["score"] for h in HANDS)
    return total, out, mass


AXES = [np.array(v, float) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
REF = None


def objective(args):
    c, hmax, ref = args
    H = field(c, hmax)
    total, _, _ = evaluate(H)
    pen, _ = penalties(H)
    C = np.asarray(c).reshape(NCA, NCY)
    rough = float((np.diff(C, 2, 0) ** 2).mean() + (np.diff(C, 2, 1) ** 2).mean())
    return 100 * total / ref + pen + 2.0 * rough


# ── 생성 ────────────────────────────────────────────
def generate(pool, hmax, ref, iters, seed, warm=None, tag=""):
    """CMA-ES로 곡면을 기른다. warm: 출발 제어점 (없으면 무작위).
    10세대마다 _ckpt/ 에 상태를 저장하고, 다시 실행하면 이어서 한다."""
    import pickle
    import cma
    ck = HERE / "_ckpt" / ("h%g-s%d%s.pkl" % (hmax, seed, tag))
    ck.parent.mkdir(exist_ok=True)
    if ck.exists():
        es, hist, best = pickle.load(open(ck, "rb"))
        print("  hmax %4.1f resume at gen %d" % (hmax, len(hist)), flush=True)
    else:
        rng = np.random.default_rng(seed)
        x0 = np.clip(0.35 + 0.1 * rng.standard_normal(NCA * NCY), 0.05, 0.95) if warm is None else np.clip(warm, 0.02, 0.98)
        es = cma.CMAEvolutionStrategy(x0, 0.3 if warm is None else 0.15, {"bounds": [0, 1], "popsize": 16, "seed": seed, "verbose": -9,
                                                "maxiter": iters})
        hist, best = [], (math.inf, None)
    t0 = time.time()
    while not es.stop() and len(hist) < iters:
        X = es.ask()
        f = pool.map(objective, [(x, hmax, ref) for x in X])
        es.tell(X, f)
        i = int(np.argmin(f))
        if f[i] < best[0]:
            best = (f[i], np.array(X[i]))
        hist.append([float(min(f)), float(np.median(f)), best[0]])
        if len(hist) % 10 == 0:
            pickle.dump((es, hist, best), open(ck, "wb"))
            print("  hmax %4.1f gen %3d best %.2f median %.2f (%.0fs)" % (hmax, len(hist), best[0], hist[-1][1],
                                                                       time.time() - t0), flush=True)
    pickle.dump((es, hist, best), open(ck, "wb"))
    return best[1], hist


def write_scad(designs):
    lines = ["// 자동 생성 파일 — sim/grip_gen.py 가 만든 손잡이 높이장. 손으로 고치지 말 것.",
             "// 오른쪽 손잡이 기준 높이(mm). 행 = a (옆 모서리에서 안쪽 거리), 열 = y. 왼쪽은 거울 대칭.",
             "gen_a = [%g, %g, %g];   // 시작, 간격, 개수" % (FA[0], FA[1] - FA[0], len(FA)),
             "gen_y = [%g, %g, %g];" % (FY[0], FY[1] - FY[0], len(FY)), ""]
    for d in designs:
        H = np.array(d["field"])
        lines.append("gen_%s = [  // 높이 예산 %g mm, 실제 최대 %.1f mm" % (d["name"], d["hmax"], H.max()))
        lines += ["  [" + ",".join("%.2f" % v for v in row) + "]," for row in H]
        lines[-1] = lines[-1].rstrip(",")
        lines.append("];")
    lines.append("GEN_FIELDS = [%s];" % ", ".join('["%s", gen_%s]' % (d["name"], d["name"]) for d in designs))
    (ROOT / "hardware" / "case" / "grip_fields.scad").write_text("\n".join(lines) + "\n", encoding="utf-8")


def report(data):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.edgecolor": GRID, "font.size": 8.5, "axes.titlesize": 9.5, "axes.titleweight": "bold",
                         "axes.spines.top": False, "axes.spines.right": False})
    designs = data["designs"]
    n = len(designs)
    fig, axes = plt.subplots(2, n, figsize=(3.6 * n, 6.6), gridspec_kw=dict(height_ratios=[1.35, 1]))
    for col, d in enumerate(designs):
        H = np.array(d["field"])
        ax = axes[0, col]
        im = ax.imshow(H.T, origin="lower", extent=[FA[0], FA[-1], FY[0], FY[-1]], cmap="Blues",
                       vmin=0, vmax=max(BUDGETS), aspect="equal")
        if H.max() > 0.5:
            ax.contour(FA, FY, H.T, levels=np.arange(1, H.max(), 1.0), colors=INK2, linewidths=0.4)
        a0, a1, y0, y1 = KEEPOUT
        ax.add_patch(plt.Rectangle((a0, y0), a1 - a0, min(y1, YMAX) - y0, fill=False, ls=":", ec="#eb6834", lw=0.8))
        surf = (H, np.gradient(H, FA, axis=0), np.gradient(H, FY, axis=1), {})
        gr = grasp(surf, HANDS["medium"], tuple(d["hands"]["medium"]["place"]))
        for p, nrm, kind, fk, seg in gr["contacts"]:
            if kind == "finger":
                ax.plot(W / 2 - p[0], p[1], "o", ms=3.2, color="#eb6834", mec="white", mew=0.4)
        ax.set_title("%s  (budget %g mm, peak %.1f mm)" % (d["name"], d["hmax"], H.max()), loc="left")
        ax.set_xlabel("distance in from side edge a (mm)")
        if col == 0:
            ax.set_ylabel("y (mm)")
        ax.set_xlim(0, AMAX)
        # 단면: 가운뎃손가락
        ax = axes[1, col]
        f = gr["fingers"][1]
        sec = surf[3][f["y"]]
        m = (sec.P[:, 0] <= 95)
        ax.fill_between(sec.P[m, 0], -T, sec.P[m, 1], color="#dfe9f6", lw=0)
        ax.plot(sec.P[m, 0], sec.P[m, 1], color=INK2, lw=0.8)
        J = np.array(f["J2"])
        for i in range(3):
            r = RADII[i] * HANDS["medium"]
            seg = np.linspace(J[i], J[i + 1], 12)
            for q in seg:
                ax.add_patch(plt.Circle(q, r, color="#f3c9b5", lw=0, alpha=0.25))
        ax.plot(J[:, 0], J[:, 1], "-o", color="#eb6834", lw=1.6, ms=3)
        ax.set_aspect("equal")
        ax.invert_yaxis()
        ax.set_xlim(-25, 95)
        ax.set_ylim(28, -T - 2)
        ax.set_xlabel("a (mm)")
        ax.set_title("middle finger section, medium hand", loc="left", fontweight="normal")
        if col == 0:
            ax.set_ylabel("height below back plane (mm)")
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "img" / "grip-gen.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    ax = axes[0]
    for d in designs:
        h = np.array(d["history"])
        ax.plot(np.arange(1, len(h) + 1), h[:, 2], lw=1.4, label=d["name"])
    ax.axhline(100, color=INK2, lw=0.8, ls="--")
    ax.text(1, 101, "slim case = 100", color=INK2, fontsize=8, va="bottom")
    ax.set_xlabel("generation")
    ax.set_ylabel("objective (lower is better)")
    ax.set_title("Shape evolution (CMA-ES, 16 shapes per generation)", loc="left")
    ax.legend(frameon=False)
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax = axes[1]
    rows = data["compare"]
    names = [r["name"] for r in rows]
    for i, mu in enumerate(MUS):
        vals = [r["rel"][str(mu)] for r in rows]
        ax.bar(np.arange(len(rows)) + (i - 1) * 0.26, vals, 0.25, label="friction %.2f" % mu,
               color=["#86b6ef", "#2a78d6", "#0b3f86"][i])
    ax.axhline(100, color=INK2, lw=0.8, ls="--")
    ax.set_xticks(np.arange(len(rows)))
    ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("joint load, worst + mean (slim = 100)")
    ax.set_title("Grip load by case (26 orientations, 3 hand sizes)", loc="left")
    ax.legend(frameon=False, fontsize=7.5, ncol=3, loc="upper center")
    ax.set_ylim(0, 118)
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "img" / "grip-gen-score.png", dpi=160)
    plt.close(fig)


def summarize(name, H, hmax=None, history=None, ctrl=None):
    total, hands, mass = evaluate(H, final=True)
    _, geo = penalties(H)
    return dict(name=name, hmax=hmax, peak=round(float(H.max()), 2), mass_g=round(1000 * mass, 1),
                thick=round(T + float(H.max()), 1), geometry=geo, hands=hands,
                field=np.round(H, 3).tolist(), history=history, ctrl=None if ctrl is None else np.round(ctrl, 4).tolist())


def relative(rows):
    slim = rows[0]
    for r in rows:
        r["rel"] = {str(mu): round(100 * sum(HW[h] * r["hands"][h][str(mu)]["score"] for h in HANDS) /
                                   sum(HW[h] * slim["hands"][h][str(mu)]["score"] for h in HANDS), 1) for mu in MUS}
        r["rel_hang"] = {str(mu): round(100 * sum(HW[h] * r["hands"][h][str(mu)]["hang"] for h in HANDS) /
                                        sum(HW[h] * slim["hands"][h][str(mu)]["hang"] for h in HANDS), 1) for mu in MUS}


if __name__ == "__main__":
    from multiprocessing import Pool
    out = HERE / "grip_gen.json"
    if "--report" in sys.argv:
        report(json.load(open(out, encoding="utf-8")))
        sys.exit()
    iters = int(next((a for a in sys.argv[1:] if a.isdigit()), 80))
    slim_total, _, _ = evaluate(np.zeros((len(FA), len(FY))))
    print("slim objective base %.4f" % slim_total, flush=True)
    designs = []
    with Pool() as pool:
        for i, hmax in enumerate(BUDGETS):
            # 낮은 예산의 결과는 높은 예산 안에 그대로 들어가므로 그것을 출발점으로 삼는다
            warm = None if not designs else designs[-1][2] * designs[-1][1] / hmax
            c, hist = generate(pool, hmax, slim_total, iters, seed=11 + i, warm=warm)
            if warm is not None and objective((warm, hmax, slim_total)) < hist[-1][2]:
                c2, hist2 = generate(pool, hmax, slim_total, iters // 2, seed=11 + i, warm=warm, tag="-warm")
                if hist2[-1][2] < hist[-1][2]:
                    c, hist = c2, hist + hist2
            designs.append((("G%d" % hmax), hmax, c, hist))
        rows = pool.starmap(summarize, [("slim", np.zeros((len(FA), len(FY))))] +
                            [("old B", analytic_field((7.0, 52.0, 15.0, 0.0)))] +
                            [(nm, field(c, hm), hm, h, c) for nm, hm, c, h in designs])
    relative(rows)
    data = dict(compare=[{k: r[k] for k in ("name", "peak", "thick", "mass_g", "geometry", "rel", "rel_hang", "hands")}
                         for r in rows], designs=rows[2:])
    json.dump(data, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    write_scad(rows[2:])
    report(data)
    for r in rows:
        print("%-6s peak %4.1f thick %4.1f mass %5.1f g  load %s  hang %s  geo %s" % (
            r["name"], r["peak"], r["thick"], r["mass_g"], r["rel"], r["rel_hang"], r["geometry"]))
        for h in HANDS:
            x = r["hands"][h]
            print("    %-6s place %s contacts %d angles %s" % (h, x["place"], x["contacts"], x["angles"]))
