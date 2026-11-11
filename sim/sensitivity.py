"""가정을 바꿔도 결론이 유지되는지 확인한다.  사용: python3 sensitivity.py"""
import json
from pathlib import Path

from model import split_layout, slab_layout, evaluate, TypingParams, HANDS
from run import WEIGHTS

results = json.load(open(Path(__file__).parent / "results.json"))


def first(name):
    return next(r for r in results if r["name"] == name)


w, p = first("wide"), first("portrait")
CAND = {
    "split v0.2 (9.0x10.0)": lambda: split_layout(9.0, 10.0, -6.0),
    "split v0.1 (9.0x9.5)": lambda: split_layout(9.0, 9.5, 4.75),
    "v0.2 + thumb Shift": lambda: split_layout(9.0, 10.0, -6.0, thumb_shift=True),
    "joined best": lambda: slab_layout(w["px"], w["py"], w["lift"], 70.0, "wide", thumb_shift=(w["shift"] == "thumb")),
    "portrait best": lambda: slab_layout(p["px"], p["py"], p["lift"], 120.0, "portrait"),
}
CASES = {
    "baseline": ({}, {}),
    "scatter 1.3 mm": (dict(sigma0=1.3), {}),
    "scatter 2.1 mm": (dict(sigma0=2.1), {}),
    "no posture slowdown": (dict(kappa=0.0, lam=0.0), {}),
    "strong posture effect": (dict(kappa=1.2, lam=1.2), {}),
    "no hand shift": ({}, dict(hand_shift=0.0001)),
    "hand shift 12 mm": ({}, dict(hand_shift=0.0675)),
    "stiff joints (-15%)": ({}, dict(mcp=(0.0, 48.0), ip=(-8.0, 68.0), az_half=22.5, elev=(8.0, 44.0))),
}

if __name__ == "__main__":
    out = {}
    print("%-24s" % "", *["%-22s" % c[:22] for c in CAND])
    for cname, (tkw, hkw) in CASES.items():
        row = {}
        for name, mk in CAND.items():
            res = evaluate(mk(), TypingParams(**tkw), **hkw)
            row[name] = dict(score=sum(res[h]["eff_kpm"] * WEIGHTS[h] for h in HANDS),
                             unreach=sum(res[h]["unreach"] for h in HANDS),
                             small=res["small"]["eff_kpm"], err=res["medium"]["err"])
        out[cname] = row
        print("%-24s" % cname, *["%5.0f (unreach %2d)      " % (v["score"], v["unreach"]) for v in row.values()])
    json.dump(out, open(Path(__file__).parent / "sensitivity.json", "w"), indent=1)
