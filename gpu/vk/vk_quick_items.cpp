#include "vk_quick_items.h"
#include "vk_internal.h"
#include "vk_menu.h"
#include "vk_ui.h"
#include "longshot_items.h"
#include <atomic>
#include <algorithm>
#include <array>
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
std::atomic<int> equipped{0};
std::atomic<int64_t> equipped_at{0};
std::atomic<int64_t> refreshed{0};
std::atomic<int64_t> requested{0};
int selected = 0, count = 0;
uint32_t displayed = 0;
std::array<int, LONGSHOT_ITEM_COUNT> items{};
int current = 0, previous = 0;
const char* message = "Select an owned item. The game keeps its normal use restrictions.";
struct Hit { float x,y,w,h; int item; };
std::vector<Hit> hits;
int64_t now() { return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
uint32_t mask() { return now() - refreshed.load() < 1200 ? owned.load() : 0; }
int equipped_item() { return now() - equipped_at.load() < 1200 ? equipped.load() : 0; }
void update_layout(uint32_t available) {
    if (displayed == available) return;
    const int remembered = count ? items[selected] : -1;
    displayed = available;
    count = 0;
    for (int item = 0; item < LONGSHOT_ITEM_COUNT; ++item)
        if (available & (1u << item)) items[count++] = item;
    const auto end = items.begin() + count;
    const auto found = std::find(items.begin(), end, remembered);
    selected = found != end ? static_cast<int>(found - items.begin()) : 0;
    hits.clear();
}
void change_page(int step) {
    const int pages = (count + 7) / 8;
    if (!pages) return;
    selected = ((selected / 8 + pages + step) % pages) * 8;
    hits.clear();
}
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
bool hud_visible() { return opts.equipped_hud && !visible() && equipped_item() != 0; }
void draw_hud(ui::Ctx& c) {
    const int item = std::abs(equipped_item());
    if (!item || item > LONGSHOT_ITEM_COUNT) return;
    const float s = c.h / 720.f, x = c.w / 2 - 90*s, y = c.h - 57*s;
    c.d->AddRectFilled({x,y},{x+180*s,y+30*s},ui::kBox,5*s);
    ui::text(c,c.f.body,15*s,{x+12*s,y+6*s},ui::kInkBright,names[item-1],156*s);
}
int take_action() { const int value = action.exchange(0); return now() - requested.load() < 500 ? value : 0; }
void update(int id, int value) {
    if (id == HOS_OPT_QUICK_OWNED) { owned = (uint32_t)value; refreshed = now(); }
    if (id == HOS_OPT_QUICK_RESULT) result = value;
    if (id == HOS_OPT_QUICK_LEFT) left = value;
    if (id == HOS_OPT_QUICK_RIGHT) right = value;
    if (id == HOS_OPT_QUICK_EQUIPPED) {
        equipped = value;
        equipped_at = now();
    }
}
bool tick(uint32_t raw, bool mine, int confirm, int back, const bool* keys, bool scripted_open, bool scripted_previous) {
    static uint32_t held;
    const uint32_t pressed = raw & ~held; held = raw;
    const bool f7 = scripted_open || (host && host->take_key_press ? mine && host->take_key_press(VK_F7) : key(VK_F7, mine));
    const bool enter = keys[7], esc = keys[5];
    const bool arrows[] = {keys[1], keys[4], keys[2], keys[3]};
    const bool swap = scripted_previous || (host && host->take_key_press ? mine && host->take_key_press(VK_F4) : key(VK_F4, mine));
    if (!opts.item_wheel) {
        const bool was = open.exchange(false);
        action = 0;
        current = previous = 0;
        return was;
    }
    const int observed = equipped_item();
    if (!observed || (current && (observed < 0) != (current < 0))) previous = 0;
    else if (current && observed != current) previous = current;
    current = observed;
    update_layout(mask());
    const uint32_t sticks = (1u << HOS_PAD_LSTICK) | (1u << HOS_PAD_RSTICK);
    const bool modifier = mine && (raw & (1u << HOS_PAD_LSTICK));
    if (f7 || (mine && (raw & sticks) == sticks && (pressed & sticks))) {
        open = !open.load();
        hits.clear();
        if (visible() && observed) {
            const auto end = items.begin() + count;
            const auto found = std::find(items.begin(), end, std::abs(observed)-1);
            if (found != end) selected = static_cast<int>(found - items.begin());
        }
    }
    const int previous_result = result.exchange(0);
    if (previous_result < 0) message = "Selection was refused: load a save and wait until gameplay resumes.";
    else if (previous_result > 0) message = "Item selected. Use it with your normal item button.";
    if (!visible() && (swap || (modifier && (pressed & (1u << HOS_PAD_LSHOULDER))))) {
        if (previous && !action.load()) choose(std::abs(previous)-1);
        else message = "Select two different items to use the previous-item shortcut.";
        return true;
    }
    const int pads[] = {HOS_PAD_UP,HOS_PAD_RIGHT,HOS_PAD_DOWN,HOS_PAD_LEFT};
    for (int i=0;i<4;i++) if ((modifier && (pressed & (1u << pads[i]))) ||
            (mine && (GetAsyncKeyState(VK_SHIFT)&0x8000) && arrows[i])) {
        if (visible()) {
            if (!count) { message = "Choose an owned item before assigning a favorite."; return true; }
            *favorites[i] = items[selected] + 1;
            menu_save();
            message = "Favorite saved. Hold L3 + that D-pad direction to select it during play.";
        } else choose(*favorites[i]-1);
        return true;
    }
    if (!visible()) return f7 || (modifier && (raw & LONGSHOT_QUICK_CHORD_PARTS));
    if (!mine && !enter && !esc && !arrows[0] && !arrows[1] && !arrows[2] && !arrows[3]) return true;
    if (esc || (pressed & (1u << back))) { open = false; return true; }
    MkwVkPointer pointer{};
    const bool have_pointer = host && host->pointer && host->pointer(&pointer);
    if (have_pointer && (pointer.pressed & HOS_MOUSE_RIGHT)) { open=false; return true; }
    if (!count) return true;
    if (arrows[2] || (pressed & (1u << HOS_PAD_RSHOULDER))) change_page(1);
    if (arrows[0] || (pressed & (1u << HOS_PAD_LSHOULDER))) change_page(-1);
    const int first = selected / 8 * 8, slots = std::min(8, count - first);
    if (arrows[1] || (pressed & (1u << HOS_PAD_RIGHT))) selected = first + (selected-first+1)%slots;
    if (arrows[3] || (pressed & (1u << HOS_PAD_LEFT))) selected = first + (selected-first+slots-1)%slots;
    const int right_axes = right.load();
    const int axes = right_axes ? right_axes : left.load();
    const float ax=(int16_t)axes/32767.f, ay=(int16_t)(axes>>16)/32767.f;
    if (ax*ax+ay*ay > .25f) {
        const int sector = ((int)std::lround(std::atan2(ax,ay)/(3.14159265359f/4))+8)%8;
        if (sector < slots) selected = first + sector;
    }
    if (have_pointer) {
        if (pointer.wheel) change_page(pointer.wheel > 0 ? -1 : 1);
        if (pointer.pressed & HOS_MOUSE_LEFT) for(const auto& h:hits)
            if(pointer.x>=h.x && pointer.x<h.x+h.w && pointer.y>=h.y && pointer.y<h.y+h.h) {
                selected=h.item;
                choose(items[selected]);
                return true;
            }
    }
    if (enter || (pressed & (1u << confirm))) choose(items[selected]);
    return true;
}
void draw(ui::Ctx& c) {
    if (!visible()) return;
    const float s=std::min(c.h/720.f,c.w/920.f), cx=c.w/2, cy=c.h/2, r=210*s;
    c.d->AddRectFilled({cx-450*s,30*s},{cx+450*s,c.h-30*s},ui::kBox,10*s);
    ui::text(c,c.f.heading,28*s,{cx-390*s,50*s},ui::kInkBright,"Quick items");
    hits.clear();
    if (!count) {
        ui::text(c,c.f.heading,20*s,{cx-140*s,cy-15*s},ui::kSoft,"No usable quick items");
        return;
    }
    char page[48]; snprintf(page,sizeof page,"Page %d / %d",selected/8+1,(count+7)/8);
    ui::text(c,c.f.body,16*s,{cx+290*s,62*s},ui::kSoft,page);
    const int first = selected / 8 * 8;
    for(int i=0;i<8 && first+i<count;i++) {
        const int row=first+i, item=items[row];
        const float a=i*(3.14159265359f/4), x=cx+std::sin(a)*r-90*s, y=cy-std::cos(a)*r-27*s;
        c.d->AddRectFilled({x,y},{x+180*s,y+54*s},row==selected?ui::kCellNameSel:ui::kCellDark,5*s);
        if(row==selected)c.d->AddRect({x,y},{x+180*s,y+54*s},ui::kGold,5*s,0,2*s);
        ui::text(c,c.f.strong,17*s,{x+12*s,y+17*s},row==selected?ui::kGoldHi:ui::kInk,names[item],156*s);
        hits.push_back({x,y,180*s,54*s,row});
    }
    ui::text(c,c.f.strong,20*s,{cx-105*s,cy-35*s},ui::kInkBright,names[items[selected]],210*s);
    ui::text(c,c.f.body,14*s,{cx-105*s,cy+5*s},ui::kSoft,std::abs(current)==items[selected]+1?"Equipped":"Confirm to select",210*s);
    ui::text(c,c.f.body,14*s,{cx-400*s,c.h-112*s},ui::kSoft,message,800*s);
    ui::text(c,c.f.body,14*s,{cx-400*s,c.h-82*s},ui::kInk,
      "Stick / Left-Right: choose   L1-R1 / Up-Down: page   Back / Esc: cancel\nL3 + D-pad or Shift + arrow: save a favorite. F4 or L3 + L1: previous item during play.",800*s);
}
}
