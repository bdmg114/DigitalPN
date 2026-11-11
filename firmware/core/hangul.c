#include "hangul.h"

/* 호환 자음 U+3131.. 30자 → 초성 번호(0..18), 종성 번호(1..27). -1 = 해당 위치에 못 옴 */
static const int8_t CHO[30] = {
    0, 1, -1, 2, -1, -1, 3, 4, 5, -1, -1, -1, -1, -1, -1,
    -1, 6, 7, 8, -1, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18};
static const int8_t JONG[30] = {
    1, 2, 3, 4, 5, 6, 7, -1, 8, 9, 10, 11, 12, 13, 14,
    15, 16, 17, -1, 18, 19, 20, 21, 22, -1, 23, 24, 25, 26, 27};

#define C(cp) ((uint8_t)((cp) - 0x3131 + 1)) /* 호환 자음 → 상태 값 */
#define V(cp) ((uint8_t)((cp) - 0x314F + 1)) /* 호환 모음 → 상태 값 */

/* 겹모음: {첫 모음, 둘째 모음, 결과} */
static const uint8_t VV[][3] = {
    {V(0x3157), V(0x314F), V(0x3158)}, /* ㅗㅏ ㅘ */
    {V(0x3157), V(0x3150), V(0x3159)}, /* ㅗㅐ ㅙ */
    {V(0x3157), V(0x3163), V(0x315A)}, /* ㅗㅣ ㅚ */
    {V(0x315C), V(0x3153), V(0x315D)}, /* ㅜㅓ ㅝ */
    {V(0x315C), V(0x3154), V(0x315E)}, /* ㅜㅔ ㅞ */
    {V(0x315C), V(0x3163), V(0x315F)}, /* ㅜㅣ ㅟ */
    {V(0x3161), V(0x3163), V(0x3162)}, /* ㅡㅣ ㅢ */
};
/* 겹받침: {첫 자음, 둘째 자음, 결과} */
static const uint8_t JJ[][3] = {
    {C(0x3131), C(0x3145), C(0x3133)}, /* ㄱㅅ ㄳ */
    {C(0x3134), C(0x3148), C(0x3135)}, /* ㄴㅈ ㄵ */
    {C(0x3134), C(0x314E), C(0x3136)}, /* ㄴㅎ ㄶ */
    {C(0x3139), C(0x3131), C(0x313A)}, /* ㄹㄱ ㄺ */
    {C(0x3139), C(0x3141), C(0x313B)}, /* ㄹㅁ ㄻ */
    {C(0x3139), C(0x3142), C(0x313C)}, /* ㄹㅂ ㄼ */
    {C(0x3139), C(0x3145), C(0x313D)}, /* ㄹㅅ ㄽ */
    {C(0x3139), C(0x314C), C(0x313E)}, /* ㄹㅌ ㄾ */
    {C(0x3139), C(0x314D), C(0x313F)}, /* ㄹㅍ ㄿ */
    {C(0x3139), C(0x314E), C(0x3140)}, /* ㄹㅎ ㅀ */
    {C(0x3142), C(0x3145), C(0x3144)}, /* ㅂㅅ ㅄ */
};

static uint8_t pair(const uint8_t t[][3], int n, uint8_t a, uint8_t b) {
    for (int i = 0; i < n; i++)
        if (t[i][0] == a && t[i][1] == b) return t[i][2];
    return 0;
}
#define VPAIR(a, b) pair(VV, (int)(sizeof VV / sizeof VV[0]), a, b)
#define JPAIR(a, b) pair(JJ, (int)(sizeof JJ / sizeof JJ[0]), a, b)

/* 현재 상태를 글자 하나로 합성 */
static uint32_t compose(const hg_state *s) {
    uint8_t v = s->v2 ? VPAIR(s->v1, s->v2) : s->v1;
    if (s->cho && v) {
        uint8_t j = s->j2 ? JPAIR(s->j1, s->j2) : s->j1;
        int jong = j ? JONG[j - 1] : 0;
        return 0xAC00u + (uint32_t)((CHO[s->cho - 1] * 21 + (v - 1)) * 28 + jong);
    }
    if (s->cho) return 0x3131u + s->cho - 1;
    if (v) return 0x314Fu + v - 1;
    return 0;
}

static void commit(hg_state *s, hg_out *o) {
    uint32_t c = compose(s);
    if (c && o->ncommit < 2) o->commit[o->ncommit++] = c;
    hg_reset(s);
}

void hg_reset(hg_state *s) { s->cho = s->v1 = s->v2 = s->j1 = s->j2 = 0; }

static void feed_consonant(hg_state *s, uint8_t c, hg_out *o) {
    bool can_jong = JONG[c - 1] > 0;
    if (!s->v1) { /* 모음이 아직 없음: 초성 자리 */
        if (s->cho) commit(s, o);
        s->cho = c;
    } else if (!s->cho) { /* 모음만 있음 */
        commit(s, o);
        s->cho = c;
    } else if (!s->j1 && can_jong) {
        s->j1 = c;
    } else if (s->j1 && !s->j2 && JPAIR(s->j1, c)) {
        s->j2 = c;
    } else {
        commit(s, o);
        s->cho = c;
    }
}

static void feed_vowel(hg_state *s, uint8_t v, hg_out *o) {
    if (s->j1) { /* 받침(겹받침이면 둘째 자음)이 다음 글자의 초성으로 넘어감 */
        uint8_t next = s->j2 ? s->j2 : s->j1;
        if (s->j2) s->j2 = 0; else s->j1 = 0;
        commit(s, o);
        s->cho = next;
        s->v1 = v;
    } else if (s->v1 && !s->v2 && VPAIR(s->v1, v)) {
        s->v2 = v;
    } else if (s->v1) {
        commit(s, o);
        s->v1 = v;
    } else {
        s->v1 = v;
    }
}

bool hg_feed(hg_state *s, uint32_t jamo, hg_out *o) {
    o->ncommit = 0;
    if (jamo >= 0x3131 && jamo <= 0x314E) feed_consonant(s, C(jamo), o);
    else if (jamo >= 0x314F && jamo <= 0x3163) feed_vowel(s, V(jamo), o);
    else { o->preedit = compose(s); return false; }
    o->preedit = compose(s);
    return true;
}

bool hg_backspace(hg_state *s, hg_out *o) {
    o->ncommit = 0;
    bool had = true;
    if (s->j2) s->j2 = 0;
    else if (s->j1) s->j1 = 0;
    else if (s->v2) s->v2 = 0;
    else if (s->v1) s->v1 = 0;
    else if (s->cho) s->cho = 0;
    else had = false;
    o->preedit = compose(s);
    return had;
}

void hg_flush(hg_state *s, hg_out *o) {
    o->ncommit = 0;
    commit(s, o);
    o->preedit = 0;
}

uint32_t hg_from_qwerty(char c) {
    static const uint16_t lower[26] = {
        /* a */ 0x3141, 0x3160, 0x314A, 0x3147, 0x3137, 0x3139, 0x314E, 0x3157, 0x3151,
        /* j */ 0x3153, 0x314F, 0x3163, 0x3161, 0x315C, 0x3150, 0x3154, 0x3142, 0x3131,
        /* s */ 0x3134, 0x3145, 0x3155, 0x314D, 0x3148, 0x314C, 0x315B, 0x314B};
    if (c >= 'a' && c <= 'z') return lower[c - 'a'];
    switch (c) {
    case 'Q': return 0x3143; /* ㅃ */
    case 'W': return 0x3149; /* ㅉ */
    case 'E': return 0x3138; /* ㄸ */
    case 'R': return 0x3132; /* ㄲ */
    case 'T': return 0x3146; /* ㅆ */
    case 'O': return 0x3152; /* ㅒ */
    case 'P': return 0x3156; /* ㅖ */
    }
    if (c >= 'A' && c <= 'Z') return lower[c - 'A'];
    return 0;
}
