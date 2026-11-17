# 출력용 STL

`case.scad`에서 뽑은 파일이다. 치수를 바꾸면 다시 뽑아야 한다(`docs/case.md` 참조). 단위는 mm이고, 각 파일은 출력 방향 그대로 놓여 있다.

| 파일 | 수량 | 재질 | 크기 (mm) |
|---|---|---|---|
| `dpn-top.stl` | 1 | PLA / PETG | 142 × 70 × 4.1 |
| `dpn-bottom.stl` | 1 | PLA / PETG | 142 × 70 × 8.2 |
| `dpn-keymat_l.stl`, `dpn-keymat_r.stl` | 각 1 | TPU 95A | 44.4 × 48.4 × 2.7 |
| `dpn-shoulder.stl` | 2 | PLA / PETG | 12 × 4.6 × 3.7 |
| `dpn-bottom-sls.stl` | (대체) | SLS · MJF · 레진 | 142 × 70 × 8.2 |
| `dpn-grip-top.stl` | (손잡이형 앞판) | PLA / PETG, 서포트 필요 | 142 × 70 × 5.5 |
| `dpn-gripG4-bottom.stl` | (손잡이형 뒷판, 생성 곡면 예산 4 mm) | PLA / PETG, 서포트 필요 | 142 × 70 × 10.3 |
| `dpn-gripG7-bottom.stl` | (손잡이형 뒷판, 생성 곡면 예산 7 mm, 기본) | PLA / PETG, 서포트 필요 | 142 × 70 × 11.6 |
| `dpn-gripG10-bottom.stl` | (손잡이형 뒷판, 생성 곡면 예산 10 mm) | PLA / PETG, 서포트 필요 | 142 × 70 × 13.2 |

`dpn-bottom-sls.stl`은 뒷면 가장자리가 완전한 원호인 뒷판으로, FDM에서는 서포트가 필요하다. FDM이면 `dpn-bottom.stl`을 쓴다.

손잡이형은 `dpn-top.stl`·`dpn-bottom.stl` 대신 `dpn-grip-top.stl`과 `dpn-gripG4/G7/G10-bottom.stl` 중 하나를 쓰고 (뒷판은 열린 쪽이 바닥을 향하게 놓여 있다), 키매트와 어깨 캡은 같은 것을 쓴다. 키매트는 좌우가 다르다(왼쪽에 탭 키).

손잡이 곡면은 쥐기 시뮬레이션이 생성한 것이다(`sim/grip_gen.py`, `docs/case.md` 3절).

## Bambu Lab A1용 출력판 (`a1/`)

A1(256 × 256 mm) 판에 맞게 부품을 묶어 둔 파일이다. 재질과 서포트 설정이 같은 것끼리 모았으므로 판 하나가 출력 한 번이다. `python plates.py`로 다시 만든다(위 STL을 다시 뽑았으면 함께 다시 돌린다).

| 파일 | 들어 있는 것 | 재질 | 서포트 |
|---|---|---|---|
| `a1-1-pla-case.stl` | 기준 케이스 앞판 · 뒷판 · 어깨 캡 × 2 | PLA / PETG | 없음 |
| `a1-2-tpu-keymat.stl` | 키매트 좌 · 우 | TPU 95A | 없음 |
| `a1-3-pla-grip.stl` (선택) | 손잡이형 앞판(오른쪽, 세로) + 뒷판 G4 · G7 · G10 (판 앞쪽부터) | PLA / PETG | 필요 (바닥에서만) |

- 기준 케이스 목업은 1 · 2번, 두 번이면 끝난다. 손잡이형까지 비교하려면 3번을 더한다(키매트 · 어깨 캡은 같이 쓴다).
- Bambu Studio에서 STL 하나가 객체 하나로 들어온다. 부품마다 설정을 바꾸려면 우클릭 → 분할 → 객체로 분할.
- TPU는 AMS lite로 넣지 말고 뒤쪽 외부 스풀 홀더로 바로 넣는다.
- 3번 판: 서포트 켜기, 유형 tree(auto), "빌드 플레이트에서만". G4 · G7 · G10은 겉으로 구분이 어려우니 떼어 낼 때 안쪽에 표시해 둔다.

## 디바이스마트안 / 스위치 높이 2.5 mm (`devicemart/`)

SKRPABE010의 실제 높이(2.5 mm)에 맞춰 `sw_h=2.5`로 뽑은 앞판이다. 뒷판·키매트·어깨 캡은 위 파일을 그대로 쓴다. 근거는 `docs/devicemart.md`.

| 파일 | 대신하는 파일 | 크기 (mm) |
|---|---|---|
| `devicemart/dpn-top-sw25.stl` | `dpn-top.stl` | 142 × 70 × 4.6 |
| `devicemart/dpn-grip-top-sw25.stl` | `dpn-grip-top.stl` | 142 × 70 × 6.0 |
