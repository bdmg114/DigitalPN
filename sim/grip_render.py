"""생성된 손잡이 곡면을 케이스 외형에 얹어 렌더링한다 (pyvista/VTK).

grip_gen.json 의 높이장을 case.scad 와 같은 외형(142 × 70, 평면 모서리 R14, 뒷면 가장자리 말림 6 mm)에 얹는다.
외형을 바깥에서 안쪽으로 줄어드는 둥근 사각형 고리들로 매개화해 곡면 하나로 그린다.

사용: python grip_render.py  → ../docs/img/grip-gen-render.png (뒷면), grip-gen-edge.png (두께),
      grip-gen-<이름>.png (시뮬레이션이 고른 보통 손 손가락 자세를 겹쳐 그림)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from scipy.interpolate import RegularGridInterpolator

import grip_gen as GG

HERE = Path(__file__).parent
IMG = HERE.parent / "docs" / "img"
HX, HY, R0 = 71.0, 35.0, 14.0
BOT, TOP = GG.Z_BACK, GG.Z_FRONT
SURFACE, INK2 = "#fcfcfb", "#52514e"
SHELL = np.array([0.80, 0.82, 0.85])
GRIPC = np.array([0.42, 0.62, 0.88])


def ring(i, n_long=70, n_short=34, n_arc=14):
    """옆 모서리에서 i만큼 안쪽으로 들어온 둥근 사각형 위의 점들 (항상 같은 개수)."""
    hx, hy, r = HX - i, HY - i, max(R0 - i, 0.05)
    pts = []
    corners = [(hx - r, hy - r, 0), (-(hx - r), hy - r, 90), (-(hx - r), -(hy - r), 180), ((hx - r), -(hy - r), 270)]
    for k, (cx, cy, a0) in enumerate(corners):
        for t in np.linspace(0, 90, n_arc, endpoint=False):
            th = np.radians(a0 + t)
            pts.append((cx + r * np.cos(th), cy + r * np.sin(th)))
        nxt = corners[(k + 1) % 4]
        a1 = np.radians(a0 + 90)
        p0 = np.array([cx + r * np.cos(a1), cy + r * np.sin(a1)])
        p1 = np.array([nxt[0] + r * np.cos(a1), nxt[1] + r * np.sin(a1)])
        n = n_long if k % 2 == 0 else n_short
        for t in np.linspace(0, 1, n, endpoint=False):
            pts.append(tuple(p0 + t * (p1 - p0)))
    pts.append(pts[0])
    return np.array(pts)


def back_mesh(H):
    """뒷면(가장자리 말림 + 손잡이) 곡면의 X, Y, Z 격자와 손잡이 높이."""
    f = RegularGridInterpolator((GG.FA, GG.FY), H, bounds_error=False, fill_value=0.0)
    insets = np.r_[np.linspace(0, GG.A0, 10), np.arange(GG.A0 + 0.75, HY - 0.2, 0.75), HY]
    R = [ring(i) for i in insets]
    X = np.array([r[:, 0] for r in R])
    Y = np.array([r[:, 1] for r in R])
    a = HX - np.abs(X)
    h = f(np.stack([a.ravel(), Y.ravel()], 1)).reshape(X.shape)
    curl = np.array([GG.EDGE_H - GG.EDGE_H * np.sqrt(max(0.0, 1 - ((GG.A0 - i) / GG.A0) ** 2)) if i < GG.A0 else 0.0
                     for i in insets])
    Z = BOT + curl[:, None] - h
    return X, Y, Z, h


def wall_mesh():
    r = ring(0)
    zs = np.linspace(BOT + GG.EDGE_H, TOP, 4)
    return np.repeat(r[None, :, 0], 4, 0), np.repeat(r[None, :, 1], 4, 0), np.repeat(zs[:, None], len(r), 1)


def surf(X, Y, Z, h=None):
    g = pv.StructuredGrid(X, Y, Z)
    g.point_data["h"] = (np.zeros_like(X) if h is None else h).ravel(order="F")
    return g


def front_mesh():
    R = [ring(i) for i in np.r_[0, 1.0, np.arange(2, HY - 0.2, 2.0), HY]]
    X = np.array([r[:, 0] for r in R])
    Y = np.array([r[:, 1] for r in R])
    return X, Y, np.full_like(X, TOP) - np.r_[1.0, np.zeros(len(R) - 1)][:, None]


CMAP = matplotlib.colors.LinearSegmentedColormap.from_list("grip", [SHELL, GRIPC * 0.95, GRIPC * 0.7])


def fingers(H, d, hand="medium"):
    """생성 시뮬레이션에서 그 손이 고른 쥐는 법으로 손가락 마디를 캡슐로 만든다 (오른손)."""
    s3 = (H, np.gradient(H, GG.FA, axis=0), np.gradient(H, GG.FY, axis=1), {})
    hl = GG.HANDS[hand]
    gr = GG.grasp(s3, hl, tuple(d["hands"][hand]["place"]))
    meshes = []
    for f in gr["fingers"]:
        J = [GG.to3(f["y"], *j) for j in f["J2"]]
        for i in range(3):
            r = GG.RADII[i] * hl
            p0, p1 = J[i], J[i + 1]
            c = pv.Cylinder(center=(p0 + p1) / 2, direction=p1 - p0, radius=r, height=np.linalg.norm(p1 - p0),
                            resolution=40)
            meshes += [c, pv.Sphere(radius=r, center=p0, theta_resolution=30, phi_resolution=20)]
        meshes.append(pv.Sphere(radius=GG.RADII[2] * hl, center=J[3], theta_resolution=30, phi_resolution=20))
    return meshes


def scene(p, H, d=None, hand=False):
    X, Y, Z, h = back_mesh(H)
    p.add_mesh(surf(X, Y, Z, h), scalars="h", cmap=CMAP, clim=[0, 6], show_scalar_bar=False, smooth_shading=True,
               specular=0.35, specular_power=30, ambient=0.18, diffuse=0.85)
    for M in (wall_mesh(), front_mesh()):
        p.add_mesh(surf(*M), color=SHELL, smooth_shading=True, specular=0.3, ambient=0.18)
    if hand and d is not None and d["name"] != "slim":
        for m in fingers(H, d):
            p.add_mesh(m, color="#e3b293", smooth_shading=True, specular=0.12, ambient=0.2)


def shot(H, path, cam, d=None, hand=False, size=(1400, 900), parallel=False, title=None, zoom=1.3):
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background(SURFACE)
    scene(p, H, d, hand)
    p.camera_position = cam
    if parallel:
        p.enable_parallel_projection()
    p.reset_camera(bounds=(-HX, HX, -HY, HY, BOT - 12, TOP))
    if parallel:
        p.camera.parallel_scale = 13.5
        p.camera.focal_point = (0, 0, -7)
        p.camera.position = (0, -400, -7)
    else:
        p.camera.zoom(zoom)
    if title:
        p.add_text(title, position="upper_left", font_size=11, color="#0b0b0b")
    p.enable_anti_aliasing("ssaa")
    p.screenshot(path)
    p.close()


BACK = [(120, -190, -150), (0, 0, -6), (0, 0, 1)]
HERO = [(-160, -150, -130), (25, 0, -10), (0, 0, 1)]
EDGE = [(0, -400, -6), (0, 0, -6), (0, 0, 1)]


def label(d):
    if d["name"] == "slim":
        return "slim case (no grip)  ·  12.3 mm"
    return "%s  ·  peak %.1f mm  ·  thickest %.1f mm  ·  load %.0f" % (d["name"], d["peak"], d["thick"], d["rel"]["0.3"])


def main():
    data = json.load(open(HERE / "grip_gen.json", encoding="utf-8"))
    cmp = {r["name"]: r for r in data["compare"]}
    designs = [dict(cmp["slim"], field=np.zeros((len(GG.FA), len(GG.FY))).tolist())] +               [dict(cmp[d["name"]], field=d["field"]) for d in data["designs"]]
    tmp = HERE / "_render"
    tmp.mkdir(exist_ok=True)
    tiles, edges = [], []
    for d in designs:
        H = np.array(d["field"])
        shot(H, tmp / ("back-%s.png" % d["name"]), BACK, d, size=(1200, 760))
        shot(H, tmp / ("edge-%s.png" % d["name"]), EDGE, d, size=(1800, 260), parallel=True)
        tiles.append((label(d), tmp / ("back-%s.png" % d["name"])))
        edges.append((d["name"], tmp / ("edge-%s.png" % d["name"])))
        if d["name"] != "slim":
            shot(H, IMG / ("grip-gen-%s.png" % d["name"]), HERO, d, hand=True, size=(1400, 880), zoom=1.15,
                 title=label(d) + "\nfingers: medium hand, grip chosen by the simulation")
    plt.rcParams.update({"figure.facecolor": SURFACE, "savefig.facecolor": SURFACE, "font.size": 9})
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.7))
    for ax, (t, f) in zip(axes.ravel(), tiles):
        ax.imshow(plt.imread(f))
        ax.set_title(t, loc="left", fontsize=9.5)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(IMG / "grip-gen-render.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(len(edges), 1, figsize=(11, 1.25 * len(edges) + 0.3))
    for ax, (t, f) in zip(axes, edges):
        ax.imshow(plt.imread(f))
        ax.text(0.0, 0.5, t, transform=ax.transAxes, fontsize=10, color=INK2, ha="right", va="center")
        ax.axis("off")
    fig.subplots_adjust(0.06, 0.02, 0.99, 0.98, 0, 0.1)
    fig.savefig(IMG / "grip-gen-edge.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
