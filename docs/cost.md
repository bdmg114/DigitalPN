# 생산 단가 추정

[hardware.md](hardware.md)의 부품표와 케이스 STL 부피로 계산한 **추정치**다. 견적을 받은 값이 아니다.
가격은 2026년 11월에 검색한 유통사 페이지(DigiKey, LCSC 등)의 캐시이며, 같은 부품도 페이지마다 값이 달라 중간값을 골랐다.
환율은 1 USD = 1,350원으로 잡았다(FRED 2026-10-30 기준 1,334원에 약간의 여유).

## 요약

| 시나리오 | 대당 원가 (USD) | 대당 원가 (원) | 일회성 비용 (별도) |
|---|---|---|---|
| 시제품 10대 (소량 구매, JLCPCB 조립, 케이스 직접 FDM 출력) | 약 85~95 | **약 11.5~13만** | — |
| 1,000대 (케이스 MJF 출력) | 약 47 | **약 6.4만** | 인증 |
| 10,000대 (케이스 사출) | 약 35 | **약 4.7만** | 인증 + 금형 (대당 원가에 금형 상각 포함) |

- 원가의 절반 이상이 **디스플레이(Sharp LS027B7DH01, 약 $18)** 다. 단가를 낮추려면 이 부품의 대량 단가 협상이나 대체 패널 검토가 가장 크게 듣는다.
- 1,000대 규모에서는 케이스(MJF 약 $9)가 두 번째로 크다. 사출 금형은 수천 대 이상에서야 MJF보다 싸진다.
- 인건비(직접 조립 시간), 설계비, 펌웨어 개발비, 유통 마진, 부가세는 넣지 않았다.

## 1,000대 기준 내역

| 항목 | 단가 근거 | 대당 (USD) |
|---|---|---|
| 디스플레이 LS027B7DH01A | DigiKey 400개 단가 $17.85, Avnet 400개 $18~20 | 18.00 |
| ESP32-S3-MINI-1-N8 | LCSC 650개 이상 $3.29~3.33 | 3.30 |
| 앞면 택트 스위치 39개 (Alps SKRP 계열) | LCSC SKRPABE010 1,000개 $0.041~0.045 | 1.76 |
| 어깨 스위치 2개 (측면 누름) | 추정 $0.10 | 0.20 |
| 다이오드 41개 (1N4148WS) | 추정 $0.005 | 0.20 |
| 배터리 503450 1000 mAh, 보호회로 | 대량 견적 공개가 없음. 유사 셀 1,000개 $1.9 + 인증·커넥터 여유 | 3.00 |
| 충전 BQ24074 | LCSC $0.47~0.99, Farnell $1.39 | 0.80 |
| 벅 TPS62840 | LCSC $0.55(BGA)~1.11(VSON) | 0.80 |
| 연료 게이지 MAX17048 | LCSC 1,000개 $0.60~0.67 | 0.65 |
| 디스플레이 5 V 승압 (필요 시) | 추정 | 0.30 |
| USB-C, FPC 커넥터, 크리스털, LED, ESD, 수동소자 | 추정 | 1.00 |
| PCB 138 × 66 × 1.0 mm | 추정 (2~4층) | 1.20 |
| PCB 조립 (양면, 약 470 접점) | JLCPCB 접점당 $0.0016~0.0017 + 셋업·확장 부품 수수료 상각 | 1.80 |
| **코어 소계** | | **33.0** |
| 앞판·뒷판·어깨 캡 MJF PA12 (26.4 cm³, 약 27 g) | JLC3DP $0.275/g (2025년 말 가격, 2026년 7월 추가 인하 공지 있음) | 7.30 |
| 키매트 좌우 TPU (5.9 cm³) | 추정 | 2.00 |
| M2 나사 6 + 열압입 인서트 6 | 추정 | 0.15 |
| 최종 조립·펌웨어 기록·검사 | 대당 10분 내외 가정 | 2.00 |
| 포장 | 추정 | 0.70 |
| 불량·운송 여유 5% | | 2.26 |
| **합계** | | **약 47.4 (약 6.4만 원)** |

STL 부피는 `hardware/case/stl/`의 파일에서 계산했다: 앞판 8.58, 뒷판 17.59, 키매트 2.92 + 2.96, 어깨 캡 0.13 × 2 cm³.
손잡이형은 앞판 9.15 + 뒷판 29.83 cm³라 MJF 비용이 약 $3.5 늘어난다.

## 10,000대 (사출) 가정

| 항목 | 대당 (USD) |
|---|---|
| 코어 (디스플레이 $15로 협상, 나머지 부품·조립 10~25% 인하 가정) | 27.7 |
| 사출 부품 (앞판·뒷판 PC/ABS, 실리콘 키매트, 어깨 캡) | 1.2 |
| 금형 상각 (앞판·뒷판·키매트·어깨 캡, 합계 약 $20,000 가정 ÷ 10,000대) | 2.0 |
| 나사·조립·검사·포장 | 2.1 |
| 불량·운송 여유 5% | 1.7 |
| **합계** | **약 34.6 (약 4.7만 원)** |

손바닥 크기 2부품 케이스의 단일 캐비티 P20 금형은 공급사 자료에서 $4,000~10,000 범위로 나온다. 1,000대에서 사출로 가면 금형만 대당 약 $20(2.7만 원)이 붙어 MJF보다 비싸다.

## 시제품 10대

| 항목 | 대당 (USD) |
|---|---|
| 디스플레이 (DigiKey 1개 단가) | 27.6 |
| ESP32-S3 모듈 | 4.5 |
| 스위치 41개 (소량 단가 약 $0.10) | 4.1 |
| 배터리 (소매) | 8.0 |
| 전원 IC 4종 (소량 단가) | 7.6 |
| 다이오드·커넥터·수동소자 | 3.5 |
| PCB + 조립 (JLCPCB 10장, 양면 셋업·스텐실·확장 부품 수수료가 대부분) | 20.0 |
| 케이스 직접 FDM 출력 (PLA 약 32 g + TPU 약 7 g) + 나사 | 2.0 |
| **소계** | **약 77** |
| 배송·관세 10~20% | 8~15 |
| **합계** | **약 85~95 (약 11.5~13만 원)** |

케이스를 JLC3DP MJF로 맡기면 대당 약 $10이 더 든다.

## 일회성 비용

| 항목 | 메모 |
|---|---|
| 전파 인증 (KC 적합성평가, 수출 시 FCC/CE) | ESP32-S3-MINI-1 모듈은 자체 인증이 있지만 완제품 EMC 시험은 따로 필요하다. 금액은 시험소 견적으로 확인할 것 |
| 배터리 운송 인증 (UN38.3, IEC 62133) | 셀 공급사가 보유한 것을 쓰면 별도 비용이 거의 없다 |
| 사출 금형 | 10,000대 시나리오에 상각해 넣었다 |
| PCB 시제품 반복 | 위 시제품 비용 × 시제품 차수 |

## 판매가 감각

하드웨어 소매가는 보통 제조 원가의 2.5~4배로 잡는다(유통 마진, 반품, 지원, 개발비 회수). 1,000대 원가 6.4만 원이면 소매 16~25만 원, 10,000대 원가 4.7만 원이면 12~19만 원 수준이다.

## 원가를 줄이는 방향

1. **디스플레이**: 원가의 약 40~55%. 대량 구매 협상, 또는 같은 자리에 들어가는 더 싼 반사형 패널 검토. 전자종이는 [hardware.md](hardware.md) 6절의 이유로 권하지 않는다.
2. **전원 IC 통합**: 충전·벅·게이지 3칩($2.25)을 PMIC 하나로 묶거나, 게이지를 빼고 ADC 전압 추정으로 바꾸면 $0.6~1 줄어든다(정확도는 떨어진다).
3. **단면 조립**: 스위치는 앞면, 나머지는 뒷면이라 양면 조립이다. 뒷면 부품을 줄이거나 스위치만 수삽/리플로 한 번으로 묶으면 조립비가 준다.
4. **케이스**: 1,000대까지는 MJF, 수천 대 이상부터 사출. 손잡이형은 부피가 커서 MJF 단가가 오른다.

## 이 추정의 한계

- 가격은 검색 결과의 캐시 페이지에서 가져왔고 페이지마다 값이 달랐다. 발주 전에 실시간 견적으로 다시 확인해야 한다.
- 배터리, PCB, 수동소자, 사출 부품 단가는 공개 단가를 찾지 못해 가정한 값이다.
- 회로도가 아직 없어 부품 수(특히 수동소자와 디스플레이 승압 회로 필요 여부)가 확정되지 않았다.
- 디스플레이 리드타임이 28주로 표시된 유통사도 있어, 수량보다 공급 일정이 먼저 문제가 될 수 있다.

## 출처

- Sharp LS027B7DH01A — [DigiKey](https://azcus.digikey.com/en/products/detail/sharp-microelectronics/LS027B7DH01A/5054067), [Findchips](https://www.findchips.com/search/LS027)
- ESP32-S3-MINI-1-N8 — [LCSC C2913206](https://www.lcsc.com/product-detail/C2913206.html?s_z=t_HCTL)
- Alps SKRPABE010 — [LCSC C115360](https://www.lcsc.com/product-detail/C115360.html), [TME](https://www.tme.com/ca/en/details/skrpabe010/microswitches-tact/alps/)
- BQ24074 — [LCSC C54313](https://www.lcsc.com/product-detail/C54313.html), [Farnell](https://il.farnell.com/texas-instruments/bq24074rgtr/batt-charger-li-ion-1-5a-vqfn/dp/3008700RL)
- TPS62840 — [LCSC C2071139](https://www.lcsc.com/product-detail/C2071139.html)
- MAX17048 — [LCSC C2682616](https://www.lcsc.com/product-detail/C2682616.html?s_z=n_gd32)
- 503450 배터리 — [Alibaba 유사 셀](https://www.alibaba.com/product-introduction/High-Capacity-Li-Ion-Polymer-Battery_1600910076009.html), [Ormix](https://ormix.lv/en/product/11420)
- JLCPCB 조립비 — [가격 안내](https://jlcpcb.com/help/article/pcb-assembly-price), [FAQ](https://jlcpcb.com/help/article/98-pcb-assembly-faqs)
- JLC3DP MJF — [가격 인하 공지](https://jlc3dp.com/blog/drastic-material-price-cuts-and-adjusted-post-processing-service-fees), [2026년 7월 공지](https://jlc3dp.com/news/materials-finishing-pricing-update-july2026)
- 사출 금형 — [DEV Community](https://dev.to/china-sourcing-agents/injection-mold-tooling-costs-for-electronics-enclosures-16dl), [Haizol](https://www.haizol.com/blog/low-volume-injection-molding)
- 환율 — [FRED DEXKOUS](https://fred.stlouisfed.org/graph?g=7sEa)
