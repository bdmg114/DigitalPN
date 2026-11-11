"""엄지 운동학 모델: 관절 가동범위 안에서 키에 닿는 자세와 그 불편도를 구한다.

좌표: 기기 앞면이 z=0 평면, +z가 사용자 쪽. 엄지는 CMC(손목 쪽 뿌리 관절)에서 시작해
중수골 → 첫마디 → 끝마디로 이어지는 3링크이고, 굽힘은 기기 면에 수직인 평면에서 일어난다.
그 평면이 기기 면 위에서 향하는 방위(azimuth)는 CMC의 좌우 벌림이 맡는다.

자유도 4개: CMC 방위 φ, CMC 들림 ε, MCP 굽힘 θm, IP 굽힘 θi.
목표(엄지 패드가 키 윗면에 닿음)는 구속 3개이므로 1개가 남고, 그 여유는 불편도 최소화에 쓴다.

굽힘 평면은 기기 면에 수직이 아니라 ρ만큼 기울 수 있다(엄지의 회내). ρ는 손을 쥔 자세가
정하는 값으로 보고 타자 중에는 고정한다. ρ가 크면 엄지가 면과 나란히 접히므로 뿌리에 가까운
키에 닿을 수 있다.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ThumbParams:
    hand_length: float            # 손 길이 (손목 주름~가운뎃손가락 끝), mm
    # 마디 길이 비율 (Buchholz 외 1992의 손 길이 대비 계수)
    k_mc: float = 0.251
    k_pp: float = 0.196
    k_dp: float = 0.158
    pad_back: float = 0.055       # 끝마디 끝에서 패드 중심까지 (손 길이 대비)
    pad_thick: float = 0.033      # 패드 표면에서 뼈 축까지
    ip_half: float = 0.042        # IP 관절 반두께
    mcp_half: float = 0.047       # MCP 관절 반두께(눌린 살 감안)
    cmc_depth: float = 10.0       # CMC가 기기 앞면보다 뒤에 있는 깊이, mm
    # 가동범위 (도). CMC는 Cooney 외 1981의 굽힘-폄 53° → 방위(면 위 쓸기), 벌림-모음 42° → 들림
    az_half: float = 26.5
    elev: tuple = (5.0, 47.0)
    elev_neutral: float = 25.0
    mcp: tuple = (0.0, 56.0)
    mcp_neutral: float = 15.0
    ip: tuple = (-10.0, 80.0)
    ip_neutral: float = 20.0
    pad_pitch: tuple = (0.0, 80.0)   # 끝마디가 키 면과 이루는 각. 이보다 크면 손톱으로 누르게 됨
    key_top: float = 1.0              # 키 윗면 높이
    # 손 전체의 미세 이동: 고쳐 쥐지 않고도 손목·손바닥이 기기 위에서 조금 미끄러져 닿는 범위를 넓힌다.
    hand_shift: float = 0.045         # 최대 이동량 (손 길이 대비, 178mm 손에서 8mm)
    shift_cost: float = 2.0           # 최대로 이동했을 때 더해지는 불편도 합(관절 2개가 한계에 닿은 것과 같음)

    @property
    def L(self):
        h = self.hand_length
        return h * self.k_mc, h * self.k_pp, h * (self.k_dp - self.pad_back)


def _dev(x, neutral, lo, hi):
    """중립 자세에서 한계까지를 0~1로 본 편차의 제곱."""
    span = np.where(x >= neutral, hi - neutral, neutral - lo)
    return ((x - neutral) / span) ** 2


D_EDGE = np.arange(0.0, 61.0, 6.0)        # CMC에서 기기 가장자리까지의 수평 거리 격자
R_MAX = 130
GAMMA = np.arange(-60.0, 60.1, 4.0)       # 엄지 방위와 패드 방향의 차이(굽힘 평면 기울기 때문) 격자
ROLLS = (-60.0, -40.0, -20.0, 0.0, 20.0, 40.0, 60.0)


def reach_profile(p: ThumbParams, roll_deg=0.0):
    """table[edge, r, γ] = 수평 거리 r(mm), 방위 차 γ인 지점을 누르는 최소 불편도 합(들림+MCP+IP).
    닿지 못하면 inf."""
    L1, L2, L3 = p.L
    h = p.hand_length
    rho = np.radians(roll_deg)
    tm = np.radians(np.arange(p.mcp[0], p.mcp[1] + 0.01, 0.5))[:, None]
    ti = np.radians(np.arange(p.ip[0], p.ip[1] + 0.01, 0.5))[None, :]
    A = L2 * np.cos(tm) + L3 * np.cos(tm + ti)         # 중수골 축 방향 성분
    B = L2 * np.sin(tm) + L3 * np.sin(tm + ti)         # 굽힘 방향 성분
    Bz = B * np.cos(rho)
    zt = p.key_top + h * p.pad_thick + p.cmc_depth     # CMC 기준 패드 뼈 축 높이
    M = np.hypot(L1 + A, Bz)
    ok = M > zt
    eps = np.arcsin(np.clip(zt / M, -1, 1)) + np.arctan2(Bz, L1 + A)
    ce, se = np.cos(eps), np.sin(eps)
    fwd = (L1 + A) * ce + Bz * se
    lat = -B * np.sin(rho)
    r = np.hypot(fwd, lat)
    gam = np.degrees(np.arctan2(lat, fwd))
    e_deg = np.degrees(eps)
    pitch = np.degrees(np.arcsin(np.clip(-(np.cos(tm + ti) * se - np.sin(tm + ti) * np.cos(rho) * ce), -1, 1)))
    ok &= (e_deg >= p.elev[0]) & (e_deg <= p.elev[1])
    ok &= (pitch >= p.pad_pitch[0]) & (pitch <= p.pad_pitch[1])
    mcp_r, mcp_z = L1 * ce, L1 * se - p.cmc_depth
    a2, b2 = L2 * np.cos(tm), L2 * np.sin(tm)
    ip_r = np.hypot((L1 + a2) * ce + b2 * np.cos(rho) * se, b2 * np.sin(rho))
    ip_z = (L1 + a2) * se - b2 * np.cos(rho) * ce - p.cmc_depth
    cost = (_dev(e_deg, p.elev_neutral, *p.elev)
            + _dev(np.degrees(tm), p.mcp_neutral, *p.mcp)
            + _dev(np.degrees(ti), p.ip_neutral, *p.ip)) + 0 * ti
    table = np.full((len(D_EDGE), R_MAX + 1, len(GAMMA)), np.inf)
    rb = np.clip(np.rint(r).astype(int), 0, R_MAX)
    gb = np.clip(np.rint((gam - GAMMA[0]) / (GAMMA[1] - GAMMA[0])).astype(int), 0, len(GAMMA) - 1)
    for i, de in enumerate(D_EDGE):
        # 기기 위에 올라온 관절은 기기를 뚫을 수 없다
        good = ok & ((mcp_r < de) | (mcp_z >= h * p.mcp_half))
        good &= (ip_r < de) | (ip_z >= p.key_top + h * p.ip_half)
        c = np.where(good, cost, np.inf)
        np.minimum.at(table[i], (rb.ravel(), gb.ravel()), c.ravel())
    # 손 이동: 반경 방향으로 s mm 옮겨 닿는 경우를 비용과 함께 허용
    smax = int(round(h * p.hand_shift))
    out = table.copy()
    for s in range(1, smax + 1):
        pen = p.shift_cost * (s / smax) ** 2
        out[:, s:] = np.minimum(out[:, s:], table[:, :-s] + pen)
        out[:, :-s] = np.minimum(out[:, :-s], table[:, s:] + pen)
    return out


def key_discomfort(table, p: ThumbParams, cmc, az_neutral, keys, half_w, half_h):
    """오른손 기준. cmc: (G, 2), az_neutral: (G,) 도, keys: (K, 2).
    반환: 불편도 (G, K) — 관절 4개 편차 제곱의 평균(0=중립, 1=모든 관절이 한계). 닿지 못하면 inf."""
    d = keys - cmc[..., None, :]
    dist = np.hypot(d[..., 0], d[..., 1])
    az = np.degrees(np.arctan2(d[..., 1], -d[..., 0]))     # 안쪽(-x)이 0°, 위(+y)로 갈수록 +
    # CMC에서 키로 가는 선이 기기 외곽에 들어서는 지점까지의 거리
    with np.errstate(divide="ignore", invalid="ignore"):
        c = cmc[..., None, :]
        tx = np.where(c[..., 0] > half_w, (c[..., 0] - half_w) / -d[..., 0], 0.0)
        ty = np.where(c[..., 1] < -half_h, (-half_h - c[..., 1]) / d[..., 1], 0.0)
    d_edge = np.clip(np.nan_to_num(np.maximum(tx, ty), nan=0.0, posinf=1.0), 0, 1) * dist
    ie = np.clip(np.rint(d_edge / (D_EDGE[1] - D_EDGE[0])).astype(int), 0, len(D_EDGE) - 1)
    ir = np.clip(np.rint(dist).astype(int), 0, R_MAX)
    t = table[ie, ir]                                      # (G, K, nγ)
    daz = (az - az_neutral[..., None])[..., None] - GAMMA  # 엄지 자체의 방위 편차
    cost = np.where(np.abs(daz) > p.az_half, np.inf, t + (daz / p.az_half) ** 2)
    return cost.min(-1) / 4.0
