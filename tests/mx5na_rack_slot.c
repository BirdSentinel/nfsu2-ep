/* NA-only EDOLIX metadata, old-save migration and category filtering. */
#include "../runtime/regional.c"
#include <assert.h>
#include <stdlib.h>
uint8_t *g_mem;
static unsigned categories, updates;
void sub_00545700_orig(CPU *c) { categories++; POP32(c->eip); c->esp += 16; }
void sub_0061bcd0_orig(CPU *c) { updates++; }
void sub_0061b980_orig(CPU *c) {
    uint32_t prev = MR32(c->esp+16);
    c->eax = prev == 0x3000 ? g_na_rack : 0x3000;
    POP32(c->eip); c->esp += 20;
}
int main(void) {
    g_mem=calloc(1,0x1000000); assert(g_mem); addon_car_count=47;
    uint32_t chunk=0x1000,rack=chunk+16,shared=rack+14,tail=shared+14;
    MR32(chunk)=0x80034602;MR32(chunk+4)=50;MR32(chunk+8)=0x34604;MR32(chunk+12)=42;
    MR32(rack)=0xa2bddcb5;MR16(rack+4)=0x210f;MR16(rack+6)=0x4b01;MR16(rack+12)=174;
    MR32(shared)=0x45f085d5;MR16(shared+4)=0x800c;MR16(shared+6)=0x4001;MR32(shared+8)=0xffff1ee9;
    MR32(tail)=0x572b056b;
    unsigned char original[14];memcpy(original,g_mem+shared,14);
    addon_rack_parts(chunk);
    assert(g_na_rack==rack && g_na_tail==tail);
    assert(MR32(rack)==0xa2bddcb5 && MR16(rack+6)==0x4b01 && MR16(rack+12)==174);
    assert(MR16(rack+4)==0x800c && MR32(rack+8)==MR32(shared+8));
    assert(!memcmp(original,g_mem+shared,14));
    CPU c={0};c.ecx=0x4000;MR32(c.ecx)=46;MR32(c.ecx+0x590+15*4)=rack;
    sub_0061bcd0(&c);assert(MR32(c.ecx+0x590+15*4)==tail && MR32(c.ecx+0x590+12*4)==rack);
    MR32(c.ecx+0x590+12*4)=shared;sub_0061bcd0(&c);
    assert(MR32(c.ecx+0x590+12*4)==rack);
    MR32(c.ecx+0x590+15*4)=shared;sub_0061bcd0(&c);
    assert(MR32(c.ecx+0x590+15*4)==shared); /* legitimate selections are retained */
    MR32(c.ecx)=4;MR32(c.ecx+0x590+15*4)=shared;sub_0061bcd0(&c);assert(MR32(c.ecx+0x590+15*4)==shared);
    c.esp=0x5000;MR32(c.esp)=0x123;MR32(c.esp+4)=15;MR32(0x8392c0)=46;
    sub_00545700(&c);assert(categories==1 && c.esp==0x5014);
    c.esp=0x5000;MR32(0x8392c0)=4;sub_00545700(&c);assert(categories==2);
    c.esp=0x5000;MR32(c.esp+4)=46;MR32(c.esp+8)=12;MR32(c.esp+16)=0;MR32(0x3000)=0x45f085d5;
    assert(addon_rack_query(&c));assert(c.eax==rack && c.esp==0x5018);
    puts("PASS NA rack metadata, unchanged shared part, old-save migration, NB preservation and category/query filtering");
    free(g_mem);
}
