/* Run on Linux: cc -O2 -ffunction-sections -fdata-sections tests/menusize_specialties.c -Wl,--gc-sections -o /tmp/menusize-specialties && /tmp/menusize-specialties */
#include <assert.h>
#include "../runtime/menusize.c"
uint8_t *g_mem;
uint8_t g_cbits[1u<<15];
static int world_map;
static void check(uint32_t hash, uint32_t tex, int preserve){
    uint32_t o=0x1000,d=0x2000;
    memset(g_mem,0,0x4000);
    MR32(o+O_TYPE)=T_IMAGE; MR32(o+O_HASH)=hash; MR32(o+0x24)=tex; MR32(o+O_DATA)=d;
    MR32(d)=0; MR32(d+4)=255; MR32(d+8)=255; MR32(d+12)=137;
    blue_accent(o,0,world_map);
    assert(MR32(d+12)==137);
    assert(MR32(d)==(preserve?0:202));
    assert(MR32(d+4)==(preserve?255:148));
    assert(MR32(d+8)==(preserve?255:24));
}
int main(void){
    g_mem=calloc(1,0x4000);g_cbits[0]=1;
    for(uint32_t h=0xa71e35f6;h<=0xa71e35fd;h++)check(h,0,1);
    check(0,0x3f40e75f,1);check(0xb46342ba,0,1);
    check(0xa71e35f5,0,0);check(0xa71e35fe,0,0);check(0x12345678,0,0);
    check(0xa148528a,0,0); /* Same row name in a normal menu still themed. */
    world_map=1;
    for(uint32_t h=0xa148528a;h<=0xa1485292;h++)check(h,0,1);
    for(uint32_t h=0xca52a3fa;h<=0xca52a3fe;h++)check(h,0,1);
    for(uint32_t h=0xa1485b0c;h<=0xa1485b14;h++)check(h,0,1);
    for(uint32_t h=0xca53bcbc;h<=0xca53bcc0;h++)check(h,0,1);
    check(0x12345678,0,0); /* Map frame/menu accents still themed. */
    free(g_mem);puts("PASS: specialty minimap markers and all world-map legend icons retain yellow/alpha; normal menu accents stay blue.");
}
