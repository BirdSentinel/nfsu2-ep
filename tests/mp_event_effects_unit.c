/* cc -O1 -Iruntime/web/compat -ffunction-sections -fdata-sections tests/mp_event_effects_unit.c
 * -Wl,--gc-sections -lm -o out/mp_event_effects_unit */
#include <assert.h>
#include <stdlib.h>
#include "../runtime/roam_game.c"
uint8_t *g_mem;
uint8_t g_cbits[1u<<15];
static void setup(void){
    memset(g_mem, 0, 0x1000000);
    O.on = g_net_ok = g_in_roam = 1;
    MR32(G_CAREER + C_STAGE) = 2;
    MR32(G_PLAYER1) = 0x1000; MR32(0x1004) = 0x2000;
    MRF32(0x7a5734) = 100;
    g_spot.n = 1; g_spot.first = 0x3000; g_spot.end = 0x4000;
    g_spot.s[0] = (MpSpot){.trig=0x3000,.race=0x5000,.kind=MPS_ONLY};
    MR32(0x3030) = MR32(0x5028) = 123;
    MRF32(0x3004) = 10;
    for (unsigned i=0;i<12;i++){ MR32(0x802300+i*12) = 0; MR32(0x802304+i*12) = i; }
}
int main(void){
    g_mem = calloc(1, 0x1000000); assert(g_mem); memset(g_cbits, 255, sizeof g_cbits);
    setup(); roam_game_event_effects(); assert(MR32(0x890020)==0x3000); assert(MRF32(0x890024)==100);
    /* Keep a nearer native career event; replace a farther one. */
    MR32(0x890020)=0x3100; MRF32(0x890024)=25; roam_game_event_effects(); assert(MR32(0x890020)==0x3100);
    MRF32(0x890024)=400; roam_game_event_effects(); assert(MR32(0x890020)==0x3000);
    for(int k=0;k<7;k++){
        setup();
        const unsigned char raceTypes[]={0,4,2,5,1,0,0};
        MR8(0x500f)=raceTypes[k]; if(k==5)MR8(0x5034)=2; if(k==6)MR8(0x500d)=1;
        roam_game_event_effects(); assert(MR32(0x890020+(k==6?7:k)*8)==0x3000);
        /* The career's event lists stay unchanged. */
        for(unsigned i=0;i<0x600;i++)assert(MR8(G_CAREER+i)==0);
    }
    for(int k=0;k<8;k++){
        setup();
        switch(k){
        case 0: O.on=0;break; case 1: g_net_ok=0;break; case 2:g_in_roam=0;break;
        case 3:MR32(G_CAREER+C_GUIDED)=1;break;
        case 4: MRF32(0x3004)=101;break; case 5:g_spot.s[0].kind=MPS_OPEN;break;
        case 6:g_spot.first=0x3100;break;case 7:MR32(0x3030)=999;break;
        }
        roam_game_event_effects(); assert(!MR32(0x890020));
    }
    puts("PASS native multiplayer effects: types, nearest, distance, lifecycle, career isolation");
    free(g_mem);
}

