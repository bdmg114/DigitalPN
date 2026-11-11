// DigitalPN — Core Interface v0.2  (v0.1 대비: 행 간격 9.5→10.0, 키 묶음을 10 mm 아래로. 근거: docs/simulation.md)
// 케이스가 지켜야 하는 "코어(PCB 조립체)"의 치수 계약. 단위 mm.
// 원점: PCB 중심, PCB 앞면(키/디스플레이 면)이 z=0, +z가 사용자 쪽, +y가 위(어깨 버튼 쪽).
// 이 파일의 값은 docs/hardware.md 의 표와 1:1로 일치해야 한다.

// ── PCB ──────────────────────────────────────────────
pcb_w = 138;   pcb_h = 66;   pcb_t = 1.0;   pcb_r = 6;

// ── 나사 (M2, 앞면에서 체결 → 뒷판 보스의 인서트) ─────
screw_pos = [[-65, 29], [65, 29], [-65, -29], [65, -29], [-25, -29], [25, -29]];
screw_d = 2.2;          // 관통 구멍
insert_d = 3.2;         // M2 열압입 인서트 하혈
insert_depth = 4.0;

// ── 디스플레이 베이 (세로 방향 2.7" 메모리 LCD 기준) ──
disp_mod_w = 42.82;  disp_mod_h = 62.8;  disp_mod_t = 1.9;  // 모듈+양면테이프
disp_act_w = 35.28;  disp_act_h = 58.8;                      // 유효 표시 영역
disp_bay_w = 44;     disp_bay_h = 64;                        // 다른 패널용 최대 허용 영역

// ── 키 격자 (좌우 각 5열 × 4행) ──────────────────────
pitch_x = 9.0;   pitch_y = 10.0;
key_x0 = 28;     // 디스플레이에 가장 가까운 열의 중심 |x|
key_y0 = 9;      // 맨 윗행 중심 y
cols = 5;  rows = 4;
sw_h = 2.0;      // 스위치 높이(액추에이터 포함)

function col_x(side, i) = side * (key_x0 + i * pitch_x);   // side: -1 왼쪽, +1 오른쪽, i: 0=안쪽
function row_y(r) = key_y0 - r * pitch_y;                  // r: 0=윗행

// 4행(r=3)은 안쪽 3칸이 스페이스 바(스위치 2개 병렬), 바깥 2칸은 단독 키
space_cols = [0, 2];                 // 스페이스 바 아래 스위치가 놓이는 열
// 키캡 목록: [열 중심 i(실수), 행 r, 폭(칸 수)]
function caps() = concat(
    [for (r = [0:2]) for (i = [0:cols-1]) [i, r, 1]],
    [[1, 3, 3], [3, 3, 1], [4, 3, 1]]);
// 스위치 목록: [i, r]
function switches() = concat(
    [for (r = [0:2]) for (i = [0:cols-1]) [i, r]],
    [for (i = space_cols) [i, 3]], [[3, 3], [4, 3]]);

// ── 가장자리 부품 (PCB 뒷면 실장) ────────────────────
usb_x = 0;           usb_w = 9.4;   usb_h = 3.6;   usb_zc = -(pcb_t + 1.6);  // 아래 모서리, USB-C
shoulder_x = 50;     shoulder_w = 10;  shoulder_h = 3.4;  shoulder_zc = -(pcb_t + 1.8); // 위 모서리 좌우
// 뒷면 부품 높이 한계: 배터리 503450 (5.0mm) + 여유
back_depth = 5.6;
batt = [34, 50, 5.0];   batt_pos = [0, 4];
// 안테나 금지 구역(뒷면, 위 모서리): 금속·배터리·손가락 받침을 두지 말 것
ant_keepout = [[24, 25], [40, 33]];  // [x0,y0],[x1,y1]

// ── 참고용 코어 목업 ─────────────────────────────────
module rrect(w, h, r) { offset(r) square([w - 2*r, h - 2*r], center = true); }

module core_mock() {
    color("darkgreen") translate([0, 0, -pcb_t]) linear_extrude(pcb_t)
        difference() { rrect(pcb_w, pcb_h, pcb_r); for (p = screw_pos) translate(p) circle(d = screw_d, $fn = 24); }
    color("silver") linear_extrude(disp_mod_t) square([disp_mod_w, disp_mod_h], center = true);
    color("white") translate([0, 0, disp_mod_t]) linear_extrude(0.02) square([disp_act_w, disp_act_h], center = true);
    color("dimgray") for (s = [-1, 1]) for (k = switches())
        translate([col_x(s, k[0]), row_y(k[1]), 0]) linear_extrude(sw_h) square([4.2, 3.2], center = true);
    color("steelblue") translate([batt_pos[0], batt_pos[1], -pcb_t - batt[2] - 0.3])
        linear_extrude(batt[2]) square([batt[0], batt[1]], center = true);
}
