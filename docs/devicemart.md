# 디바이스마트 구성안

[hardware.md](hardware.md)의 기준 설계를 **디바이스마트(devicemart.co.kr)에서 살 수 있는 부품만으로** 다시 구성한 안이다. 케이스 변경은 최소로 했다.

디바이스마트는 자체 재고 외에 DigiKey·Mouser·LCSC·Arrow 품목을 대신 들여와 판다(상품 페이지에 "해외구매", 다른 유통사 부품 번호가 표시된다). 그래서 대부분의 IC를 원화로 국내에서 살 수 있다. 다만 해외구매 품목은 준비기간이 4일~2주이고 **주문 후 취소·반품이 안 된다.**

가격·재고는 2026년 11월 검색에 나온 상품 페이지 값이다. 같은 품번도 경로(DigiKey·Mouser·LCSC)에 따라 페이지가 여러 개이고 재고·가격이 서로 달랐다. 주문 전에 상품 페이지에서 다시 확인한다.

## 요약

| | 기준안 | 디바이스마트안 |
|---|---|---|
| 바뀐 부품 | — | 충전 IC, 3.3 V 전원(벅 → LDO), 배터리, 어깨 스위치 |
| 케이스 | 142 × 70 × 12.3 mm | 142 × 70 × **12.8 mm**. **앞판 하나만** 0.5 mm 두꺼워짐. 뒷판·키매트·어깨 캡 그대로 |
| 배터리 | 503450 1000 mAh | 523450 950 mAh (KC 인증) |
| 배터리 수명 (계산) | 약 한 달 | 약 4주 |
| 대당 부품비 (10대, VAT 포함) | 약 7.5만 원 + 해외 배송·관세 | **약 8.6만 원**, 국내 배송 |

## 부품표

| 기능 | 기준안 | 디바이스마트안 | 디바이스마트 가격 (VAT 별도) | 바뀌는 것 |
|---|---|---|---|---|
| 디스플레이 | Sharp LS027B7DH01A | **같음** ([상품](https://www.devicemart.co.kr/goods/view?no=6962946)) | 42,110원 | 없음. A 없는 LS027B7DH01 페이지는 단종 표시가 있으니 A를 산다 |
| MCU·무선 | ESP32-S3-MINI-1-N8 | **같음** ([Mouser 경로](https://www.devicemart.co.kr/goods/view?no=15464675)) | 10개 이상 7,030원, 준비 약 1주 | 없음 |
| 키 스위치 39개 | Alps SKRPABE010 | **같음** ([상품](https://www.devicemart.co.kr/goods/view?no=14615376)) | 50~99개 개당 260원, 재고 3만 개 이상 | **높이 2.5 mm** → 앞판 +0.5 mm (아래 케이스 변경 참조) |
| 어깨 스위치 2개 | 측면 누름 택트 스위치 | NW3 측면형 마이크로 택트 [NW3-A03-04] ([상품](https://www.devicemart.co.kr/goods/view?no=1322065)), 4.6 × 3.6 mm | 100원 안팎 | 버튼 높이를 데이터시트로 확인. 맞지 않으면 어깨 캡만 고친다 |
| 충전 | BQ24074 | **BQ24072RGTR** ([상품](https://www.devicemart.co.kr/goods/view?no=11992349)) | 1,980원, 준비 약 1주 | 같은 계열·같은 16핀 VQFN이라 풋프린트를 그대로 쓴다. 입력 과전압 보호가 10.5 V → 6.6 V로 낮지만 USB 5 V 전용이라 문제없다. 일부 핀 기능이 달라(BQ24072는 TD 등) 회로도에서 그 핀 처리만 데이터시트대로 바꾼다 |
| 3.3 V 전원 | TPS62840 벅 | **TLV75733PDBVR** LDO, 1 A, SOT-23-5 ([LCSC 경로](https://www.devicemart.co.kr/goods/view?no=15425020)) | 390원, 재고 9만 개 이상 | TPS62840은 검색되지 않았다. 아래 전력 영향 참조 |
| 디스플레이 5 V | (필요 시) 승압 | **TPS61202DSCR** 승압, WSON-10 ([상품](https://www.devicemart.co.kr/goods/view?no=15029347)) | 확인 필요 | LS027B7DH01A의 VDD는 5 V라 승압이 필요하다. 대기 전류가 수십 µA로 커서 아래 전력 계산에 넣었다 |
| 잔량 측정 | MAX17048 | **MAX17048X+T10** ([상품](https://www.devicemart.co.kr/goods/view?no=15089729)) | 4,800원 (10개 이상 4,310원) | 같은 칩이지만 **WLP 패키지**(TDFN인 G+는 검색되지 않음). 손납땜은 어렵다. 아래 조립 참조 |
| 배터리 | 503450 1000 mAh | **더한 TW523450 950 mAh, KC 인증** ([판매사 페이지](https://www.devicemart.co.kr/goods/brand?code=1889)) | 5,500원 | 34 × 50 mm로 같고 두께가 5.0 → 약 5.2 mm. 뒷면 공간(5.6 mm)에 들어간다. 커넥터는 1.25 mm 2핀(A1251-02) |
| (대안) 배터리 | | Jauch LP523450JU + PCM + JST PHR-3 1000 mAh ([DigiKey 경로](https://www.devicemart.co.kr/goods/view?no=15435201)) | 확인 필요 | 3선(NTC 포함)이라 충전 IC의 TS 핀에 온도 감지를 연결할 수 있다 |
| USB-C | USB-C 리셉터클 | **TYPE-C-31-M-12** 16핀 SMD ([상품](https://www.devicemart.co.kr/goods/view?no=15027351)) | 50개 이상 320원 | 케이스 USB 구멍(9.4 × 3.6 mm) 안에 들어가는지 데이터시트로 확인 |
| 디스플레이 FPC | FPC 커넥터 | 0.5 mm 10핀 SMD (Molex 5051101092 또는 [FFC-10P LOCK 0.5mm](https://www.devicemart.co.kr/goods/view?no=20934)) | 수백 원 | 접점 방향(상·하)을 LS027B7DH01A의 FPC 데이터시트와 맞춘다 |
| 다이오드 41개, 32.768 kHz 크리스털, LED, ESD, 수동소자 | | 1N4148WS 등 범용품 | 대당 약 5천 원 | 없음 |

## 케이스 변경

**바뀌는 부품은 앞판 하나다.** 바깥 윤곽(142 × 70 mm), 나사 위치, 화면 창, 키 구멍은 그대로이고, 앞판이 0.5 mm 높아져 전체 두께가 12.3 → 12.8 mm가 된다.

| 부품 | 변경 | 확인 |
|---|---|---|
| 앞판 (`top`) | 4.1 → 4.6 mm | OpenSCAD로 렌더링해 확인 |
| 손잡이형 앞판 | 5.5 → 6.0 mm | 렌더링 확인 |
| 뒷판, 키매트, 어깨 캡 | 없음 | 렌더링 결과 치수가 같다 |

이유는 **스위치 높이**다. 코어 치수 계약(`dpn_core.scad`의 `sw_h = 2.0`)은 2.0 mm를 가정했지만, 기준안에서도 쓰는 SKRPABE010의 실제 높이는 2.5 mm다(Alps SKRP 시리즈 자료, RS 상품 정보). 그래서 **이 0.5 mm는 디바이스마트안이 아니라 기준안에도 필요한 수정**이다. 지금 STL대로 출력하면 키매트가 스위치에 0.5 mm 눌린 상태로 조립된다.

뽑아 둔 파일 (`hardware/case/stl/devicemart/`):

```sh
openscad -D 'part="top"' -D sw_h=2.5 -o dpn-top-sw25.stl hardware/case/case.scad
openscad -D 'part="top"' -D 'style="grip"' -D sw_h=2.5 -o dpn-grip-top-sw25.stl hardware/case/case.scad
```

뒷판·키매트·어깨 캡은 기존 `stl/`의 파일을 그대로 쓴다.

두께를 12.3 mm로 지키려면 뒷면 공간을 5.6 → 5.1 mm로 줄이고 뒷판 바닥에 배터리 자리만 0.5 mm 파 넣는 방법이 있다(배터리 자리는 손가락 홈과 겹치지 않는다). 하지만 그러면 뒷판도 바뀌고 배터리 아래 바닥이 1.1 mm로 얇아져, 시제품에서는 0.5 mm를 받아들이는 쪽을 권한다.

### 배터리 두께 여유

523450은 두께가 약 5.2 mm라 뒷면 공간 5.6 mm 안에서 여유가 0.6 → 0.4 mm로 준다. 시제품에는 충분하지만, 리튬폴리머는 오래 쓰면 부풀 수 있으니 판매처의 최대 두께 값을 받아 두고 0.4 mm 안에 드는지 확인한다.

## 전력 영향 (계산값)

| 변경 | 하루 소모 증가 |
|---|---|
| 벅(TPS62840, 대기 전류 약 60 nA) → LDO(TLV757, 대기 전류 수십 µA) | 약 0.6 mAh. 3.7 V에서 3.3 V로 내리는 손실은 가벼운 부하에서 벅과 큰 차이가 없다 |
| 5 V 승압 상시 동작 (TPS61202, 대기 전류 약 50 µA로 가정) | 약 1.2 mAh |
| 배터리 1000 → 950 mAh | 용량 5% 감소 |

기준안 약 30 mAh/일에서 약 32 mAh/일로 늘고, 950 mAh로 **약 4주**다. 정확한 대기 전류는 각 데이터시트로 다시 계산한다.

LDO는 배터리가 약 3.45 V 밑으로 떨어지면 Wi-Fi 송신 피크에서 3.3 V를 유지하지 못한다. 그 아래 남은 용량은 몇 % 수준이라, 펌웨어에서 저전압 종료 기준을 3.5 V 근처로 잡는다.

## 조립

디바이스마트에서 산 부품은 JLCPCB 조립 서비스의 부품 재고와 무관하므로, **PCB만 제작하고 조립은 직접 하는** 것을 전제로 했다(PCB 제작은 디바이스마트 범위 밖이다: JLCPCB 또는 국내 PCB 업체).

- 스위치·다이오드·USB-C·LDO는 손납땜이 된다.
- BQ24072(VQFN-16)와 TPS61202(WSON-10)는 스텐실 + 핫플레이트나 열풍기로 붙인다.
- **MAX17048X+T10은 WLP라 손으로 붙이기 어렵다.** 방법은 둘이다. ① 스텐실 + 리플로로 붙인다. ② 첫 시제품에서는 빼고, 배터리 전압을 ESP32 ADC로 읽는다(분압 저항 2개, 정확도는 떨어진다). PCB에는 두 방식 자리를 모두 둔다.
- 스텐실은 JLCPCB에 PCB와 같이 주문한다.

## 비용 (10대, 부품은 VAT 포함 원화)

| 항목 | 대당 (원) |
|---|---|
| LS027B7DH01A | 46,321 |
| ESP32-S3-MINI-1-N8 | 7,733 |
| SKRPABE010 39개 | 11,154 |
| 어깨 스위치 2개 | 200 |
| BQ24072 + TLV75733 + TPS61202 (추정) + MAX17048X | 약 9,000 |
| USB-C, FPC 커넥터 | 1,350 |
| 다이오드·크리스털·수동소자·LED·ESD | 약 5,000 |
| TW523450 배터리 | 5,500 |
| **부품 소계** | **약 86,000** |

10대 부품 약 86만 원 + 여유 10% + PCB·스텐실 약 5~10만 원(JLCPCB, 배송 포함) = **약 100만 원**. [parts-order.md](parts-order.md#2단계-내역-10대-부품은-12대분)의 해외 구매안(JLCPCB 조립 포함 약 140만 원)보다 싸지만, 조립을 직접 하는 시간이 들어간다. 디바이스마트는 66,000원 이상이면 무료배송이다.

## 확인할 것

1. **SKRPABE010의 누름 압력은 1.57 N이다.** [hardware.md](hardware.md)의 목표(약 1.0 N, 1.6 N 이상은 무겁다)보다 무겁다. 이 문제는 기준안도 같다. 디바이스마트에서 더 가벼운 SKRP 품번은 찾지 못했다(SKRPACE010은 더 무겁고, SKRPAME010은 압력을 확인하지 못했다). 0단계 목업에서 1.57 N으로 쳐 보고 무거우면 다른 스위치를 다시 고른다.
2. 어깨 스위치 NW3-A03-04의 버튼 높이와 누름 방향이 어깨 캡(`shoulder_zc`, 3.4 mm 구멍)과 맞는지.
3. TW523450의 최대 두께와 커넥터 리드 위치.
4. BQ24072와 BQ24074의 핀 기능 차이.
5. TPS61202의 대기 전류. 크면 대기 전류가 작은 다른 5 V 승압 IC를 디바이스마트에서 다시 찾는다.
6. USB-C와 FPC 커넥터의 높이·위치가 케이스 구멍과 디스플레이 자리에 맞는지.

## 출처

- 디바이스마트 상품 — [LS027B7DH01A](https://www.devicemart.co.kr/goods/view?no=6962946), [LS027B7DH01](https://www.devicemart.co.kr/goods/view?no=6962947), [ESP32-S3-MINI-1-N8](https://www.devicemart.co.kr/goods/view?no=15464675), [SKRPABE010](https://www.devicemart.co.kr/goods/view?no=14615376), [SKRPACE010](https://www.devicemart.co.kr/goods/view?no=15190495), [NW3-A03-04](https://www.devicemart.co.kr/goods/view?no=1322065), [BQ24072RGTR](https://www.devicemart.co.kr/goods/view?no=11992349), [TLV75733PDBVR](https://www.devicemart.co.kr/goods/view?no=15425020), [TPS61202DSCR](https://www.devicemart.co.kr/goods/view?no=15029347), [MAX17048X+T10](https://www.devicemart.co.kr/goods/view?no=15089729), [더한 배터리](https://www.devicemart.co.kr/goods/brand?code=1889), [Jauch LP523450](https://www.devicemart.co.kr/goods/view?no=15435201), [TYPE-C-31-M-12](https://www.devicemart.co.kr/goods/view?no=15027351), [FFC-10P 0.5mm](https://www.devicemart.co.kr/goods/view?no=20934)
- SKRP 높이·압력 — [Alps SKRP 데이터시트(Mouser)](https://www.mouser.com/datasheet/2/15/SKRP-1370722.pdf), [RS Online](https://uk.rs-online.com/web/p/tactile-switches/9174087), [JLCPCB C115360](https://jlcpcb.com/partdetail/Alpsalpine-SKRPABE010/C115360)
