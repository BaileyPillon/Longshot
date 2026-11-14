#include "vk_quick_items.h"
#include "vk_internal.h"
#include "vk_menu.h"
#include "vk_ui.h"
#include "longshot_items.h"
#include <atomic>
#include <chrono>
#include <cmath>
#include <vector>

namespace mkwvk::quick {
namespace {
#define ITEM_NAME(label, value, actor, ages, bottle) label,
const char* names[] = {LONGSHOT_ITEMS(ITEM_NAME)};
#undef ITEM_NAME
std::atomic<bool> open{false};
std::atomic<int> action{0}, result{0}, left{0}, right{0};
std::atomic<uint32_t> owned{0};
std::atomic<int64_t> refreshed{0};
std::atomic<int64_t> requested{0};
int selected = 0;
const char* message = "Select an owned item. The game keeps its normal use restrictions.";
struct Hit { float x,y,w,h; int item; };
std::vector<Hit> hits;
int64_t now() { return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
uint32_t mask() { return now() - refreshed.load() < 1200 ? owned.load() : 0; }
bool key(int code, bool mine) {
    static bool held[256]{};
    const bool down = mine && (GetAsyncKeyState(code) & 0x8000), edge = down && !held[code];
    held[code] = down; return edge;
}
void choose(int item) {
    if (item < 0 || item >= LONGSHOT_ITEM_COUNT || !(mask() & (1u << item))) {
        message = "That item is unavailable for this age or is not currently owned.";
        return;
    }
    requested = now();
    action = item + 1;
    open = false;
}
int* favorites[] = {&opts.quick_up, &opts.quick_right, &opts.quick_down, &opts.quick_left};
}
const char* item_name(int value) { return value > 0 && value <= LONGSHOT_ITEM_COUNT ? names[value-1] : "None"; }
bool visible() { return open.load(); }
int take_action() { const int value = action.exchange(0); return now() - requested.load() < 500 ? value : 0; }
void update(int id, int value) {
    if (id == HOS_OPT_QUICK_OWNED) { owned = (uint32_t)value; refreshed = now(); }
    if (id == HOS_OPT_QUICK_RESULT) result = value;
    if (id == HOS_OPT_QUICK_LEFT) left = value;
    if (id == HOS_OPT_QUICK_RIGHT) right = value;
}
bool tick(uint32_t raw, bool mine, int confirm, int back, const bool* keys) {
    static uint32_t held;
    const uint32_t pressed = raw & ~held; held = raw;
    const bool f7 = host && host->take_key_press ? mine && host->take_key_press(VK_F7) : key(VK_F7, mine);
    const bool enter = keys[7], esc = keys[5];
    const bool arrows[] = {keys[1], keys[4], keys[2], keys[3]};
    if (!opts.item_wheel) { const bool was = open.exchange(false); action = 0; return was; }
    const uint32_t sticks = (1u << HOS_PAD_LSTICK) | (1u << HOS_PAD_RSTICK);
    const bool modifier = mine && (raw & (1u << HOS_PAD_LSTICK));
    if (f7 || (mine && (raw & sticks) == sticks && (pressed & sticks))) open = !open.load();
    const int previous_result = result.exchange(0);
    if (previous_result < 0) message = "Selection was refused: load a save and wait until gameplay resumes.";
    else if (previous_result > 0) message = "Item selected. Use it with your normal item button.";
    const int pads[] = {HOS_PAD_UP,HOS_PAD_RIGHT,HOS_PAD_DOWN,HOS_PAD_LEFT};
    for (int i=0;i<4;i++) if ((modifier && (pressed & (1u << pads[i]))) ||
            (mine && (GetAsyncKeyState(VK_SHIFT)&0x8000) && arrows[i])) {
        if (visible()) {
            if (!(mask() & (1u << selected))) { message = "Choose an owned item before assigning a favorite."; continue; }
            *favorites[i] = selected + 1;
            menu_save();
            message = "Favorite saved. Hold L3 + that D-pad direction to select it during play.";
        } else choose(*favorites[i]-1);
        return true;
    }
    if (!visible()) return f7 || modifier;
    if (!mine) return true;
    if (esc || (pressed & (1u << back))) { open = false; return true; }
    if (arrows[1] || (pressed & (1u << HOS_PAD_RIGHT))) selected = (selected/8)*8 + (selected+1)%8;
    if (arrows[3] || (pressed & (1u << HOS_PAD_LEFT))) selected = (selected/8)*8 + (selected+7)%8;
    if (arrows[2] || (pressed & (1u << HOS_PAD_RSHOULDER))) selected = (selected+8)%32;
    if (arrows[0] || (pressed & (1u << HOS_PAD_LSHOULDER))) selected = (selected+24)%32;
    const int axes = right.load() ? right.load() : left.load();
    const float ax=(int16_t)axes/32767.f, ay=(int16_t)(axes>>16)/32767.f;
    if (ax*ax+ay*ay > .25f) {
        const int sector = ((int)std::lround(std::atan2(ax,ay)/(3.14159265359f/4))+8)%8;
        selected = (selected/8)*8+sector;
    }
    MkwVkPointer pointer{};
    if (host && host->pointer && host->pointer(&pointer)) {
        if (pointer.pressed & HOS_MOUSE_RIGHT) { open=false; return true; }
        if (pointer.wheel) selected = (selected+32+(pointer.wheel>0?24:8))%32;
        if (pointer.pressed & HOS_MOUSE_LEFT) for(const auto& h:hits)
            if(pointer.x>=h.x && pointer.x<h.x+h.w && pointer.y>=h.y && pointer.y<h.y+h.h) { selected=h.item; choose(selected); return true; }
    }
    if (enter || (pressed & (1u << confirm))) choose(selected);
    return true;
}
void draw(ui::Ctx& c) {
    if (!visible()) return;
    const float s=c.h/720.f, cx=c.w/2, cy=c.h/2, r=210*s;
    c.d->AddRectFilled({cx-450*s,30*s},{cx+450*s,c.h-30*s},ui::kBox,10*s);
    ui::text(c,c.f.heading,28*s,{cx-390*s,50*s},ui::kInkBright,"Quick items");
    char page[48]; snprintf(page,sizeof page,"Page %d / 4",selected/8+1);
    ui::text(c,c.f.body,16*s,{cx+290*s,62*s},ui::kSoft,page);
    const uint32_t available=mask(); hits.clear();
    for(int i=0;i<8;i++) {
        const int item=(selected/8)*8+i;
        const float a=i*(3.14159265359f/4), x=cx+std::sin(a)*r-90*s, y=cy-std::cos(a)*r-27*s;
        const bool have=(available&(1u<<item))!=0;
        c.d->AddRectFilled({x,y},{x+180*s,y+54*s},item==selected?ui::kCellNameSel:ui::kCellDark,5*s);
        if(item==selected)c.d->AddRect({x,y},{x+180*s,y+54*s},ui::kGold,5*s,0,2*s);
        ui::text(c,c.f.strong,17*s,{x+12*s,y+17*s},have?(item==selected?ui::kGoldHi:ui::kInk):ui::kSoft,names[item],156*s);
        hits.push_back({x,y,180*s,54*s,item});
    }
    ui::text(c,c.f.strong,20*s,{cx-105*s,cy-35*s},ui::kInkBright,names[selected],210*s);
    ui::text(c,c.f.body,14*s,{cx-105*s,cy+5*s},ui::kSoft,(available&(1u<<selected))?"Confirm to select":"Unavailable",210*s);
    ui::text(c,c.f.body,14*s,{cx-400*s,c.h-112*s},ui::kSoft,message,800*s);
    ui::text(c,c.f.body,14*s,{cx-400*s,c.h-82*s},ui::kInk,
      "Stick / Left-Right: choose   L1-R1 / Up-Down: page   Back / Esc: cancel\nHold L3 + D-pad here to save a favorite; use the same chord during play. Keyboard: Shift + arrow.",800*s);
}
}
