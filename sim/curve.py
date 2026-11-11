"""엄지 가동범위에 맞춰 행을 곡선으로 만든다: 열마다의 세로 이동량(stagger)을 시뮬레이션으로 최적화.

열의 가로 위치는 그대로라 기기 폭이 늘지 않는다.  사용: python3 curve.py  → curve.json
"""
import itertools
import json
from multiprocessing import Pool

import numpy as np

from model import split_layout, evaluate, HANDS
from run import WEIGHTS

PX, PY = 9.0, 10.0


def score(args):
    stagger, yc = args
    lay = split_layout(PX, PY, yc, stagger=stagger)
    if not lay.params["fits"]:
        return None
    res = evaluate(lay)
    return dict(stagger=[float(s) for s in stagger], yc=yc,
                score=sum(res[h]["eff_kpm"] * WEIGHTS[h] for h in HANDS),
                strain=sum(res[h]["discomfort"] * WEIGHTS[h] for h in HANDS),
                hands={h: dict(eff=res[h]["eff_kpm"], err=res[h]["err"], strain=res[h]["discomfort"],
                               worst=res[h]["worst"], unreach=res[h]["unreach"]) for h in HANDS})


def quad(a, b):
    """기울기 a(mm/열)와 곡률 b(mm/열²)로 만든 이동량. 평균은 0."""
    o = np.array([a * (i - 2) + b * (i - 2) ** 2 for i in range(5)])
    return tuple(np.round(o - o.mean(), 2))


if __name__ == "__main__":
    with Pool(3) as pool:
        base = score(((0, 0, 0, 0, 0), -6.0))
        # 1) 기울기 × 곡률 격자
        cands = [(quad(a, b), yc) for a, b in itertools.product(np.arange(-3, 3.1, 1.0), np.arange(-2, 2.1, 0.5))
                 for yc in (-6.0, -3.0)]
        res = [r for r in pool.map(score, cands, chunksize=2) if r]
        res.sort(key=lambda r: -r["score"])
        best = res[0]
        # 2) 열별 미세 조정 (좌표 하강)
        for _ in range(2):
            for i in range(5):
                trial = []
                for d in (-1.5, -0.75, 0.75, 1.5):
                    s = list(best["stagger"])
                    s[i] += d
                    trial.append((tuple(s), best["yc"]))
                for r in pool.map(score, trial):
                    if r and r["score"] > best["score"]:
                        best = r
    json.dump(dict(base=base, best=best, grid=res[:20]), open("curve.json", "w"), indent=1)
    for name, r in (("grid", base), ("curved", best)):
        print(name, r["stagger"], r["yc"], "score %.1f strain %.3f" % (r["score"], r["strain"]),
              {h: (round(v["eff"]), round(v["err"], 3), round(v["strain"], 2), round(v["worst"], 2)) for h, v in r["hands"].items()})
    print("top grid:", [(r["stagger"], r["yc"], round(r["score"], 1)) for r in res[:6]])
