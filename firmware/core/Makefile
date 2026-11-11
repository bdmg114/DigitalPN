CFLAGS ?= -std=c99 -Wall -Wextra -Werror -O2

test: test_hangul
	./test_hangul

test_hangul: test_hangul.c hangul.c hangul.h
	$(CC) $(CFLAGS) -o $@ test_hangul.c hangul.c

clean:
	rm -f test_hangul

.PHONY: test clean
