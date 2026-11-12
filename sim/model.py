"""배열 생성, 그립 최적화, 두 엄지 타자 시간·오타 모델."""
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from thumb import ThumbParams, reach_profile, key_discomfort, ROLLS

HERE = Path(__file__).parent

# ── 말뭉치 → 두벌식 키 입력열 ─────────────────────────────────────
CHO = "r R s e E f a q Q t T d w W c z x v g".split()
JUNG = "k o i O j p u P h hk ho hl y n nj np nl b m ml l".split()
JONG = [""] + "r R rt s sw sg e f fr fa fq ft fx fv fg a q qt t T d w c z x v g".split()


def keystrokes(text):
    """문자열 → 키 이름 열. 대문자는 Shift가 필요한 글자."""
    out = []
    for ch in text:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3:
            s = o - 0xAC00
            out.extend(CHO[s // 588])
            out.extend(JUNG[s % 588 // 28])
            out.extend(JONG[s % 28])
        elif ch == " ":
            out.append("SPC")
        elif ch == "\n":
            out.append("ENT")
        elif ch in ",.":
            out.append(ch)
    return out


@lru_cache(maxsize=None)
def corpus_keys():
    return tuple(keystrokes((HERE / "corpus_ko.txt").read_text(encoding="utf-8")))


# ── 배열 ─────────────────────────────────────────────────────────
# 반쪽 묶음의 글자: 안쪽 열 → 바깥 열
RIGHT_ROWS = [list("yuiop"), ["h", "j", "k", "l", "BS"], ["n", "m", ",", ".", "ENT"]]
LEFT_ROWS = [list("trewq"), list("gfdsa"), list("bvcxz")]


@dataclass
class Layout:
    name: str
    labels: list      # 키 이름
    xy: np.ndarray    # (K, 2) 키 중심
    hand: np.ndarray  # (K,) 0=왼손 1=오른손
    wide: np.ndarray  # (K,) 키 폭(칸)
    px: float
    py: float
    W: float
    H: float
    params: dict
    shift: str = "shoulder"   # "shoulder" | "thumb"

    def index(self, label):
        return self.labels.index(label)


def _half(px, py, rot_deg, thumb_shift, R0=None):
    """오른쪽 반쪽의 키들 (묶음 중심 기준). i=안쪽 열부터, r=윗행부터.
    R0가 있으면 행이 반지름 R0(맨 아랫행)부터 py 간격의 동심원 호가 되는 부채꼴 배열.
    rot_deg>0 이면 묶음 위쪽이 화면 쪽으로 기운다. 반환: 이름, 중심 (K,2), 폭, 키별 회전각(rad)."""
    keys = []
    for r, row in enumerate(RIGHT_ROWS):
        for i, lab in enumerate(row):
            keys.append((lab, i, r, 1))
    if thumb_shift:   # 스페이스 2칸 + Shift를 엄지 키로
        keys += [("SPC_R", 0.5, 3, 2), ("SHIFT_R", 2, 3, 1), ("LEFT", 3, 3, 1), ("RIGHT", 4, 3, 1)]
    else:
        keys += [("SPC_R", 1, 3, 3), ("LEFT", 3, 3, 1), ("RIGHT", 4, 3, 1)]
    labs = [k[0] for k in keys]
    ii = np.array([k[1] for k in keys], float)
    rr = np.array([k[2] for k in keys], float)
    if R0 is None:
        g = np.stack([(ii - 2) * px, (1.5 - rr) * py], -1)
        ang = np.zeros(len(keys))
    else:
        rad = R0 + (3 - rr) * py
        a = (ii - 2) * px / (R0 + 1.5 * py)
        g = np.stack([rad * np.sin(a), rad * np.cos(a) - (R0 + 1.5 * py)], -1)
        ang = -a
    t = math.radians(rot_deg)
    R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
    return labs, g @ R.T, np.array([k[3] for k in keys], float), ang + t


def _mirror(labs_r, xy_r):
    m = {"SPC_R": "SPC_L", "SHIFT_R": "SHIFT_L", "LEFT": "LANG", "RIGHT": "MENU"}
    flat_r = [l for row in RIGHT_ROWS for l in row]
    flat_l = [l for row in LEFT_ROWS for l in row]
    labs = [flat_l[flat_r.index(l)] if l in flat_r else m[l] for l in labs_r]
    return labs, xy_r * np.array([-1, 1])


def _corners(xy, wide, px, py, ang):
    """키캡 구멍의 네 모서리 (K, 4, 2)."""
    hw, hh = (wide - 1) * px / 2 + (px - 1.2) / 2, (py - 1.2) / 2 * np.ones_like(wide)
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = sx * hw, sy * hh
            out.append(xy + np.stack([lx * np.cos(ang) - ly * np.sin(ang), lx * np.sin(ang) + ly * np.cos(ang)], -1))
    return np.stack(out, 1)


def split_layout(px, py, yc, rot=0.0, R0=None, bay=44.0, gap=1.5, H=70.0, thumb_shift=False, edge=3.0,
                 stagger=None, left_tab=False):
    """화면을 가운데 두고 좌우로 나눈 배열.
    stagger: 열마다의 세로 이동량 5개(안쪽 열부터, mm). 열 위치는 그대로 두고 행을 곡선으로 만든다.
    left_tab: 왼쪽 스페이스 바를 2칸으로 줄이고 그 옆에 TAB 키를 둔다."""
    def half(extra_key):
        labs, xy, wide, ang = _half(px, py, rot, extra_key, R0)
        if stagger is not None:
            col = np.rint((xy[:, 0] + 2 * px) / px * 2) / 2        # 키 중심의 열 번호(넓은 키는 x.5 가능)
            for k in range(len(labs)):
                lo = int(math.floor(col[k] - (wide[k] - 1) / 2 + 1e-6))
                hi = int(math.ceil(col[k] + (wide[k] - 1) / 2 - 1e-6))
                xy[k, 1] += min(stagger[c] for c in range(lo, hi + 1))  # 넓은 키는 덮는 열 중 가장 낮은 쪽에
        cor = _corners(xy, wide, px, py, ang)
        xy = xy + np.array([bay / 2 + gap - cor[..., 0].min(), yc])
        return labs, xy, wide, ang, _corners(xy, wide, px, py, ang)

    labs, xy, wide, ang, cor = half(thumb_shift)
    W = 2 * (cor[..., 0].max() + edge)
    fits = cor[..., 1].max() <= H / 2 - edge and cor[..., 1].min() >= -H / 2 + edge
    l_labs, l_xy, l_wide, l_ang, _ = half(thumb_shift or left_tab)
    ll, lxy = _mirror(l_labs, l_xy)
    if left_tab and not thumb_shift:
        ll = ["TAB" if l == "SHIFT_L" else l for l in ll]
    lay = Layout("split", labs + ll, np.vstack([xy, lxy]),
                 np.array([1] * len(labs) + [0] * len(ll)), np.concatenate([wide, l_wide]),
                 px, py, W, H, dict(px=px, py=py, yc=yc, rot=rot, R0=R0, fits=bool(fits),
                      stagger=None if stagger is None else [float(s) for s in stagger], left_tab=left_tab),
                 "thumb" if thumb_shift else "shoulder")
    lay.ang = np.concatenate([ang, -l_ang])
    return lay


def slab_layout(px, py, lift, H, name, edge=3.0, thumb_shift=True):
    """좌우 반쪽이 붙은 10열 배열. 맨 아랫행 중심이 바닥에서 edge + lift + py/2 높이에 온다."""
    labs, xy, wide, ang = _half(px, py, 0.0, thumb_shift)
    xy = xy + np.array([2.5 * px, 0.0])
    xy[:, 1] += (-H / 2 + edge + lift + py / 2) - xy[:, 1].min()
    ll, lxy = _mirror(labs, xy)
    lay = Layout(name, labs + ll, np.vstack([xy, lxy]),
                 np.array([1] * len(labs) + [0] * len(ll)), np.concatenate([wide, wide]),
                 px, py, 10 * px + 2 * edge, H, dict(px=px, py=py, lift=lift, fits=True),
                 "thumb" if thumb_shift else "shoulder")
    lay.ang = np.zeros(len(lay.labels))
    return lay


# ── 그립 최적화 ──────────────────────────────────────────────────
@lru_cache(maxsize=None)
def profile(hand_length, **kw):
    p = ThumbParams(hand_length, **kw)
    return p, [reach_profile(p, r) for r in ROLLS]


def key_freq(lay: Layout):
    seq = corpus_keys()
    f = np.zeros(len(lay.labels))
    for k in seq:
        if k == "SPC":
            f[lay.index("SPC_L")] += 0.5
            f[lay.index("SPC_R")] += 0.5
        elif k in lay.labels:                      # ENT 같은 기능 키
            f[lay.index(k)] += 1
        elif k.lower() in lay.labels:
            f[lay.index(k.lower())] += 1
            if k.isupper() and len(k) == 1 and lay.shift == "thumb":
                f[lay.index("SHIFT_R" if lay.hand[lay.index(k.lower())] == 0 else "SHIFT_L")] += 1
    return f / f.sum()


# 그립 범위: CMC는 기기 외곽에서 손 길이의 0.30배(중수골 길이 + 살)까지 떨어질 수 있다.
# 그보다 멀면 엄지 뿌리(물갈퀴)가 기기 모서리에 닿지 않아 기기를 받칠 수 없다.
GRIP = dict(inside=5.0, out_frac=0.30, up_frac=0.6, az=(0.0, 130.0))


def best_grip(lay: Layout, hand_length, side, freq, **thumb_kw):
    """한 손의 CMC 위치, 손 방향, 엄지 굽힘 평면 기울기를 골라 빈도 가중 불편도를 최소화한다.
    그립은 타자 내내 고정(고쳐 쥐지 않음)이라고 가정한다. 거친 격자 → 주변 세밀 격자 순으로 찾는다."""
    p, tables = profile(hand_length, **thumb_kw)
    sel = lay.hand == side
    keys = lay.xy[sel] * (np.array([-1, 1]) if side == 0 else 1)   # 왼손은 좌우를 뒤집어 오른손 좌표로
    f = freq[sel]
    f = f / f.sum() + 0.004            # 드물게 쓰는 키도 닿아야 한다
    out = GRIP["out_frac"] * hand_length
    lo = (lay.W / 2 - GRIP["inside"], -lay.H / 2 - out, GRIP["az"][0])
    hi = (lay.W / 2 + out, -lay.H / 2 + GRIP["up_frac"] * min(lay.H, 80), GRIP["az"][1])

    def score_of(D):
        un = ~np.isfinite(D)
        return (np.where(un, 0, D) * f).sum(-1) + 20 * (un * f).sum(-1)

    def grid(center, span, n):
        axes = [np.unique(np.clip(np.linspace(c - s, c + s, n), l, h)) for c, s, l, h in zip(center, span, lo, hi)]
        CX, CY, AZ = [a.ravel() for a in np.meshgrid(*axes, indexing="ij")]
        return CX, CY, AZ, np.stack([CX, CY], -1)

    mid = [(l + h) / 2 for l, h in zip(lo, hi)]
    half = [(h - l) / 2 for l, h in zip(lo, hi)]
    # 1) 거친 격자: 기울기(roll)마다 가장 좋은 지점을 후보로 남긴다
    CX, CY, AZ, cmc = grid(mid, half, 13)
    cands = []
    for ri, table in enumerate(tables):
        D = key_discomfort(table, p, cmc, AZ, keys, lay.W / 2, lay.H / 2)
        sc = score_of(D)
        for i in np.argsort(sc)[:2]:
            cands.append((float(sc[i]), (float(CX[i]), float(CY[i]), float(AZ[i])), ri, D[i]))
    cands.sort(key=lambda c: c[0])
    # 2) 상위 후보 여러 개를 각각 좁혀 가며 다듬는다 (국소 최적 회피)
    best = cands[0]
    for c in cands[:5]:
        cur = c
        for shrink in (8, 30):
            CX, CY, AZ, cmc = grid(cur[1], [h / shrink for h in half], 7)
            D = key_discomfort(tables[cur[2]], p, cmc, AZ, keys, lay.W / 2, lay.H / 2)
            sc = score_of(D)
            i = int(np.argmin(sc))
            if sc[i] < cur[0]:
                cur = (float(sc[i]), (float(CX[i]), float(CY[i]), float(AZ[i])), cur[2], D[i])
        if cur[0] < best[0]:
            best = cur
    return dict(cmc=best[1][:2], az=best[1][2], roll=ROLLS[best[2]]), best[3]


# ── 타자 모델 ────────────────────────────────────────────────────
@dataclass(frozen=True)
class TypingParams:
    # 두 엄지 타자 모델 (MacKenzie & Soukoreff 2002; 엄지 Fitts 계수는 Silfverberg 외 2000)
    a: float = 176.0        # ms
    b: float = 64.0         # ms/bit
    t_min: float = 88.0     # 반대쪽 엄지가 이어 칠 때의 최소 간격, ms
    # 아래 셋은 이 설계를 위한 가정이며 민감도 분석 대상
    kappa: float = 0.6      # 불편한 자세가 이동 시간을 늘리는 비율: ×(1 + kappa·불편도)
    sigma0: float = 1.7     # 엄지 착지점 표준편차, mm
    lam: float = 0.6        # 불편한 자세가 착지 산포를 늘리는 비율
    t_fix: float = 700.0    # 오타 하나를 알아채고 고치는 추가 시간(지우기+다시 치기 제외), ms
    t_regrip: float = 500.0 # 닿지 않는 키를 위해 고쳐 쥐는 시간, ms
    cap_gap: float = 1.6    # 키 간격 − 키캡 폭


def simulate(lay: Layout, D, tp: TypingParams = TypingParams()):
    """D: 키별 불편도(닿지 못하면 inf). 반환: 지표 dict."""
    seq = corpus_keys()
    reach = np.isfinite(D)
    Dk = np.where(reach, D, 1.0)
    sig = tp.sigma0 * (1 + tp.lam * Dk)
    hx = (lay.wide - 1) * lay.px / 2 + lay.px / 2
    p_ok = np.array([math.erf(hx[k] / (sig[k] * math.sqrt(2))) * math.erf(lay.py / 2 / (sig[k] * math.sqrt(2)))
                     for k in range(len(Dk))])
    W = min(lay.px, lay.py) - tp.cap_gap
    xy, hand = lay.xy.tolist(), lay.hand.tolist()
    slow = (1 + tp.kappa * Dk).tolist()
    idx = {l: i for i, l in enumerate(lay.labels)}
    spc = (idx["SPC_L"], idx["SPC_R"])
    pos = [xy[idx["d"]], xy[idx["k"]]]
    last = [0.0, 0.0]
    t = 0.0
    prev_hand = 1
    n = n_alt = 0
    errs = disc = 0.0
    regrips = 0

    def press(k):
        nonlocal t, prev_hand, n, n_alt, errs, disc, regrips
        h = hand[k]
        d = math.hypot(xy[k][0] - pos[h][0], xy[k][1] - pos[h][1])
        mt = (tp.a + tp.b * math.log2(d / W + 1)) * slow[k]
        if not reach[k]:
            mt += tp.t_regrip
            regrips += 1
        tk = last[h] + mt
        if h != prev_hand:
            tk = max(tk, t + tp.t_min)
            n_alt += 1
        t = tk
        last[h] = t
        pos[h] = xy[k]
        prev_hand = h
        n += 1
        errs += 1 - p_ok[k]
        disc += Dk[k]

    for key in seq:
        if key == "SPC":
            press(spc[1 - prev_hand])
            continue
        k = idx[key] if key in idx else idx.get(key.lower())
        if k is None:
            continue
        if key.isupper() and len(key) == 1:
            if lay.shift == "thumb":
                press(idx["SHIFT_R" if hand[k] == 0 else "SHIFT_L"])
            # 어깨 버튼 Shift는 검지가 누르므로 엄지 타자 흐름에 끼어들지 않는다
        press(k)

    chars = len(seq)                       # 낸 글쇠(자모·공백·문장부호) 수
    raw = t / chars                        # ms / 글쇠
    err = errs / n
    eff = raw + err * (tp.t_fix + 2 * raw) * n / chars
    return dict(raw_kpm=60000 / raw, eff_kpm=60000 / eff, err=err, discomfort=disc / n,
                alt=n_alt / n, regrips=regrips, unreach=int((~reach).sum()),
                worst=float(np.max(Dk)), presses_per_char=n / chars)


HANDS = {"small": 160.0, "medium": 178.0, "large": 196.0}   # 손 길이 mm (성인 대략 5 / 50 / 95 백분위)


def evaluate(lay: Layout, tp: TypingParams = TypingParams(), hands=HANDS, **thumb_kw):
    f = key_freq(lay)
    res = {}
    for name, hl in hands.items():
        D = np.full(len(lay.labels), np.inf)
        grips = []
        for side in (0, 1):
            g, d = best_grip(lay, hl, side, f, **thumb_kw)
            D[lay.hand == side] = d
            grips.append(g)
        r = simulate(lay, D, tp)
        r.update(grips=grips, D=D)
        res[name] = r
    return res
