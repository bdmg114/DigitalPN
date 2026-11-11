// DigitalPN — 기준 케이스 (파라메트릭)
// 사용: openscad -D 'part="top"' -o top.stl case.scad
// part: "assembly" | "top" | "bottom" | "keymat_l" | "keymat_r" | "shoulder"
include <dpn_core.scad>

part = "assembly";

// ── 사용자가 바꿔도 되는 값 ──────────────────────────
wall      = 1.7;    // 옆벽 두께
clearance = 0.3;    // PCB와 벽 사이 틈
outer_r   = 8;      // 바깥 모서리 반경
face_t    = 1.4;    // 앞판 두께
floor_t   = 1.4;    // 뒷판 두께
cap_w     = 7.4;    // 키캡 윗면 폭
cap_h     = 7.9;    // 키캡 윗면 높이(세로)
cap_gap   = 0.2;    // 키캡과 구멍 사이 틈(한쪽)
cap_proud = 1.0;    // 키캡이 앞판 위로 솟는 높이
mat_t     = 0.4;    // 키매트 연결 시트 두께 (TPU 권장)
nub_d     = 2.4;    // 스위치를 누르는 돌기 지름
win_margin = 0.5;   // 표시 영역 주변 창 여유(한쪽)
grip_depth = 0;     // >0 이면 뒷판 좌우에 손가락 걸이 융기 추가 (mm)

// ── 유도 값 ─────────────────────────────────────────
$fn = 48;
eps = 0.01;
out_w = pcb_w + 2 * (clearance + wall);
out_h = pcb_h + 2 * (clearance + wall);
in_w = pcb_w + 2 * clearance;
in_h = pcb_h + 2 * clearance;
in_r = max(outer_r - wall, 0.5);
mat_z = sw_h + 0.2;                 // 키매트 시트 아랫면
gap_z = mat_z + mat_t + 0.1;        // 앞판 안쪽 면
top_z = gap_z + face_t;             // 앞판 바깥 면
bot_z = -(pcb_t + back_depth + floor_t);
hole_w = cap_w + 2 * cap_gap;
hole_h = cap_h + 2 * cap_gap;

module key_holes_2d(grow = 0) {
    for (s = [-1, 1]) for (c = caps())
        translate([col_x(s, c[0]), row_y(c[1])])
            rrect((c[2] - 1) * pitch_x + hole_w + 2 * grow, hole_h + 2 * grow, 1.2);
}

module top_shell() {
    difference() {
        union() {
            difference() {
                linear_extrude(top_z) rrect(out_w, out_h, outer_r);
                translate([0, 0, -eps]) linear_extrude(gap_z + eps) rrect(in_w, in_h, in_r);
            }
            // PCB를 누르는 나사 기둥
            for (p = screw_pos) translate(p) cylinder(d = 4.6, h = gap_z + eps);
        }
        // 디스플레이 창
        translate([0, 0, gap_z - eps]) linear_extrude(face_t + 2 * eps)
            rrect(disp_act_w + 2 * win_margin, disp_act_h + 2 * win_margin, 0.8);
        // 디스플레이 모듈이 들어갈 자리(앞판 안쪽은 건드리지 않음)
        // 키 구멍
        translate([0, 0, gap_z - eps]) linear_extrude(face_t + 2 * eps) key_holes_2d();
        // 나사 구멍 + 접시머리 자리
        for (p = screw_pos) translate(p) {
            translate([0, 0, -eps]) cylinder(d = screw_d, h = top_z + 2 * eps);
            translate([0, 0, top_z - 0.8]) cylinder(d1 = screw_d, d2 = 4.2, h = 0.8 + eps);
        }
    }
}

module edge_cut(x, w, h, zc, ydir) {
    translate([x, ydir * (out_h / 2 - wall / 2 - clearance / 2), zc])
        cube([w, wall + clearance + 2, h], center = true);
}

module bottom_shell() {
    difference() {
        union() {
            difference() {
                translate([0, 0, bot_z]) linear_extrude(-bot_z) rrect(out_w, out_h, outer_r);
                translate([0, 0, bot_z + floor_t]) linear_extrude(-bot_z) rrect(in_w, in_h, in_r);
            }
            // PCB 받침 보스 (열압입 인서트)
            for (p = screw_pos) translate([p[0], p[1], bot_z + floor_t - eps])
                cylinder(d = 5.6, h = back_depth + eps);
            if (grip_depth > 0) for (s = [-1, 1])
                translate([s * (out_w / 2 - 14), 0, bot_z]) scale([1, 2.2, grip_depth / 6])
                    sphere(d = 12);
        }
        for (p = screw_pos) translate([p[0], p[1], -pcb_t - insert_depth])
            cylinder(d = insert_d, h = insert_depth + eps);
        edge_cut(usb_x, usb_w, usb_h, usb_zc, -1);
        for (s = [-1, 1]) edge_cut(s * shoulder_x, shoulder_w, shoulder_h, shoulder_zc, 1);
        if (grip_depth > 0) translate([0, 0, bot_z - 20]) cube([out_w * 2, out_h * 2, 40 - 2 * eps], center = true);
    }
}

// 한쪽 키매트: 얇은 시트 위에 키캡이 솟아 있고, 아래에 스위치를 누르는 돌기가 있다.
module keymat(side) {
    x_in = key_x0 - pitch_x / 2 + 0.3;
    x_out = key_x0 + (cols - 1) * pitch_x + pitch_x / 2 - 0.3;
    y_top = row_y(0) + pitch_y / 2 - 0.3;
    y_bot = row_y(rows - 1) - pitch_y / 2 + 0.3;
    translate([0, 0, mat_z]) linear_extrude(mat_t)
        translate([side * (x_in + x_out) / 2, (y_top + y_bot) / 2]) rrect(x_out - x_in, y_top - y_bot, 1);
    for (c = caps()) translate([col_x(side, c[0]), row_y(c[1]), mat_z + mat_t - eps])
        hull() {
            linear_extrude(eps) rrect((c[2] - 1) * pitch_x + cap_w, cap_h, 1.0);
            translate([0, 0, top_z + cap_proud - mat_z - mat_t - 0.6])
                linear_extrude(0.6) rrect((c[2] - 1) * pitch_x + cap_w - 0.8, cap_h - 0.8, 1.0);
        }
    for (k = switches()) translate([col_x(side, k[0]), row_y(k[1]), sw_h])
        cylinder(d = nub_d, h = mat_z - sw_h + eps);
}

// 어깨 버튼 캡: 벽 구멍을 지나는 막대 + 안쪽 빠짐 방지 턱
module shoulder_cap() {
    cube([shoulder_w - 0.4, wall + 1.6, shoulder_h - 0.4], center = true);
    translate([0, -(wall + 1.6) / 2, 0]) cube([shoulder_w + 2, 0.8, shoulder_h + 1.2], center = true);
}

module assembly() {
    core_mock();
    color("gainsboro", 0.9) top_shell();
    color("gray") bottom_shell();
    color("orange") for (s = [-1, 1]) keymat(s);
    color("orange") for (s = [-1, 1])
        translate([s * shoulder_x, out_h / 2 - wall / 2 + 0.6, shoulder_zc]) shoulder_cap();
}

if (part == "top") rotate([180, 0, 0]) translate([0, 0, -top_z]) top_shell();   // 앞판을 바닥에 붙여 출력
else if (part == "bottom") translate([0, 0, -bot_z]) bottom_shell();
else if (part == "keymat_l") rotate([180, 0, 0]) translate([0, 0, -(top_z + cap_proud)]) keymat(-1);
else if (part == "keymat_r") rotate([180, 0, 0]) translate([0, 0, -(top_z + cap_proud)]) keymat(1);
else if (part == "shoulder") shoulder_cap();
else assembly();

echo(str("외형(mm): ", out_w, " x ", out_h, " x ", top_z - bot_z, " (+키캡 ", cap_proud, ")"));
