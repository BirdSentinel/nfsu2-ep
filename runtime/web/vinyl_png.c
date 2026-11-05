/* Portable PNG vinyl overrides. Electron decodes/quantizes PNGs at launch;
 * the game still decompresses and owns its original texture allocation.
 * Replace only its indexed mip chain and palette, preserving all pointers,
 * dimensions, hashes and the texture-pack loader's relocation metadata. */
#include "cpu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int fileio_resolve_game(const char *, char *, size_t);

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
        memcpy(data, replacement + 16, 349504);
        memcpy(data + palette_offset, replacement + 16 + 349504, 1024);
        fprintf(stderr, "[vinyl-png] replaced %s\n", name);
    } else fprintf(stderr, "[vinyl-png] invalid override for %s: original retained\n", name);
    free(replacement);
}
