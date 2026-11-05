/* cc -Iruntime tests/vinyl_hd.c -o out/vinyl-hd-test */
#include "cpu.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
uint8_t *g_mem;
#include "../runtime/web/vinyl_png.c"
static const char *fixture;
static int enabled=1, promoted, calls;
int fileio_resolve_game(const char *win,char *out,size_t n){
    if(!enabled)return 0;
    assert(strstr(win,"CARS\\MX5NA\\VINYLS\\"));
    snprintf(out,n,"%s",fixture); return 1;
}
void metal_replace_texture(unsigned id,unsigned w,unsigned h,unsigned levels,unsigned fmt,const uint8_t *p){
    assert(id==7 && fmt==21);
    if(!p){assert(w==512&&h==512);return;}
    assert(w==1024&&h==1024&&levels>=1); promoted++;
    for(unsigned y=0;y<1024;y++)for(unsigned x=0;x<1024;x++){
        const uint8_t *v=p+(y*1024+x)*4;
        assert(v[0]==0 && v[1]==(y%2?255:0) && v[2]==(x%2?255:0));
    }
}
static void composite(CPU *c){
    calls++;
    memcpy(g_mem+0x200000,g_mem+0x100000,512*512*4);
    MR32(0x104)++; /* Native colour conversion mutates the caller's context. */
    c->eax=42; c->esp+=4;
}
int main(int argc,char **argv){
    assert(argc==2);fixture=argv[1];hd_names[0].hash=0;strcpy(hd_names[0].car,"MX5NA");g_mem=calloc(1,0x400000);assert(g_mem);
    CPU c={0};c.esp=0x80;MR32(0x84)=0x100;MR32(0x100)=0x400;MR32(0x104)=6;MR32(0x2c4)=1;
    MR32(0x124)=1;MR32(0x128)=0x500;MR32(0x130)=0x100000;
    MR32(0x400)=0x600;MR16(0x444)=MR16(0x446)=512;MR8(0x44a)=32;
    memcpy(g_mem+0x508,"MX5NA_CONTEST_01",16);MR16(0x544)=MR16(0x546)=512;MR8(0x54a)=32;
    MR32(0x618)=0x700;MR32(0x714)=21;MR32(0x718)=7;MR32(0x71c)=7;MR32(0x720)=0x200000;
    memset(g_mem+0x100000,73,512*512*4);
    vinyl_png_composite(&c,composite);
    assert(promoted==1&&calls==5&&c.eax==42&&c.esp==0x84&&MR32(0x104)==7);
    for(unsigned i=0;i<512*512*4;i++)assert(g_mem[0x100000+i]==73&&g_mem[0x200000+i]==73);
    enabled=0;c.esp=0x80;vinyl_png_composite(&c,composite);
    assert(promoted==1&&calls==6&&MR32(0x104)==8);
    free(g_mem);puts("PASS 1024 subpixel detail, guest buffer/context restoration and 512 fallback");
}
