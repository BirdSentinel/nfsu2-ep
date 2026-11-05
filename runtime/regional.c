/* regional.c -- the European game's own cars, the Vauxhall Corsa and the
 * Peugeot 106, in this North American game.
 *
 * The game folder has both (CARS\CORSA, CARS\PEUGOT106: the same files as the
 * European release's) and CarTypeInfo lists them (types 7 and 6, among the 31
 * player cars, with their names in every language's text), but the North
 * American exe keeps them off its lists by the game's region ([0x864f24],
 * 0x570a30; 0 in this exe):
 *  - 0x5022c0, whether the region sells a car type, for the car lot
 *    (UICareerCarLot::BuildCarList, 0x4df9c0, at 0x4dfa83) and every other
 *    car select (UIQRCarSelect::BuildCarList, 0x4e22e0, at 0x4e2374: Quick
 *    Race, Customize, LAN, and Online's UI_OLCarSelect.fng, whose screen is
 *    made by the same 0x4fc190): no for a type in the region's table, region
 *    0's {7, 6} at 0x7f7c48, the others' {5, 18} (the Civic and the RSX) at
 *    0x7f7c50;
 *  - 0x4feaf0, the AI racers' cars: a random one rated near the player's car
 *    from the region's 26 types (region 0's at 0x7f6da4, the others' at
 *    0x7f6dc0 with 7 and 6 in place of 5 and 18; 3 SUVs at 0x7f6ddc when
 *    the player drives an SUV).
 * Here region 0's table holds no type (-1), and its AI list is 28 long, the
 * two in the padding after it (read by nothing else; HOOK_SITE 0x4febad,
 * where both lists' paths meet).  The same as NFSU2 Extra Options'
 * UnlockRegionalCars (ExOptsTeam/NFSU2ExOpts, ExtraOptionsStuff.h).  The
 * page's save check (web/src/app/profile.ts) has always counted both among
 * the game's cars. */
#include "cpu.h"
#include "widescreen.h"           /* HOOK_SITE */
#include <stdio.h>
#include <sys/stat.h>

extern int fileio_resolve_game(const char *, char *, size_t);

/* Retail North American folders do not include these optional cars. Never
 * offer them to the player or AI unless their required assets are present. */
static int regional_assets_present(void){
    const char *cars[] = { "CORSA", "PEUGOT106" };
    const char *files[] = { "GEOMETRY.BIN", "TEXTURES.BIN", "VINYLS.BIN" };
    for (unsigned c = 0; c < 2; c++) for (unsigned f = 0; f < 3; f++){
        char win[128], path[1024]; struct stat st;
        snprintf(win, sizeof win, "CARS\\%s\\%s", cars[c], files[f]);
        if (!fileio_resolve_game(win, path, sizeof path) || stat(path, &st) || !S_ISREG(st.st_mode) || st.st_size <= 0)
            return 0;
    }
    return 1;
}

#define LOCKED_NA       0x007f7c48u   /* 2 car types region 0 does not sell */
#define AI_CARS_NA      0x007f6da4u   /* region 0's AI car types, a byte each */
#define AI_CARS_NA_N    26u
#define T_PEUGOT106     6u
#define T_CORSA         7u

static int g_on;

void regional_install(void){
    if (!regional_assets_present()){
        fprintf(stderr, "[cars] optional Corsa/106 assets absent: keeping the North American car lists\n");
        return;
    }
    /* only on the data of the exe this port is made for */
    if (MR32(LOCKED_NA) != T_CORSA || MR32(LOCKED_NA + 4u) != T_PEUGOT106
        || MR8(AI_CARS_NA + AI_CARS_NA_N - 2u) != 5u || MR8(AI_CARS_NA + AI_CARS_NA_N - 1u) != 18u
        || MR16(AI_CARS_NA + AI_CARS_NA_N) != 0u){
        fprintf(stderr, "[cars] the exe's region tables are not the ones expected: no Corsa or 106\n");
        return;
    }
    MR32(LOCKED_NA) = MR32(LOCKED_NA + 4u) = 0xffffffffu;
    MR8(AI_CARS_NA + AI_CARS_NA_N) = T_CORSA;
    MR8(AI_CARS_NA + AI_CARS_NA_N + 1u) = T_PEUGOT106;
    g_on = 1;
}

int regional_hook(CPU *c, uint32_t ip){
    /* The retail career list has two padding bytes after its 46 flags. */
    if (ip == HOOK_SITE(0x00513c6c)) {
        if (addon_car_count == 47u) MR8(c->esp + 0x10u + 46u) = 1;
        return 1;
    }
    if (ip == HOOK_SITE(0x00529d18)) {
        c->esi = addon_donor_type(c->esi); /* initial-unlock lookup only */
        return 1;
    }
    if (ip != HOOK_SITE(0x004febad)) return 0;    /* mov eax, [esp+0x34]: esi the list, ebp its length */
    if (g_on && c->esi == AI_CARS_NA && c->ebp == AI_CARS_NA_N) c->ebp = AI_CARS_NA_N + 2u;
    return 1;
}

/* This port does not execute ASI plugins. Keep the single optional MX5NA
 * extension explicit and bounded by the existing 48 stock-profile slots. */
uint32_t addon_car_count = 46u;
uint32_t addon_part_count(void) {
    uint32_t n = MR32(0x008a2b74u);
    /* Existing saves use 16000 as their absent-part sentinel. This one-car
     * extension stays below that ceiling, so retain the retail encoding. */
    return n > 16000u ? n : 16000u;
}

static void addon_rack_parts(uint32_t chunk);
void sub_00636be0_orig(CPU *c);
void sub_00636be0(CPU *c) {
    uint32_t chunk = MR32(c->esp + 4u), id = MR32(chunk);
    if (id == 0x34600u) {
        uint32_t size = MR32(chunk + 4u);
        uint32_t table = (chunk + 0x17u) & ~15u;
        addon_car_count = 46u;
        if (size == 47u * 0x890u + 8u &&
            !memcmp(g_mem + table + 46u * 0x890u, "MX5NA\0", 6) &&
            !memcmp(g_mem + table + 4u * 0x890u, "MIATA\0", 6))
            addon_car_count = 47u;
    }
    if (id == 0x80034602u && addon_car_count == 47u) addon_rack_parts(chunk);
    sub_00636be0_orig(c);
    if (!c->eax) return;
    if (id == 0x34600u) {
        MR32(0x89d2d4u) = 6u;
        MR32(0x89d2dcu) = addon_car_count;
        MR32(0x89d2e0u) = addon_car_count + 1u;
        fprintf(stderr, "[cars] %u car types; Miata NB type 4, MX5NA %s\n",
                addon_car_count, addon_car_count == 47u ? "type 46" : "absent");
    } else if (id == 0x80034602u) {
        uint32_t n = addon_part_count(), bits = 1u;
        while ((1u << bits) < n + 1u && bits < 31u) bits++;
        MR32(0x89d418u) = bits;
        MR32(0x89d420u) = n;
        MR32(0x89d424u) = n + 1u;
    }
}

void addon_stock_append(uint32_t db) {
    if (addon_car_count != 47u) return;
    uint32_t n = MR32(db + 0x540u);
    if (n > 48u) return;
    uint32_t na = 48u, nb = 48u;
    for (uint32_t i = 0; i < n; i++)
        if (MR32(db + i * 0x1cu + 0x18u) == 46u) na = i;
        else if (MR32(db + i * 0x1cu + 0x18u) == 4u) nb = i;
    if (na < n) goto order;
    if (n >= 48u) return;
    uint32_t r = db + n * 0x1cu, hash = 0xffffffffu;
    const char *s = "STOCK_MX5NA";
    while (*s) hash = hash * 33u + (unsigned char)*s++;
    MR32(r) = 0x79aadcu;
    MR32(r + 4u) = MR32(r + 12u) = 0;
    MR32(r + 8u) = hash;
    MR32(r + 16u) = MR32(r + 20u) = 1u;
    MR32(r + 24u) = 46u;
    MR32(db + 0x540u) = n + 1u;
    fprintf(stderr, "[cars] appended MX5NA to loaded profile (%u stock cars)\n", n + 1u);
    na = n++;
order:
    if (nb < na && nb + 1u != na) {
        unsigned char record[0x1c];
        memcpy(record, g_mem + db + na * 0x1cu, sizeof record);
        memmove(g_mem + db + (nb + 2u) * 0x1cu,
                g_mem + db + (nb + 1u) * 0x1cu, (na - nb - 1u) * 0x1cu);
        memcpy(g_mem + db + (nb + 1u) * 0x1cu, record, sizeof record);
    }
}

void sub_00516500_orig(CPU *c);
void sub_00516500(CPU *c) {
    uint32_t db = c->ecx;
    sub_00516500_orig(c);
    addon_stock_append(db);
}

void sub_00513c50_orig(CPU *c);
void sub_00513c50(CPU *c) {
    uint32_t head = MR32(c->esp + 4u);
    sub_00513c50_orig(c);
    if (addon_car_count != 47u) return;
    uint32_t nb = 0, na = 0, p = MR32(head);
    for (unsigned i = 0; p && p != head && i < 48u; i++, p = MR32(p)) {
        if (MR32(p + 8u) == 4u) nb = p;
        if (MR32(p + 8u) == 46u) na = p;
    }
    if (nb && na && MR32(nb) != na) {
        uint32_t next = MR32(na), prev = MR32(na + 4u);
        MR32(prev) = next; MR32(next + 4u) = prev;
        next = MR32(nb);
        MR32(na) = next; MR32(na + 4u) = nb;
        MR32(nb) = na; MR32(next + 4u) = na;
    }
}

void sub_00459240_orig(CPU *c);
void sub_00459240(CPU *c) {
    uint32_t a = c->esp + 4u, type = MR32(a);
    MR32(a) = addon_donor_type(type);
    sub_00459240_orig(c);
    MR32(a) = type;
}

/* Keep saved part indices stable: reuse the NA-only CRIMSON record as EDOLIX.
 * Only its category, rating and display/attribute metadata change; its owner,
 * key and geometry binding remain NA-specific. Shared spoilers stay untouched. */
static uint32_t g_na_rack, g_na_tail;
static void addon_rack_parts(uint32_t chunk) {
    uint32_t end = chunk + 8u + MR32(chunk + 4u);
    for (uint32_t p = chunk + 8u; p + 8u <= end;) {
        uint32_t tag = MR32(p), size = MR32(p + 4u), next = p + 8u + size;
        if (next > end || next <= p) return;
        if (tag == 0x34604u) {
            uint32_t rack = 0, edolix = 0, tail = 0;
            for (uint32_t r = p + 8u; r + 14u <= next; r += 14u) {
                if (MR32(r) == 0xa2bddcb5u) rack = r;
                if (MR32(r) == 0x45f085d5u) edolix = r;
                if (MR32(r) == 0x572b056bu) tail = r;
            }
            if (rack && edolix && tail) {
                MR16(rack + 4u) = MR16(edolix + 4u);
                MR32(rack + 8u) = MR32(edolix + 8u);
                g_na_rack = rack; g_na_tail = tail;
                fprintf(stderr, "[cars] MX5NA rack moved to EDOLIX; taillight selection enabled\n");
            }
            return;
        }
        p = next;
    }
}

/* Called before the memoized retail query; skip the shared EDOLIX variants
 * for the NA, whose own rack occupies that choice. */
void sub_0061b980_orig(CPU *c);
int addon_rack_query(CPU *c) {
    uint32_t e = c->esp;
    if (addon_car_count != 47u || !g_na_rack || MR32(e+4u) != 46u || MR32(e+8u) != 12u) return 0;
    CPU initial = *c;
    for (unsigned n = 0; n < 4; n++) {
        sub_0061b980_orig(c);
        uint32_t part = c->eax, key = part ? MR32(part) : 0;
        if (key != 0x45f085d5u && key != 0x0954cebdu) return 1;
        *c = initial; MR32(e+16u) = part;
    }
    c->eax = 0; POP32(c->eip); c->esp += 20u;
    return 1;
}

/* Old saves may still have the rack in the taillight slot. Move that choice
 * to a stock spoiler slot and restore rear lights only for that legacy choice. */
void sub_0061bcd0_orig(CPU *c);
void sub_0061bcd0(CPU *c) {
    uint32_t ride = c->ecx;
    if (addon_car_count == 47u && g_na_rack && g_na_tail && MR32(ride) == 46u) {
        uint32_t tail = ride+0x590u+15u*4u, spoiler = ride+0x590u+12u*4u;
        if (MR32(tail) == g_na_rack) {
            uint32_t old = MR32(spoiler);
            if (!old || MR8(old+5u) == 0u) MR32(spoiler) = g_na_rack;
            MR32(tail) = g_na_tail;
        }
        uint32_t selected = MR32(spoiler);
        if (selected && (MR32(selected) == 0x45f085d5u || MR32(selected) == 0x0954cebdu))
            MR32(spoiler) = g_na_rack;
    }
    sub_0061bcd0_orig(c);
}

void sub_00545700_orig(CPU *c);
void sub_00545700(CPU *c) {
    sub_00545700_orig(c);
}
