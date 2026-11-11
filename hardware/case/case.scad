// DigitalPN — 기준 케이스 (파라메트릭, 곡선형, 3D 프린팅용)
// 사용: openscad -D 'part="top"' -o top.stl case.scad
// part: "assembly" | "top" | "bottom" | "keymat_l" | "keymat_r" | "shoulder"
//
// 모양의 원칙
//  - 손에 닿는 모든 모서리를 둥글린다: 평면 모서리 R14, 뒷면 가장자리는 배 밑바닥처럼 6 mm에 걸쳐 말려 올라간다.
//  - 주머니: 튀어나온 것이 없다. 가장자리 두께가 얇아 미끄러져 들어가고, 키캡은 0.6 mm만 솟는다.
//  - FDM: 두 껍데기 모두 바깥 면을 바닥에 붙여 서포트 없이 출력한다. 그래서 곡면은 45°보다 눕지 않는다.
include <dpn_core.scad>

part = "assembly";

// ── 사용자가 바꿔도 되는 값 ──────────────────────────
process   = "fdm";  // "fdm": 45° 제한 곡면(서포트 불필요) | "sls": 완전한 원호 곡면(SLS·MJF·레진용)
wall      = 1.7;    // 옆벽 두께
clearance = 0.3;    // PCB와 벽 사이 틈
outer_r   = 14;     // 바깥 모서리 반경 (평면)
face_t    = 1.4;    // 앞판 두께
floor_t   = 1.6;    // 뒷판 두께
back_edge = 6.0;    // 뒷면 가장자리가 말려 올라가는 높이
back_cham = 2.5;    // 그중 바닥에서 45° 직선으로 올라가는 높이 (fdm)
front_edge = 1.0;   // 앞면 가장자리 모따기
cap_w     = 7.4;    // 키캡 윗면 폭
cap_h     = 8.4;    // 키캡 윗면 높이(세로)
cap_gap   = 0.2;    // 키캡과 구멍 사이 틈(한쪽)
cap_proud = 0.6;    // 키캡이 앞판 위로 솟는 높이 (주머니에서 눌림을 줄이려면 낮게)
mat_t     = 0.4;    // 키매트 연결 시트 두께 (TPU 권장)
nub_d     = 2.4;    // 스위치를 누르는 돌기 지름
win_margin = 0.5;   // 표시 영역 주변 창 여유(한쪽)
grip      = true;   // 뒷면 손가락 자리에 미끄럼 방지 홈
grip_depth = 0.6;   // 홈 깊이 (0.2 mm 적층 3겹)
grip_w    = 1.2;    // 홈 폭 (바닥면 브리지가 되므로 1.5 이하)
grip_pitch = 3.6;   // 홈 간격

// ── 유도 값 ─────────────────────────────────────────
$fn = 64;
eps = 0.01;
steps = 14;                         // 곡면을 나누는 단 수
out_w = pcb_w + 2 * (clearance + wall);
out_h = pcb_h + 2 * (clearance + wall);
mat_z = sw_h + 0.2;                 // 키매트 시트 아랫면
gap_z = mat_z + mat_t + 0.1;        // 앞판 안쪽 면
top_z = gap_z + face_t;             // 앞판 바깥 면
bot_z = -(pcb_t + back_depth + floor_t);
hole_w = cap_w + 2 * cap_gap;
hole_h = cap_h + 2 * cap_gap;

// 가장자리 단면: 바깥 면에서 d 만큼 들어온 높이에서 외곽이 얼마나 안으로 들어가는가
arc_r = (back_edge - back_cham) / sin(45);                 // fdm: 45°에서 시작해 수직으로 끝나는 원호
fdm_total = back_cham + arc_r * (1 - cos(45));
function back_inset(d) =
    d >= back_edge ? 0 :
    process == "sls" ? back_edge - sqrt(back_edge * back_edge - pow(back_edge - d, 2)) :
    d < back_cham ? fdm_total - d :
    arc_r * (1 - cos(asin((back_edge - d) / arc_r)));
function front_inset(d) = d >= front_edge ? 0 : front_edge - d;

module outline(inset = 0) { rrect(out_w - 2 * inset, out_h - 2 * inset, max(outer_r - inset, 0.6)); }

// z0..z1 사이를 단면 함수에 따라 쌓아 올린 덩어리. d0: z0에서의 바깥 면까지 거리, dir: z가 늘 때 d의 방향
module loft(z0, z1, extra = 0, back = true) {
    n = steps;
    for (i = [0 : n - 1]) {
        za = z0 + (z1 - z0) * i / n;
        zb = z0 + (z1 - z0) * (i + 1) / n;
        ia = (back ? back_inset(za - bot_z) : front_inset(top_z - za)) + extra;
        ib = (back ? back_inset(zb - bot_z) : front_inset(top_z - zb)) + extra;
        hull() {
            translate([0, 0, za]) linear_extrude(eps) outline(ia);
            translate([0, 0, zb - eps]) linear_extrude(eps) outline(ib);
        }
    }
}

module key_holes_2d() {
    for (s = [-1, 1]) for (c = caps())
        translate([col_x(s, c[0]), key_y(c[0], c[1], c[2])])
            rrect((c[2] - 1) * pitch_x + hole_w, hole_h, 1.2);
}

module top_shell() {
    difference() {
        union() {
            difference() {
                loft(0, top_z, back = false);
                translate([0, 0, -eps]) linear_extrude(gap_z + eps) outline(wall);
            }
            for (p = screw_pos) translate(p) cylinder(d = 4.6, h = gap_z + eps);   // PCB를 누르는 나사 기둥
        }
        translate([0, 0, gap_z - eps]) linear_extrude(face_t + 2 * eps) {
            rrect(disp_act_w + 2 * win_margin, disp_act_h + 2 * win_margin, 0.8);  // 디스플레이 창
            key_holes_2d();
        }
        for (p = screw_pos) translate(p) {
            translate([0, 0, -eps]) cylinder(d = screw_d, h = top_z + 2 * eps);
            translate([0, 0, top_z - 0.8]) cylinder(d1 = screw_d, d2 = 4.2, h = 0.8 + eps);   // 접시머리 자리
        }
    }
}

module edge_cut(x, w, h, zc, ydir) {
    translate([x, ydir * (out_h / 2 - 3), zc]) cube([w, 8, h], center = true);
}

// 뒷면 손가락 자리의 곡선 홈: 아래 바깥 모서리를 중심으로 한 동심 호 (손가락이 감기는 방향과 직각)
module grip_grooves() {
    flat = fdm_total + 1.5;                 // 평평한 뒷면 안쪽으로만
    translate([0, 0, bot_z - eps]) linear_extrude(grip_depth + eps) intersection() {
        outline(process == "sls" ? back_edge + 1.5 : flat);
        for (s = [-1, 1]) intersection() {
            translate([s * (out_w / 4 + 12), 0]) square([out_w / 2 - 24, out_h], center = true);   // 가운데는 비움
            translate([s * (out_w / 2 - 6), -out_h / 2 + 4])
                for (r = [14 : grip_pitch : 70]) difference() {
                    circle(r + grip_w / 2);
                    circle(r - grip_w / 2);
                }
        }
    }
}

module bottom_shell() {
    difference() {
        union() {
            difference() {
                loft(bot_z, 0);
                difference() {                                   // 속: 벽 두께를 유지하며 같은 곡면을 따라간다
                    loft(bot_z, eps, extra = wall);
                    translate([0, 0, bot_z - 1]) linear_extrude(floor_t + 1) outline(-1);
                }
            }
            for (p = screw_pos) translate([p[0], p[1], bot_z + floor_t - eps])   // PCB 받침 보스
                cylinder(d = 5.6, h = back_depth + eps);
        }
        for (p = screw_pos) translate([p[0], p[1], -pcb_t - insert_depth])
            cylinder(d = insert_d, h = insert_depth + eps);
        edge_cut(usb_x, usb_w, usb_h, usb_zc, -1);
        for (s = [-1, 1]) edge_cut(s * shoulder_x, shoulder_w, shoulder_h, shoulder_zc, 1);
        if (grip) grip_grooves();
    }
}

// 한쪽 키매트: 얇은 시트 위에 키캡이 솟아 있고, 아래에 스위치를 누르는 돌기가 있다.
module keymat(side) {
    translate([0, 0, mat_z]) linear_extrude(mat_t) offset(-1.5) offset(1.5 + (pitch_x - cap_w) / 2 - 0.3)
        for (c = caps()) translate([col_x(side, c[0]), key_y(c[0], c[1], c[2])])
            square([(c[2] - 1) * pitch_x + cap_w, cap_h], center = true);
    for (c = caps()) translate([col_x(side, c[0]), key_y(c[0], c[1], c[2]), mat_z + mat_t - eps])
        hull() {      // 윗면을 조금 좁혀 볼록한 느낌을 준다
            linear_extrude(eps) rrect((c[2] - 1) * pitch_x + cap_w, cap_h, 1.0);
            translate([0, 0, top_z + cap_proud - mat_z - mat_t - 0.6])
                linear_extrude(0.6) rrect((c[2] - 1) * pitch_x + cap_w - 1.2, cap_h - 1.2, 1.4);
        }
    for (k = switches()) translate([col_x(side, k[0]), k[1], sw_h])
        cylinder(d = nub_d, h = mat_z - sw_h + eps);
}

// 어깨 버튼 캡: 벽 구멍을 지나는 막대 + 안쪽 빠짐 방지 턱. 바깥 끝은 케이스 곡면과 같은 높이.
module shoulder_cap() {
    cube([shoulder_w - 0.4, wall + 1.6, shoulder_h - 0.4], center = true);
    translate([0, -(wall + 1.6) / 2, 0]) cube([shoulder_w + 2, 0.8, shoulder_h + 1.2], center = true);
}

module assembly() {
    core_mock();
    color("gainsboro") top_shell();
    color("slategray") bottom_shell();
    color("orange") for (s = [-1, 1]) keymat(s);
    color("orange") for (s = [-1, 1])
        translate([s * shoulder_x, out_h / 2 - back_inset(shoulder_zc - bot_z) - (wall + 1.6) / 2 + 0.2, shoulder_zc])
            shoulder_cap();
}

if (part == "top") rotate([180, 0, 0]) translate([0, 0, -top_z]) top_shell();   // 앞면을 바닥에 붙여 출력
else if (part == "bottom") translate([0, 0, -bot_z]) bottom_shell();           // 뒷면을 바닥에 붙여 출력
else if (part == "keymat_l") rotate([180, 0, 0]) translate([0, 0, -(top_z + cap_proud)]) keymat(-1);
else if (part == "keymat_r") rotate([180, 0, 0]) translate([0, 0, -(top_z + cap_proud)]) keymat(1);
else if (part == "shoulder") shoulder_cap();
else assembly();

echo(str("외형(mm): ", out_w, " x ", out_h, " x ", top_z - bot_z, " (+키캡 ", cap_proud, "), 가장자리 두께 ",
         top_z - bot_z - back_edge - front_edge));
