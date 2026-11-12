# 출력용 STL

`case.scad`에서 뽑은 파일이다. 치수를 바꾸면 다시 뽑아야 한다(`docs/case.md` 참조). 단위는 mm이고, 각 파일은 출력 방향 그대로 놓여 있다.

| 파일 | 수량 | 재질 | 크기 (mm) |
|---|---|---|---|
| `dpn-top.stl` | 1 | PLA / PETG | 142 × 70 × 4.1 |
| `dpn-bottom.stl` | 1 | PLA / PETG | 142 × 70 × 8.2 |
| `dpn-keymat_l.stl`, `dpn-keymat_r.stl` | 각 1 | TPU 95A | 44.4 × 48.4 × 2.7 |
| `dpn-shoulder.stl` | 2 | PLA / PETG | 12 × 4.6 × 3.7 |
| `dpn-bottom-sls.stl` | (대체) | SLS · MJF · 레진 | 142 × 70 × 8.2 |

`dpn-bottom-sls.stl`은 뒷면 가장자리가 완전한 원호인 뒷판으로, FDM에서는 서포트가 필요하다. FDM이면 `dpn-bottom.stl`을 쓴다.
