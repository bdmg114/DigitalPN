# 부품 주문 리스트 (소량, 한국 배송)

[README의 검증 계획](../README.md#검증-계획) 단계별로 필요한 부품과, **1개~수십 개 단위로 한국까지 보내 주는** 국내·해외 판매처를 정리했다.
부품 선정 근거는 [hardware.md](hardware.md), 원가는 [cost.md](cost.md)에 있다.

가격·재고는 2026년 11월 검색 결과의 캐시 값이다. 페이지마다 값이 달랐고 시간이 지나면 바뀌므로 **주문 전에 실시간 페이지에서 다시 확인**한다.
국내 쇼핑몰(디바이스마트, 엘레파츠, ICbanQ 등)은 검색으로 해당 품번의 판매 페이지를 찾지 못해 재고·가격을 확인하지 못했다. 각 사이트에서 품번으로 직접 검색해 볼 것.

## 판매처별 한국 배송 조건

| 판매처 | 소량 주문 | 한국 배송비 | 메모 |
|---|---|---|---|
| [DigiKey Korea](https://www.digikey.kr/en/help-support/delivery-information/delivery-time-and-cost) | 1개부터 | ₩60,000 이상 무료, 미만 ₩20,000 | 원화 결제, 보통 3~4일 도착. 마켓플레이스 품목은 무료배송 계산에서 빠진다 |
| Mouser Korea ([mouser.kr](https://www.mouser.kr/)) | 1개부터 | ₩60,000($50) 이상 대부분 무료 | FCA 조건이라 관부가세·통관 수수료는 받을 때 낸다 |
| [LCSC](https://www.lcsc.com/faqs/shipping-delivering/customs-duties-taxes) | 1개부터(수동소자는 릴 단위가 아니라 소량 묶음) | 결제 화면에서 계산 | FCA/EXW. 관부가세는 구매자 부담. JLCPCB 조립과 부품 번호를 공유한다 |
| [JLCPCB](https://jlcpcb.com/help/article/how-much-does-shipping-cost) | PCB 5장, 조립 2장부터 | 견적 화면에서 무게·국가로 계산 | 2026-10-01 ~ 2027-02-05 DHL 수요 할증 기간 |
| [TME](https://www.tme.com/) (폴란드) | 1개부터 | 결제 화면에서 계산 | Alps SKRPABE010 재고 보유(검색 시점 5,088개) |
| The Pi Hut / Pimoroni (영국) | 1개부터 | 국제 배송 있음 | Adafruit 브레이크아웃 재고가 미국 본사보다 나은 경우가 있다 |
| Adafruit (미국) | 1개부터 | 국제 배송 있음 | 미국발은 면세 한도가 $200 |
| AliExpress | 1개부터 | 대부분 무료~소액 | 느리고 정품 보장이 약하다. 나사·인서트·필라멘트·만능기판 같은 소모품에만 쓴다 |
| 국내 (디바이스마트, 엘레파츠, ICbanQ, 메카솔루션) | 1개부터 | 국내 택배 | 관세 걱정이 없다. **리튬 배터리는 국내에서 산다**(아래 주의 참조) |

### 통관 주의

- 자가사용 물품은 물품가 **$150 이하(미국발 $200 이하)** 면 목록통관으로 관부가세가 면제된다. 넘으면 초과분이 아니라 **전체**에 관세·부가세가 붙는다.
- **같은 판매자에게 같은 날 산 물건을 나눠 들여오면 합산**된다. 배송대행지에서 합배송할 때도 합계를 먼저 계산한다.
- 전자부품이 목록통관 대상인지는 품목 분류에 따라 다를 수 있다. 확실하지 않으면 관세청 고객센터(125)에 품목과 금액으로 문의한다.
- 개인통관고유부호를 미리 발급받아 둔다.
- **리튬폴리머 배터리 단품은 항공 운송 제한 때문에 해외 소매점 대부분이 국제 배송을 하지 않거나 막는다.** 국내에서 사는 것이 현실적이다.

## 0단계: 타건 목업

기준 케이스 출력 + 스위치를 얹은 만능기판 + 개발보드로 USB 키보드처럼 동작시키는 단계. 2벌(분할형·붙임형) 기준.

| 부품 | 수량 | 추천 판매처 | 가격 메모 |
|---|---|---|---|
| 택트 스위치 Alps **SKRPABE010** (4 × 3 mm, 저하중) | 100 | TME, DigiKey(검색 시점 품절·백오더, 리드타임 20주) | TME 1개 약 $0.20. 0.7 / 1.0 / 1.6 N 비교용으로 같은 SKRP 계열의 다른 하중품도 20개씩 |
| 대체 스위치 Same Sky **TS20-42-25-WT-160-SMT-TR** | 100 | DigiKey (재고 2만 개 이상) | 1개 $0.21, 25개 $0.17. SKRP를 못 구할 때 |
| 측면 누름 택트 스위치 (어깨 버튼) | 10 | DigiKey / LCSC | 소량 약 $0.1~0.3 |
| ESP32-S3 개발보드 **ESP32-S3-DevKitM-1-N8** (본 설계와 같은 MINI-1 모듈) | 2 | DigiKey, Adafruit, LCSC | Future Electronics 1개 $19.21. LCSC 표시가는 페이지마다 달랐다 |
| 다이오드 1N4148 (만능기판용 THT) | 100 | 국내 쇼핑몰, LCSC | 소액 |
| 만능기판 (양면, 2.54 mm), 에나멜선·점퍼선 | 각 2~3 | 국내 쇼핑몰, AliExpress | SMD 스위치를 얹으려면 SMD 변환 기판이나 직접 그린 간단한 PCB(JLCPCB 5장)가 편하다 |
| M2 열압입 인서트 (바깥지름 3.2 mm, 길이 3~4 mm) | 100 | CNC Kitchen(West3D·Prusa·3DJake), AliExpress | CNC Kitchen M2×3 100개 $24. AliExpress 제품은 바깥지름·권장 구멍 지름을 판매자 도면으로 확인 |
| M2 × 6 mm 접시머리 나사 | 50 | 국내 철물·볼트 쇼핑몰, AliExpress | 소액 |
| PLA 또는 PETG 필라멘트, TPU 95A 필라멘트 | 각 1롤 | 국내 3D 프린팅 쇼핑몰 | 케이스 1벌에 PLA 약 32 g + TPU 약 7 g |

## 1단계: 개발보드 시제품

개발보드 + 메모리 LCD + 키 PCB로 키→화면 지연, 한글 조합, 저널 기록, 전원 차단 복구를 확인하는 단계. 전원부는 브레이크아웃 보드로 대신한다.

| 부품 | 수량 | 추천 판매처 | 가격 메모 |
|---|---|---|---|
| **Adafruit SHARP Memory Display Breakout 2.7" 400×240** (Adafruit 4694, LS027B7DH01 탑재) | 2 | The Pi Hut, Pimoroni, Cool Components(영국), DigiKey, Adafruit | 영국 판매처 £36.50~43.70. 3 V 레귤레이터·5 V 승압·레벨 변환이 들어 있어 ESP32에 바로 연결된다. **재고가 판매처마다 들쭉날쭉하고 단종 표시한 곳(Botland)도 있다** |
| 대안: Tindie "SIKTEC Sharp Memory LCD 2.7" 보드 | 1~2 | [Tindie](https://www.tindie.com/products/siktec/new-sharp-memory-lcd-27inch-400x240-display-ls027/) | Adafruit 보드 품절 시 |
| Adafruit **bq24074** USB/DC/태양광 리튬 충전 브레이크아웃 | 1~2 | Adafruit, DigiKey, Mouser | 본 설계와 같은 충전 IC. 전원 경로 동작 확인용 |
| Adafruit **MAX17048** 연료 게이지 (STEMMA QT) | 1~2 | Adafruit, DigiKey, Mouser | 본 설계와 같은 게이지 IC, I²C |
| TI **TPS62840-1** 평가 보드 (YBGEVM56 또는 DLCEVM55) | 0~1 | DigiKey | 약 $59. 대기 전류를 미리 재 볼 때만. 1단계에서는 개발보드의 LDO로 충분하다 |
| 리튬폴리머 **503450** 1000 mAh, 보호회로 내장, JST-PH 2.0 | 2 | **국내 쇼핑몰** | 커넥터 극성이 브레이크아웃과 맞는지 확인(제조사마다 반대인 경우가 있다) |
| 키 PCB (스위치 39 + 다이오드만 올린 기판) | 5장 | JLCPCB | 2층, 조립 없이 직접 납땜 |

## 2단계: 코어 PCB v0.1

본 설계의 일체형 PCB. 시제품 10대 기준([cost.md 시제품 10대](cost.md#시제품-10대)). JLCPCB 조립을 쓰면 대부분 부품이 LCSC 재고에서 자동으로 채워지므로, **LCSC에 없는 부품만 따로 사서 JLCPCB로 보내거나(위탁 부품) 받아서 직접 납땜**한다.

| 부품 | 수량 | 추천 판매처 | 가격 메모 |
|---|---|---|---|
| **Sharp LS027B7DH01A** 디스플레이 패널 | 10~12 | **DigiKey Korea** (정품 기준 샘플은 정식 유통에서. [A안 구매 조건](cost.md#a안-구매-조건) 1번) | DigiKey KR 1개 ₩42,180, 재고 7,589개(검색 시점, 공장 리드타임 28주). LCSC C17247735 1개 약 $19.98(10개 이상 $19.08) — 정식 유통 여부 확인 필요 |
| ESP32-S3-MINI-1-N8 | 10~12 | LCSC(JLCPCB 조립), DigiKey | 소량 약 $4.5 |
| SKRPABE010 택트 스위치 | 420 (39 × 10 + 여유) | LCSC C115360(JLCPCB 조립), TME | JLCPCB 조립 시 확장 부품 수수료가 붙는다 |
| 측면 누름 택트 스위치 | 25 | LCSC | |
| 1N4148WS | 450 | LCSC | 기본 부품이면 수수료 없음 |
| BQ24074 (C54313), TPS62840 (C2071139), MAX17048 (C2682616) | 각 12 | LCSC | 전원 IC 4종 소량 합계 약 $7.6/대 |
| 디스플레이 5 V 승압 IC (필요 시) | 12 | LCSC | 데이터시트로 VDD 확인 뒤 결정 |
| USB-C 리셉터클, 디스플레이 FPC 커넥터, 32.768 kHz 크리스털, LED, ESD 다이오드, 수동소자 | 대당 1벌 + 여유 | LCSC | FPC 커넥터 핀 수·피치는 LS027B7DH01A 데이터시트로 확인 |
| PCB 138 × 66 × 1.0 mm + 양면 조립 | 10 | JLCPCB | 10대 기준 대당 약 $20(셋업·스텐실·확장 부품 수수료가 대부분) |
| 503450 배터리 | 12 | 국내 쇼핑몰 | |

## 주문 묶음 제안

면세 한도와 무료배송 기준을 같이 맞추는 묶음이다.

1. **DigiKey Korea 한 번** (₩60,000 넘겨 무료배송): 개발보드 2 + 대체 스위치 100 + Adafruit 브레이크아웃류. $150를 넘기 쉬우니 넘으면 관부가세(대략 부가세 10% + 품목별 관세)를 예산에 넣는다. 2단계의 디스플레이 10개는 금액이 커서 어차피 과세 대상이다.
2. **TME 한 번**: SKRPABE010 100개(+ 하중 비교용 다른 SKRP 품번). $150 안쪽.
3. **영국(The Pi Hut / Pimoroni)**: DigiKey에 Adafruit 4694 재고가 없을 때만.
4. **JLCPCB + LCSC 같이**: 키 PCB(1단계)와 코어 PCB(2단계). LCSC 부품을 JLCPCB 주문에 합쳐 배송비를 한 번만 낸다.
5. **국내**: 배터리, 필라멘트, 나사, 만능기판, 공구.
6. **AliExpress**: 인서트·나사 같은 소모품만, 물품가를 작게 유지.

## 출처

- 배송 조건 — [DigiKey Korea 배송 안내](https://www.digikey.kr/en/help-support/delivery-information/delivery-time-and-cost), [Mouser Korea](https://www.mouser.kr/), [LCSC 관세 FAQ](https://www.lcsc.com/faqs/shipping-delivering/customs-duties-taxes), [JLCPCB 배송비](https://jlcpcb.com/help/article/how-much-does-shipping-cost), [JLCPCB 관세](https://jlcpcb.com/help/article/customs,-duties-and-taxes), [DHL 수요 할증](https://mydhl.express.dhl/kr/en/ship/surcharges/demand-surcharge.html)
- 통관 — [토스뱅크 해외직구 관세](https://www.tossbank.com/articles/customs), [대한민국 정책브리핑](https://m.korea.kr/news/policyNewsView.do?newsId=148957712), [2026 면세 한도 정리](https://glasswallet.com/calculate/customs-duty/duty-free-guide)
- LS027B7DH01A — [DigiKey Korea](https://www.digikey.kr/en/products/detail/sharp-microelectronics/LS027B7DH01A/5054067), [LCSC C17247735](https://www.lcsc.com/product-detail/C17247735.html), [JLCPCB](https://jlcpcb.com/partdetail/18376852-LS027B7DH01A/C17247735), [Findchips](https://www.findchips.com/search/LS027)
- Adafruit 4694 — [The Pi Hut](https://thepihut.com/products/adafruit-sharp-memory-display-breakout-2-7-400x240-monochrome), [Pimoroni](https://shop.pimoroni.com/products/adafruit-sharp-memory-display-breakout-2-7-400x240-monochrome), [Cool Components](https://coolcomponents.co.uk/products/sharp-memory-display-breakout-2-7-400x240-monochrome), [DigiKey](https://www.digikey.de/en/products/detail/adafruit-industries-llc/4694/13157994), [Botland(단종 표시)](https://botland.store/withdrawn-products/17701-monochrome-sharp-memory-display-breakout-design-27-400x240-adafruit-4694-5904422354527.html)
- 스위치 — [DigiKey SKRPABE010](https://azcus.digikey.com/en/products/detail/alps-alpine/SKRPABE010/18768948), [TME SKRPABE010](https://www.tme.com/ca/en/details/skrpabe010/microswitches-tact/alps/)
- ESP32-S3 — [DigiKey Korea ESP32-S3-MINI-1-N8](https://www.digikey.kr/en/products/detail/espressif-systems/ESP32-S3-MINI-1-N8/15295890), [Adafruit DevKitM-1-N8](https://www.adafruit.com/products/5311), [Future Electronics DevKitM-1-N8](https://futureelectronics.com/p/semiconductors--wireless-rf--rf-wireless/esp32-s3-devkitm-1-n8-espressif-systems-9165274)
- 전원 — [Adafruit bq24074 가이드](https://learn.adafruit.com/adafruit-bq24074-universal-usb-dc-solar-charger-breakout?view=all), [DigiKey TPS62840-1YBGEVM56](https://www.digikey.ch/en/products/detail/texas-instruments/TPS62840-1YBGEVM56/10434610), [DigiKey TPS62840-1DLCEVM55](https://www.digikey.jp/en/products/detail/texas-instruments/TPS62840-1DLCEVM55/10434525)
- 인서트 — [West3D CNC Kitchen](https://west3d.com/products/cnc-kitchen-heat-set-inserts-various-sizes), [Prusa M2 short](https://www.prusa3d.com/product/heat-set-inserts-m2-short-100-pcs/), [McMaster M2](https://www.mcmaster.com/inserts/thread-size~m2/)
