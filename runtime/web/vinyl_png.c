/* Portable PNG vinyl overrides. Electron decodes/quantizes PNGs at launch;
 * the game still decompresses and owns its original texture allocation.
 * Replace only its indexed mip chain and palette, preserving all pointers,
 * dimensions, hashes and the texture-pack loader's relocation metadata. */
#include "cpu.h"
#include "guest_span.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int fileio_resolve_game(const char *, char *, size_t);

/* The retail compositor has fixed-size paint-marker tables. Evaluate the four
 * subpixel phases separately in its existing 512 allocations, then interleave
 * their results. This retains its paint/recolour/mask semantics at 1024 without
 * changing guest pointers, allocation sizes or the original archive. */
#define HD_PIXELS 1398080u
#define BASE_BYTES (512u * 512u * 4u)
extern void metal_replace_texture(unsigned, unsigned, unsigned, unsigned, unsigned, const uint8_t *);
static struct { uint32_t hash; char car[25]; } hd_names[256];
static unsigned hd_name_next;
static int guest_range(uint32_t p, size_t n){
#ifdef __wasm__
    return guest_span(1, p, (uint32_t)n);
#else
    return p && (uint64_t)p+n <= GSZ;
#endif
}
static uint8_t *hd_read(uint32_t ti){
    if (!guest_range(ti, 0x7c) || MR16(ti+0x44)!=512 || MR16(ti+0x46)!=512) return NULL;
    char car[25]={0}, win[128], path[1024];
    /* TextureInfo's label is discarded by the retail loader. Remember the car
     * alongside the authoritative hash when its safe 512 override is decoded. */
    for(unsigned i=0;i<256;i++) if(hd_names[i].hash==MR32(ti+0x24) && hd_names[i].car[0]){
        memcpy(car,hd_names[i].car,sizeof car); break;
    }
    if(!car[0]) return NULL;
    snprintf(win,sizeof win,"CARS\\%s\\VINYLS\\%08x.vph",car,MR32(ti+0x24));
    if(!fileio_resolve_game(win,path,sizeof path)) return NULL;
    FILE *f=fopen(path,"rb"); if(!f) return NULL;
    size_t size=16+HD_PIXELS+1024; uint8_t *p=malloc(size); uint32_t h[4];
    int ok=p && fread(p,1,size,f)==size && fgetc(f)==EOF; fclose(f);
    if(ok){ memcpy(h,p,16); ok=!memcmp(p,"VPX1",4)&&h[1]==1024&&h[2]==1024&&h[3]==8; }
    if(!ok){ free(p); return NULL; } return p;
}
void vinyl_png_composite(CPU *c, void (*original)(CPU *)){
    uint32_t ctx=MR32(c->esp+4);
    if(!guest_range(ctx,0x1c8)){ original(c); return; }
    uint32_t ti=MR32(ctx), count=MR32(ctx+0x1c4);
    if(!guest_range(ti,0x7c)||MR8(ti+0x4a)!=32||MR16(ti+0x44)!=512||MR16(ti+0x46)!=512||count>8){ original(c); return; }
    uint32_t plat=MR32(ti), obj=guest_range(plat,0x1c)?MR32(plat+0x18):0;
    if(!guest_range(obj,160)){ original(c); return; }
    uint32_t mid=MR32(obj+28), fmt=MR32(obj+20), levels=MR32(obj+24);
    if(fmt!=21 && fmt!=22){ original(c); return; }
    /* Clear a previous HD image, including when the user removes the vinyl. */
    metal_replace_texture(mid,512,512,levels,fmt,NULL);
    struct Input { uint32_t pixels; uint8_t *hd, *backup; } inputs[16]={0};
    unsigned n=0;
    for(unsigned i=0;i<count;i++) for(unsigned k=0;k<2;k++){
        uint32_t l=ctx+0x24+i*0x34, src=MR32(l+4+k*4), pixels=MR32(l+12+k*8);
        if(!MR32(l)||!guest_range(src,0x7c)||!guest_range(pixels,BASE_BYTES)) continue;
        if(MR32(l+16+k*8)) continue;
        int duplicate=0; for(unsigned j=0;j<n;j++) if(inputs[j].pixels==pixels) duplicate=1;
        if(duplicate) continue;
        uint8_t *hd=hd_read(src); if(!hd) continue;
        uint8_t *backup=malloc(BASE_BYTES); if(!backup){ free(hd); continue; }
        memcpy(backup,g_mem+pixels,BASE_BYTES); inputs[n++]=(struct Input){pixels,hd,backup};
    }
    uint8_t context[0x1c8]; memcpy(context,g_mem+ctx,sizeof context); CPU entry=*c;
    /* Initialize the native paint-marker cache and retain the normal guest result. */
    original(c); CPU result=*c; uint8_t returned[0x1c8]; memcpy(returned,g_mem+ctx,sizeof returned);
    uint32_t output=MR32(obj+32);
    uint8_t *hd=n && guest_range(output,BASE_BYTES)?malloc(HD_PIXELS*4u):NULL;
    uint8_t *normal=hd?malloc(BASE_BYTES):NULL;
    if(hd && normal){
        memcpy(normal,g_mem+output,BASE_BYTES);
        for(unsigned phase=0;phase<4;phase++){
            for(unsigned j=0;j<n;j++){
                uint8_t *indices=inputs[j].hd+16, *palette=indices+HD_PIXELS;
                for(unsigned y=0;y<512;y++) for(unsigned x=0;x<512;x++){
                    unsigned ix=(2*y+(phase>>1))*1024+2*x+(phase&1);
                    memcpy(g_mem+inputs[j].pixels+(y*512+x)*4,palette+indices[ix]*4,4);
                }
            }
            memcpy(g_mem+ctx,context,sizeof context); *c=entry; original(c);
            for(unsigned y=0;y<512;y++) for(unsigned x=0;x<512;x++)
                memcpy(hd+((2*y+(phase>>1))*1024+2*x+(phase&1))*4,g_mem+output+(y*512+x)*4,4);
        }
        memcpy(g_mem+output,normal,BASE_BYTES);
        /* Native textures stop at 8x8; retain the same cutoff at twice the resolution. */
        size_t at=0, next=1024u*1024u*4u;
        for(unsigned w=1024;w>8;w/=2){
            unsigned nw=w/2;
            for(unsigned y=0;y<nw;y++) for(unsigned x=0;x<nw;x++) for(unsigned k=0;k<4;k++){
                unsigned p=at+(2*y*w+2*x)*4+k;
                hd[next+(y*nw+x)*4+k]=(hd[p]+hd[p+4]+hd[p+w*4]+hd[p+w*4+4]+2)/4;
            }
            at=next; next+=(size_t)nw*nw*4;
        }
        metal_replace_texture(mid,1024,1024,8,fmt,hd);
        static unsigned logged; if(logged++<8) fprintf(stderr,"[vinyl-hd] 1024x1024 composite t%u (%u HD inputs)\n",mid,n);
    }
    for(unsigned j=0;j<n;j++){ memcpy(g_mem+inputs[j].pixels,inputs[j].backup,BASE_BYTES); free(inputs[j].hd); free(inputs[j].backup); }
    /* Preserve the ordinary compositor's returned context, including colour conversions. */
    memcpy(g_mem+ctx,returned,sizeof returned); *c=result;
    free(normal); free(hd);
}

void vinyl_png_decoded(uint32_t out, uint32_t size){
    /* Retail 512-square P8 vinyls: seven mips, aligned palette, 156-byte trailer. */
    /* Binarius-authored packs omit the retail palette's 64-byte padding. */
    if (size != 350748u && size != 350684u) return;
    uint8_t *data = g_mem + out, *ti = data + size - 156u;
    uint32_t image_size, palette_size, image_at, palette_at;
    memcpy(&image_at, ti + 0x30, 4); memcpy(&palette_at, ti + 0x34, 4);
    memcpy(&image_size, ti + 0x38, 4); memcpy(&palette_size, ti + 0x3c, 4);
    uint32_t palette_offset = palette_at - image_at;
    if (image_size != 349504u || palette_size != 1024u
        || (palette_offset != 349568u && palette_offset != 349504u)
        || palette_offset + palette_size + 156u != size
        || ti[0x44] != 0 || ti[0x45] != 2 || ti[0x46] != 0 || ti[0x47] != 2 || ti[0x4e] != 7) return;
    char name[25], car[25]; unsigned len = 0, split = 0;
    for (; len < 24 && ti[12 + len]; len++){
        unsigned char ch = ti[12 + len];
        if (!((ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '_')) return;
        name[len] = (char)ch;
        if (ch == '_' && !split) split = len;
    }
    if (!split || !len) return;
    name[len] = 0; memcpy(car, name, split); car[split] = 0;
    char win[128], path[1024];
    uint32_t texture_hash; memcpy(&texture_hash, ti + 36, 4);
    /* Hash is authoritative: long retail texture labels can be truncated. */
    snprintf(win, sizeof win, "CARS\\%s\\VINYLS\\%08x.vpx", car, texture_hash);
    if (!fileio_resolve_game(win, path, sizeof path)) return;
    FILE *fp = fopen(path, "rb");
    if (!fp) return;
    const size_t total = 16u + 349504u + 1024u;
    uint8_t *replacement = malloc(total); uint32_t hd[4];
    int ok = replacement && fread(replacement, 1, total, fp) == total && fgetc(fp) == EOF;
    fclose(fp);
    if (ok){
        memcpy(hd, replacement, sizeof hd);
        ok = !memcmp(replacement, "VPX1", 4) && hd[1] == 512 && hd[2] == 512 && hd[3] == 7;
    }
    if (ok){
        unsigned slot=256;
        for(unsigned i=0;i<256;i++) if(hd_names[i].hash==texture_hash && hd_names[i].car[0]){ slot=i; break; }
        if(slot==256) slot=hd_name_next++%256;
        hd_names[slot].hash=texture_hash; snprintf(hd_names[slot].car,sizeof hd_names[slot].car,"%s",car);
        memcpy(data, replacement + 16, 349504);
        memcpy(data + palette_offset, replacement + 16 + 349504, 1024);
        fprintf(stderr, "[vinyl-png] replaced %s\n", name);
    } else fprintf(stderr, "[vinyl-png] invalid override for %s: original retained\n", name);
    free(replacement);
}
