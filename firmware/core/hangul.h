/* DigitalPN — 두벌식 한글 오토마타 (하드웨어 독립, 동적 할당 없음)
 *
 * 키 입력(호환 자모 U+3131..U+3163)을 받아 완성된 글자(commit)와
 * 조합 중인 글자(preedit)를 돌려준다. 호출자는 commit을 문서에 넣고
 * preedit을 커서 위치에 덮어 그리면 된다.
 */
#ifndef DPN_HANGUL_H
#define DPN_HANGUL_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint8_t cho;   /* 초성: 호환 자음 인덱스+1 (0 = 없음) */
    uint8_t v1;    /* 첫 모음: 호환 모음 인덱스+1 */
    uint8_t v2;    /* 겹모음의 둘째 모음 */
    uint8_t j1;    /* 받침 첫 자음 */
    uint8_t j2;    /* 겹받침 둘째 자음 */
} hg_state;

typedef struct {
    uint32_t commit[2]; /* 이번 입력으로 확정된 글자 (0~2개) */
    uint8_t  ncommit;
    uint32_t preedit;   /* 조합 중인 글자, 없으면 0 */
} hg_out;

void hg_reset(hg_state *s);

/* 자모 하나를 입력한다. jamo가 호환 자모 범위가 아니면 false (상태 변화 없음). */
bool hg_feed(hg_state *s, uint32_t jamo, hg_out *out);

/* 조합 중인 글자에서 자모 하나를 지운다. 조합 중이 아니면 false
 * (호출자가 문서의 앞 글자를 지워야 함). */
bool hg_backspace(hg_state *s, hg_out *out);

/* 조합을 끝내고 남은 글자를 확정한다 (스페이스, 엔터, 커서 이동 전에 호출). */
void hg_flush(hg_state *s, hg_out *out);

/* 두벌식 자판: QWERTY 문자 → 호환 자모. 대문자는 쌍자음/ㅒㅖ. 해당 없으면 0. */
uint32_t hg_from_qwerty(char c);

#endif
