/* Loaded retail profiles gain one unlocked car after the unchanged Miata NB. */
#include "../runtime/regional.c"
#include <assert.h>
#include <stdlib.h>

uint8_t *g_mem;
int main(void) {
    g_mem = calloc(1, 0x1000000);
    assert(g_mem);
    uint32_t db = 0x83ad90u;
    addon_car_count = 47;
    for (uint32_t i = 0; i < 31; i++) {
        uint32_t r = db + i * 28;
        MR32(r) = 0x79aadc;
        MR32(r + 8) = 1000 + i;
        MR32(r + 16) = MR32(r + 20) = 1;
        MR32(r + 24) = i;
    }
    MR32(db + 0x540) = 31;
    addon_stock_append(db);
    assert(MR32(db + 0x540) == 32);
    for (uint32_t i = 0; i < 32; i++) {
        uint32_t r = db + i * 28;
        assert(MR32(r + 24) == (i == 5 ? 46 : i > 5 ? i - 1 : i));
        if (i != 5) assert(MR32(r + 8) == 1000 + (i > 5 ? i - 1 : i));
        assert(MR32(r + 16) == 1);
    }
    unsigned char before[0x544];
    memcpy(before, g_mem + db, sizeof before);
    addon_stock_append(db);
    assert(!memcmp(before, g_mem + db, sizeof before));
    assert(addon_donor_type(46) == 4 && addon_donor_type(4) == 4);
    assert(addon_part_count() == 16000);
    puts("PASS existing profile keeps all 31 cars; unlocked MX5NA follows Miata, idempotently");
    free(g_mem);
}
