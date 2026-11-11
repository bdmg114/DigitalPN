/* 호스트 테스트: make -C firmware/core test */
#include "hangul.h"
#include <stdio.h>
#include <string.h>

static char buf[256];
static size_t len;

static void put(uint32_t cp) {
    if (!cp) return;
    if (cp < 0x80) buf[len++] = (char)cp;
    else if (cp < 0x800) { buf[len++] = (char)(0xC0 | cp >> 6); buf[len++] = (char)(0x80 | (cp & 63)); }
    else { buf[len++] = (char)(0xE0 | cp >> 12); buf[len++] = (char)(0x80 | ((cp >> 6) & 63)); buf[len++] = (char)(0x80 | (cp & 63)); }
}

/* keys: 두벌식 QWERTY 표기. ' ' = 스페이스(조합 종료), '<' = 백스페이스 */
static const char *type(const char *keys) {
    hg_state s; hg_out o;
    hg_reset(&s); len = 0;
    for (; *keys; keys++) {
        if (*keys == '<') {
            if (!hg_backspace(&s, &o) && len) { /* 문서의 마지막 글자를 지움 */
                do len--; while (len && ((unsigned char)buf[len] & 0xC0) == 0x80);
            }
        } else if (hg_feed(&s, hg_from_qwerty(*keys), &o)) {
            for (int i = 0; i < o.ncommit; i++) put(o.commit[i]);
        } else {
            hg_flush(&s, &o);
            for (int i = 0; i < o.ncommit; i++) put(o.commit[i]);
            put((uint32_t)*keys);
        }
    }
    hg_flush(&s, &o);
    for (int i = 0; i < o.ncommit; i++) put(o.commit[i]);
    buf[len] = 0;
    return buf;
}

static int fails;
static void expect(const char *keys, const char *want) {
    const char *got = type(keys);
    if (strcmp(got, want)) { printf("FAIL %-22s want %s got %s\n", keys, want, got); fails++; }
}

int main(void) {
    expect("gksrmf", "한글");
    expect("dkssudgktpdy", "안녕하세요");
    expect("ekfrdl", "닭이");          /* 겹받침 분리: ㄺ → ㄹ + 기 */
    expect("ekfrk", "달가");
    expect("djqtdj", "없어");
    expect("rkqt", "값");
    expect("rkqtdl", "값이");
    expect("rhkdhl", "과외");          /* 겹모음 */
    expect("dmltk", "의사");
    expect("rnrrk", "국가");           /* 같은 자음 연속은 쌍자음이 되지 않음 */
    expect("dlTek", "있다");
    expect("Rhc", "꽃");
    expect("dOrl", "얘기");
    expect("zzz", "ㅋㅋㅋ");
    expect("hk", "ㅘ");
    expect("kr", "ㅏㄱ");
    expect("gks rmf", "한 글");
    expect("gks<", "하");              /* 자모 단위 백스페이스 */
    expect("gks<<<", "");
    expect("gks<<<<", "");
    expect("rkqt<", "갑");
    expect("rhk<", "고");
    expect("gksr<<", "");              /* ㄱ 삭제 후에는 확정된 '한'을 글자 단위로 삭제 */
    expect("dkEk", "아따");            /* ㄸ은 받침이 될 수 없음 */
    expect("aksgdl", "많이");
    expect("dlfrek", "읽다");
    printf(fails ? "%d failed\n" : "all hangul tests passed\n", fails);
    return fails != 0;
}
