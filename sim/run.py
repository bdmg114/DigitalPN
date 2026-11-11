"""설계 공간 탐색. 결과를 results.json 으로 저장한다.  사용: python3 run.py"""
import itertools
import json
import sys
from multiprocessing import Pool

import numpy as np

from model import split_layout, slab_layout, evaluate, HANDS

WEIGHTS = {"small": 0.25, "medium": 0.5, "large": 0.25}
MAX_W = 146.0          # "스마트폰보다 조금 작게"


def summarize(lay, res):
    out = dict(name=lay.name, shift=lay.shift, W=round(lay.W, 1), H=lay.H, **lay.params)
    out["score"] = sum(res[h]["eff_kpm"] * w for h, w in WEIGHTS.items())
    out["min_eff"] = min(res[h]["eff_kpm"] for h in HANDS)
    for h in HANDS:
        r = res[h]
        out[h] = {k: round(float(r[k]), 4) for k in ("raw_kpm", "eff_kpm", "err", "discomfort", "worst")}
        out[h].update(unreach=r["unreach"], regrips=r["regrips"], grips=r["grips"],
                      D=[None if not np.isfinite(d) else round(float(d), 3) for d in r["D"]])
    return out


def job(spec):
    kind, kw = spec
    if kind == "split":
        best = None
        kw = dict(kw)
        for yc in kw.pop("ycs", (-6.0, 0.0, 6.0)):   # 묶음의 세로 위치는 맞는 것 중 가장 좋은 것
            lay = split_layout(yc=yc, **kw)
            if not lay.params["fits"] or lay.W > MAX_W:
                continue
            s = summarize(lay, evaluate(lay))
            if best is None or s["score"] > best["score"]:
                best = s
        return best
    lay = slab_layout(**kw)
    return summarize(lay, evaluate(lay))


def specs():
    out = []
    for px, py, rot, R0 in itertools.product(
            (7.5, 8.0, 8.5, 9.0, 9.5), (7.5, 8.5, 9.5), (0, 15, 30), (None, 60.0)):
        out.append(("split", dict(px=px, py=py, rot=float(rot), R0=R0)))
    for px, py, lift in itertools.product((11.0, 12.0, 13.0, 14.0), (8.0, 9.0, 10.0), (0.0, 6.0, 12.0)):
        out.append(("slab", dict(px=px, py=py, lift=lift, H=70.0, name="wide")))
    for px, py, lift in itertools.product((5.5, 6.0, 6.5, 6.9), (5.5, 6.5, 7.5), (3.0, 10.0, 18.0)):
        out.append(("slab", dict(px=px, py=py, lift=lift, H=120.0, name="portrait")))
    return out


def refine_specs():
    """1차 탐색에서 경계에 걸린 변수(행 간격, 세로 위치)를 넓혀 다시 본다."""
    out = []
    for px, py, yc in itertools.product((9.0, 9.5), (9.5, 10.0, 10.5, 11.0), (-12.0, -9.0, -6.0, -3.0, 0.0, 4.0)):
        out.append(("split", dict(px=px, py=py, rot=0.0, R0=None, ycs=(yc,))))
    # 화면을 위로 올리고 좌우 묶음을 붙인 형태를 같은 조건(어깨 Shift)으로 비교
    for px, py, lift in itertools.product((9.0, 9.5, 10.0, 10.5, 11.0), (9.5, 10.0), (0.0, 6.0)):
        out.append(("slab", dict(px=px, py=py, lift=lift, H=70.0, name="wide", thumb_shift=False)))
    return out


if __name__ == "__main__":
    refine = "--refine" in sys.argv
    sp = refine_specs() if refine else specs()
    print(len(sp), "specs", file=sys.stderr)
    with Pool() as pool:
        res = []
        for i, r in enumerate(pool.imap(job, sp, chunksize=4)):
            if r:
                res.append(r)
            if i % 50 == 0:
                print(i, len(sp), file=sys.stderr, flush=True)
    if refine:
        res += json.load(open("results.json"))
    res.sort(key=lambda r: -r["score"])
    json.dump(res, open("results.json", "w"), ensure_ascii=False)
    for r in res[:15]:
        print(r["name"], {k: r[k] for k in ("px", "py", "rot", "R0", "yc", "lift", "W") if k in r},
              "score %.1f min %.1f" % (r["score"], r["min_eff"]),
              [(r[h]["unreach"], round(r[h]["err"], 3)) for h in HANDS])
