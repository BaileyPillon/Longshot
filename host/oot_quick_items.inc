/* Included after hos_main.c's GameData helpers, on the serialized player update.
   The enum setter was located from oot-coop's documented flag layout and checked
   against the local supported image. All game calls remain on the guest thread. */
#include "../gpu/vk/longshot_items.h"
typedef struct { const char *value, *actor; unsigned ages, bottle; } QuickItem;
#define QUICK_ITEM(label, value, actor, ages, bottle) {value, actor, ages, bottle},
static const QuickItem quick_items[] = {LONGSHOT_ITEMS(QUICK_ITEM)};
#undef QUICK_ITEM

static uint32_t quick_hash(const char *s) {
    uint32_t h = 0, k; size_t n = strlen(s), i = 0;
    for (; i + 4 <= n; i += 4) {
        k = (uint32_t)(unsigned char)s[i] | (uint32_t)(unsigned char)s[i+1] << 8 |
            (uint32_t)(unsigned char)s[i+2] << 16 | (uint32_t)(unsigned char)s[i+3] << 24;
        k *= 0xcc9e2d51u; k = k << 15 | k >> 17; k *= 0x1b873593u;
        h ^= k; h = h << 13 | h >> 19; h = h * 5 + 0xe6546b64u;
    }
    k = 0;
    for (size_t j = i; j < n; j++) k |= (uint32_t)(unsigned char)s[j] << (8 * (j-i));
    if (i < n) { k *= 0xcc9e2d51u; k = k << 15 | k >> 17; k *= 0x1b873593u; h ^= k; }
    h ^= (uint32_t)n; h ^= h >> 16; h *= 0x85ebca6bu; h ^= h >> 13; h *= 0xc2b2ae35u; h ^= h >> 16;
    return h;
}
static int quick_owned(Ctx *c, unsigned index, int child) {
    if (index >= LONGSHOT_ITEM_COUNT) return 0;
    const QuickItem *item = &quick_items[index];
    if (!(item->ages & (child ? 1u : 2u))) return 0;
    if (item->bottle) {
        int valid = 0;
        return oot_gamedata_bool(c, item->bottle, &valid) && valid;
    }
    if (index >= 22 && index <= 24 && oot_item_count(c, "Weapon_Range_Bow") <= 0) return 0;
    return oot_item_count(c, item->actor) > 0;
}
static int quick_assign(Ctx *c, unsigned index, int child) {
    if (!quick_owned(c, index, child)) return 0;
    const uint64_t mgr = oot_singleton(c, OOT_GAMEDATA_SLOT);
    A64Fn set = a64_lookup(0x80400980ULL); /* GameDataMgr::setEnum(mgr, valueHash, flagHash) */
    if (!mgr || !set) return 0;
    /* Leave most of the game's queue free. Its own setter aborts on exhaustion. */
    const uint32_t capacity = recomp_load32(c, mgr + 0x270);
    if (!capacity || capacity > 65536 || (recomp_load32(c, mgr + 0x280) & 0xfffff) >= capacity / 2) return 0;
    const Ctx saved = *c;
    c->x[0] = mgr; c->x[1] = quick_hash(quick_items[index].value);
    c->x[2] = child ? 0xa0029837u : 0xbc32ce24u; c->x[30] = 0;
    set(c);
    *c = saved;
    hos_log("longshot: selected owned %s for %s Link", quick_items[index].value, child ? "child" : "adult");
    return 1;
}
static void quick_items_tick(Ctx *c, int64_t now) {
    int rx_option(int id, int otherwise); void rx_option_set(int id, int value);
    const int action = rx_option(HOS_OPT_QUICK_ACTION, 0);
    if (!rx_option(HOS_OPT_ITEM_WHEEL, 0)) return;
    int child = 1, loading = 1;
    const int ready = oot_gamedata_bool(c, 0xcea220d3u, &child) &&
        oot_gamedata_bool(c, 0xef2b60c2u, &loading) && !loading && !oot_event_playing(c);
    if (action) rx_option_set(HOS_OPT_QUICK_RESULT, ready && quick_assign(c, (unsigned)(action-1), child) ? action : -1);
    static int64_t next;
    if (!action && now < next) return;
    next = now + 200000000LL;
    uint32_t mask = 0;
    if (ready) for (unsigned i = 0; i < LONGSHOT_ITEM_COUNT; i++) if (quick_owned(c, i, child)) mask |= 1u << i;
    rx_option_set(HOS_OPT_QUICK_OWNED, (int)mask);
}
