/* cc -O2 -ffunction-sections -fdata-sections tests/addon_rack_unit.c
 *    -Wl,--gc-sections -lm -o /tmp/addon_rack_unit && /tmp/addon_rack_unit */
#include <assert.h>
#include <stdlib.h>
#include "../runtime/regional.c"

uint8_t *g_mem;
static unsigned calls, skipped;
static const uint32_t sp = 0x1000, ret = 0x5449c0, db = 0x8a2b68;

/* Match the retail function's destructive use of its incoming arguments,
 * including its ret 20. Every retry must start with the original query. */
void sub_0061b980_orig(CPU *c) {
    assert(c->esp == sp && c->ecx == db);
    assert(MR32(sp) == ret && MR32(sp + 4) == 46 && MR32(sp + 8) == 12);
    assert(MR32(sp + 12) == 0x1234 && MR32(sp + 20) == 3);
    assert(MR32(sp + 16) == (calls ? 0x2000 + calls * 16 : 0));
    ++calls;
    c->eax = 0x2000 + calls * 16;
    MR32(c->eax) = calls <= skipped ? (calls & 1 ? 0x45f085d5 : 0x0954cebd) : 0xa2bddcb5;
    MR32(sp + 4) = 0xabcdef01; /* slot mask */
    MR32(sp + 8) = 0x8a0380;   /* owner-list pointer, NOT slot 12 */
    c->ecx = 0xdeadbeef;
    POP32(c->eip); c->esp += 20;
}

static void run(unsigned skip) {
    CPU c = {0}; c.esp = sp; c.ecx = db;
    uint32_t args[] = {ret, 46, 12, 0x1234, 0, 3};
    memcpy(g_mem + sp, args, sizeof args);
    calls = 0; skipped = skip;
    assert(addon_rack_query(&c) == 1);
    assert(c.esp == sp + 24 && c.eip == ret);
    assert(calls == (skip < 4 ? skip + 1 : 4));
    assert(c.eax == (skip < 4 ? 0x2000 + calls * 16 : 0));
}

int main(void) {
    g_mem = calloc(1, 0x10000); assert(g_mem);
    addon_car_count = 47; g_na_rack = 0x2100;
    run(0); run(1); run(2); run(4);
    CPU c = {0}; c.esp = sp;
    MR32(sp + 4) = 4; MR32(sp + 8) = 12;
    assert(addon_rack_query(&c) == 0 && c.esp == sp);
    free(g_mem);
    puts("PASS addon rack: destructive arguments, both excluded variants, bounded retries, other cars");
}
