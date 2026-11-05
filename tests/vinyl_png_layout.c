/* gcc -Iruntime tests/vinyl_png_layout.c runtime/web/vinyl_png.c -o /tmp/vinyl-test */
#include "cpu.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
uint8_t *g_mem;
void vinyl_png_decoded(uint32_t, uint32_t);
static char fixture[1024];
int fileio_resolve_game(const char *win, char *out, size_t n) {
    assert(strstr(win, "CARS\\MX5NA\\VINYLS\\") == win);
    snprintf(out, n, "%s", fixture);
    return 1;
}
int main(int argc, char **argv) {
    assert(argc == 2);
    snprintf(fixture, sizeof fixture, "%s", argv[1]);
    FILE *fp = fopen(fixture, "rb"); assert(fp);
    unsigned char *vpx = malloc(350544); assert(vpx);
    assert(fread(vpx, 1, 350544, fp) == 350544); fclose(fp);
    g_mem = malloc(400000); assert(g_mem);
    for (unsigned padding = 0; padding <= 64; padding += 64) {
        unsigned palette = 349504 + padding, size = palette + 1024 + 156;
        memset(g_mem, 0xcc, 400000);
        unsigned char *ti = g_mem + 100 + size - 156;
        memset(ti, 0, 156);
        memcpy(ti + 12, "MX5NA_CONTEST_01", 16);
        unsigned values[] = {0, palette, 349504, 1024};
        memcpy(ti + 48, values, sizeof values);
        ti[69] = ti[71] = 2; ti[78] = 7;
        unsigned char trailer[156]; memcpy(trailer, ti, 156);
        vinyl_png_decoded(100, size);
        assert(!memcmp(g_mem + 100, vpx + 16, 349504));
        assert(!memcmp(g_mem + 100 + palette, vpx + 16 + 349504, 1024));
        assert(!memcmp(ti, trailer, 156));
        assert(g_mem[99] == 0xcc && g_mem[100 + size] == 0xcc);
        for (unsigned i = 349504; i < palette; i++) assert(g_mem[100 + i] == 0xcc);
    }
    free(vpx); free(g_mem);
    puts("PASS retail and addon vinyl layouts, metadata and boundaries");
}
