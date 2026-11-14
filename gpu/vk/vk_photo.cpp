#include "vk_photo.h"
#include "vk_menu.h"
#include "vk_ui.h"
#include "vk_paths.h"
#include <atomic>
#include <chrono>
#include <filesystem>
#include <mutex>
#include <thread>

namespace mkwvk::photo {
namespace {
std::atomic<bool> enabled{false}, pending{false};
std::atomic<int64_t> player_at{0}, activity_at{0};
std::atomic<int> lens{100};
bool guides = true;
std::mutex message_lock;
std::string message = "The world keeps running. Choose a safe place before using the camera.";
int64_t now() { return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
void note(std::string value) { std::lock_guard lock(message_lock); message = std::move(value); }
bool key(int code, bool mine) {
    if (host && host->take_key_press) { const bool pressed=host->take_key_press(code); return mine && pressed; }
    static bool held[256]{};
    const bool down=mine && (GetAsyncKeyState(code)&0x8000), pressed=down && !held[code];
    held[code]=down; return pressed;
}
void capture() {
    if (pending.exchange(true)) return;
    note("Saving photograph...");
    std::thread([] {
        try {
            char module[4096]{};
            if (!game_module_path(module, sizeof module)) throw std::runtime_error("game folder unavailable");
            const auto directory=std::filesystem::u8path(module).parent_path()/"screenshots";
            std::filesystem::create_directories(directory);
            const auto stamp=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
            const auto path=directory/("Longshot-"+std::to_string(stamp)+".png");
            const auto utf8=path.u8string();
            const std::string target(utf8.begin(),utf8.end());
            if (!shot_ask_next(target.c_str(),[](void*,int64_t,int ok) {
                    note(ok ? "Photograph saved in this game's screenshots folder." : "Photograph could not be saved.");
                    pending=false;
                },nullptr)) { note("Screenshot service is busy. Try again."); pending=false; }
        } catch (const std::exception&) { note("Could not create the screenshots folder."); pending=false; }
    }).detach();
}
}
bool active() { return enabled.load(); }
void ready(bool value) { player_at=value ? now() : 0; }
void activity() { activity_at=now(); }
int hud() {
    if (active()) return 0;
    if (!opts.context_hud || now()-player_at.load()>1200) return -1;
    return now()-activity_at.load()<4000 ? 1 : 0;
}
int fov() { return active() ? lens.load() : opts.fov; }
bool tick(uint32_t raw,bool mine,int back,const bool* keys) {
    static uint32_t held;
    const uint32_t pressed=raw&~held; held=raw;
    const bool f8=key(VK_F8,mine), f9=key(VK_F9,mine), f12=key(VK_F12,mine);
    const uint32_t chord=(1u<<HOS_PAD_TOUCHPAD)|(1u<<HOS_PAD_RSTICK);
    const bool toggle=f8 || (mine && (raw&chord)==chord && (pressed&chord));
    const bool was=active();
    if (active() && now()-player_at.load()>1200) enabled=false;
    if (toggle) {
        if (active()) enabled=false;
        else if (now()-player_at.load()<1200) { enabled=true; lens=opts.fov; guides=true; }
    }
    if (!active()) return was;
    if (keys[5] || (pressed&(1u<<back))) { enabled=false; return true; }
    if (f9 || (pressed&(1u<<HOS_PAD_LSTICK))) guides=!guides;
    if (f12 || (pressed&(1u<<HOS_PAD_NORTH))) capture();
    if (keys[3] || (pressed&(1u<<HOS_PAD_LEFT))) lens=std::max(50,lens.load()-5);
    if (keys[4] || (pressed&(1u<<HOS_PAD_RIGHT))) lens=std::min(150,lens.load()+5);
    return true;
}
void draw(ui::Ctx& c) {
    if (!active() || !guides) return;
    const float s=c.h/720.f;
    for(int i=1;i<3;i++) {
        c.d->AddLine({c.w*i/3,0},{c.w*i/3,c.h},IM_COL32(255,255,255,70));
        c.d->AddLine({0,c.h*i/3},{c.w,c.h*i/3},IM_COL32(255,255,255,70));
    }
    const float x=28*s,y=c.h-110*s;
    c.d->AddRectFilled({x,y},{c.w-x,c.h-20*s},ui::kBox,6*s);
    ui::text(c,c.f.strong,18*s,{x+16*s,y+10*s},ui::kInkBright,
        "Photo camera  |  F12 / Triangle: capture  |  F9 / L3: guides  |  F8 / Back: exit",c.w-2*x-32*s);
    ui::text(c,c.f.body,14*s,{x+16*s,y+37*s},ui::kInk,
        "Sticks: move / look    L1-R1 / PageUp-Down: height    D-pad Left-Right: lens",c.w-2*x-32*s);
    std::lock_guard lock(message_lock);
    ui::text(c,c.f.body,14*s,{x+16*s,y+61*s},ui::kSoft,message.c_str(),c.w-2*x-32*s);
}
}
