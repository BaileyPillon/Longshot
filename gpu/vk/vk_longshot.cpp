// Longshot's native checkpoint browser. The launcher owns archive/restart operations;
// this renderer exchanges bounded text messages only within its unique launch session.
#include "vk_longshot.h"
#include "vk_internal.h"
#include "vk_ui.h"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace mkwvk::longshot {
namespace {
struct Entry { std::string id, name; };
struct State { bool fresh = false; int shortcut = 0; std::string message; std::vector<Entry> entries; };
std::string read_state(const std::filesystem::path& path) {
#ifdef _WIN32
    // std::ifstream omits FILE_SHARE_DELETE on Windows. The launcher must be
    // able to atomically replace its heartbeat while this snapshot is read.
    const HANDLE file = CreateFileW(path.c_str(), GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) throw std::runtime_error("Checkpoint service is updating; retrying...");
    char bytes[16385]; DWORD count = 0;
    const bool ok = ReadFile(file, bytes, sizeof bytes, &count, nullptr) != 0;
    CloseHandle(file);
    if (!ok || count > 16384) throw std::runtime_error("Invalid checkpoint service response.");
    return std::string(bytes, count);
#else
    std::ifstream input(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(input), {});
#endif
}
class Channel {
    std::filesystem::path directory;
    std::mutex mutex;
    State state;
    std::string request;
    std::atomic<bool> stop{false};
    std::thread worker;
    void run() {
        using namespace std::chrono;
        auto next = steady_clock::now();
        while (!stop.load()) {
            std::string outgoing;
            { std::lock_guard lock(mutex); outgoing.swap(request); }
            try {
                if (!outgoing.empty()) {
                    const auto path = directory / "request.txt";
                    if (std::filesystem::exists(path)) throw std::runtime_error("A checkpoint operation is already pending.");
                    const auto temp = directory / "request.tmp";
                    { std::ofstream out(temp, std::ios::binary | std::ios::trunc); out << "LSP1\n" << outgoing << '\n' << GetCurrentProcessId() << '\n';
                      out.flush(); if (!out) throw std::runtime_error("Could not send checkpoint request."); }
                    std::filesystem::rename(temp, path);
                }
                if (steady_clock::now() >= next) {
                    next = steady_clock::now() + milliseconds(350);
                    State update;
                    const auto path = directory / "state.txt";
                    if (std::filesystem::exists(path) && std::filesystem::file_size(path) <= 16384 &&
                        std::filesystem::file_time_type::clock::now() - std::filesystem::last_write_time(path) < seconds(3)) {
                        std::istringstream input(read_state(path));
                        std::string line;
                        std::getline(input, line);
                        if (line != "LSP1") throw std::runtime_error("Unsupported checkpoint service.");
                        std::getline(input, update.message);
                        std::getline(input, line);
                        update.shortcut = line == "1" ? 1 : line == "2" ? 2 : 0;
                        while (update.entries.size() < 32 && std::getline(input, line)) {
                            const auto tab = line.find('\t');
                            if (tab == std::string::npos || tab > 64 || line.size() > 300) continue;
                            const auto id = line.substr(0, tab);
                            if (id.find_first_not_of("0123456789abcdef") != std::string::npos || id.size() != 16) continue;
                            update.entries.push_back({id, line.substr(tab + 1)});
                        }
                        update.fresh = true;
                    } else update.message = "Checkpoint service unavailable. Reopen Longshot's launcher and restart with Player tools.";
                    std::lock_guard lock(mutex); state = std::move(update);
                }
            } catch (const std::exception& error) {
                std::lock_guard lock(mutex); state.fresh = false; state.message = error.what();
            }
            std::this_thread::sleep_for(milliseconds(50));
        }
    }
public:
    Channel() {
        const char* path = std::getenv("LONGSHOT_PLAYER_TOOLS_DIR");
        if (!path || !*path) { state.message = "Start with Player tools in the Longshot launcher to use checkpoints."; return; }
        directory = std::filesystem::u8path(path);
        state.message = "Connecting to the checkpoint service...";
        worker = std::thread([this] { run(); });
    }
    ~Channel() { stop = true; if (worker.joinable()) worker.join(); }
    bool enabled() const { return !directory.empty(); }
    State snapshot() { std::lock_guard lock(mutex); return state; }
    void send(const std::string& value) { std::lock_guard lock(mutex); if (request.empty()) request = value; }
};
Channel& channel() { static Channel value; return value; }
std::atomic<bool> open{false};
int selected = 0, first = 0, confirm_action = 0;
std::string restore_id, restore_name;
struct Hit { float x0,y0,x1,y1; int row; };
std::vector<Hit> hits;
bool key(int code, bool mine) {
    static bool held[256]{};
    const bool down = mine && (GetAsyncKeyState(code) & 0x8000);
    const bool edge = down && !held[code]; held[code] = down;
    return edge;
}
void activate(const State& state) {
    if (!state.fresh) return;
    if (selected == 0) confirm_action = 1;
    else if (selected == 1) channel().send("shortcut " + std::to_string((state.shortcut + 1) % 3));
    else if (selected - 2 < (int)state.entries.size()) {
        const auto& e = state.entries[selected - 2];
        confirm_action = 2; restore_id = e.id; restore_name = e.name;
    }
}
}
bool available() { return channel().enabled(); }
bool visible() { return open.load(std::memory_order_relaxed); }
void show() { open = true; confirm_action = 0; }
bool tick(uint32_t raw, bool mine, int confirm, int back, const bool* keys) {
    if (!available() && !visible()) return false;
    const State state = channel().snapshot();
    static uint32_t held;
    const uint32_t pressed = raw & ~held;
    held = raw;
    const bool f5 = host && host->take_key_press ? mine && host->take_key_press(VK_F5) : key(VK_F5, mine);
    const bool enter = keys[7], esc = keys[5], up = keys[1], down = keys[2];
    const uint32_t modifier = state.shortcut == 1 ? 1u << HOS_PAD_TOUCHPAD : 1u << HOS_PAD_BACK;
    const bool chord = mine && state.shortcut && (raw & modifier);
    if (f5) { open = !open.load(); confirm_action = 0; }
    if (chord && (pressed & (1u << HOS_PAD_UP))) { show(); selected = 0; activate(state); }
    if (chord && (pressed & (1u << HOS_PAD_RIGHT))) show();
    if (chord && (pressed & (1u << HOS_PAD_DOWN))) {
        show(); selected = 2; if (!state.entries.empty()) activate(state);
    }
    // A configured modifier belongs to player tools. Do not also toggle the
    // ordinary menu on touchpad-down before the D-pad part of the chord arrives.
    if (!visible()) return f5 || chord;
    if (!mine) return true;
    bool choose = enter || (pressed & (1u << confirm));
    bool cancel = esc || (pressed & (1u << back));
    if (!confirm_action) {
        const int rows = 2 + (int)state.entries.size();
        if (up || (!chord && (pressed & (1u << HOS_PAD_UP)))) selected = (selected + rows - 1) % rows;
        if (down || (!chord && (pressed & (1u << HOS_PAD_DOWN)))) selected = (selected + 1) % rows;
        selected = std::clamp(selected, 0, rows - 1);
    }
    MkwVkPointer pointer{};
    if (host && host->pointer && host->pointer(&pointer)) {
        cancel |= (pointer.pressed & HOS_MOUSE_RIGHT) != 0;
        if (pointer.pressed & HOS_MOUSE_LEFT) {
            for (const auto& hit : hits)
                if (pointer.x >= hit.x0 && pointer.x < hit.x1 && pointer.y >= hit.y0 && pointer.y < hit.y1) {
                    if (confirm_action) { if (hit.row == -1) choose = true; else cancel = true; }
                    else selected = hit.row, choose = true;
                }
        }
    }
    if (cancel) { if (confirm_action) confirm_action = 0; else open = false; return true; }
    if (choose) {
        if (confirm_action && state.fresh) {
            channel().send(confirm_action == 1 ? "capture" : "restore " + restore_id);
            confirm_action = 0;
        } else activate(state);
    }
    return true;
}
void draw(ui::Ctx& c) {
    if (!visible()) return;
    const State state = channel().snapshot();
    const float s = c.h / 720.f, x = std::max(12.f*s, (c.w - 820*s)/2), w = std::min(c.w-24*s,820*s);
    const float y = 44*s;
    c.d->AddRectFilled({x,y},{x+w,c.h-40*s},ui::kBox,8*s);
    ui::text(c,c.f.heading,30*s,{x+28*s,y+22*s},ui::kInkBright,"Longshot checkpoints");
    ui::text(c,c.f.body,15*s,{x+28*s,y+68*s},ui::kSoft,
             "Native saved progress. Save in-game before capturing; recovery restarts the game.",w-56*s);
    hits.clear();
    if (confirm_action) {
        const std::string title = confirm_action == 1 ? "Capture the latest saved checkpoint and restart?" : "Load " + restore_name + " into a new profile?";
        ui::text(c,c.f.strong,22*s,{x+28*s,y+140*s},ui::kInkBright,title.c_str(),w-56*s);
        ui::text(c,c.f.body,18*s,{x+28*s,y+220*s},ui::kSoft,
                 "Unsaved progress will be lost. Your existing save files and profiles are kept. This is not an instant memory state.",w-56*s);
        for (int i=0;i<2;i++) {
            const float left=x+28*s+i*220*s, top=y+330*s;
            c.d->AddRectFilled({left,top},{left+200*s,top+48*s},i?ui::kCellName:ui::kGold,4*s);
            ui::text(c,c.f.strong,18*s,{left+16*s,top+12*s},i?ui::kInk:ui::kGoldInk,i?"Cancel / back":"Continue / confirm");
            hits.push_back({left,top,left+200*s,top+48*s,i?-2:-1});
        }
    } else {
        std::vector<std::string> rows={"Capture latest native save...",std::string("PS5 shortcuts: ")+
            (state.shortcut==1?"Touchpad + D-pad":state.shortcut==2?"Create + D-pad":"Off (F5 opens browser)")};
        for (const auto& entry:state.entries) rows.push_back("Load: "+entry.name);
        selected=std::clamp(selected,0,(int)rows.size()-1);
        if(selected<first) first=selected;
        if(selected>=first+7) first=selected-6;
        for(int i=first;i<(int)rows.size()&&i<first+7;i++) {
            const float top=y+120*s+(i-first)*49*s;
            c.d->AddRectFilled({x+20*s,top},{x+w-20*s,top+43*s},i==selected?ui::kCellNameSel:ui::kCellDark,3*s);
            ui::text(c,c.f.body,18*s,{x+32*s,top+10*s},i==selected?ui::kGoldHi:ui::kInk,rows[i].c_str(),w-64*s);
            hits.push_back({x+20*s,top,x+w-20*s,top+43*s,i});
        }
    }
    ui::text(c,c.f.body,14*s,{x+28*s,c.h-172*s},ui::kSoft,state.message.c_str(),w-56*s);
    ui::text(c,c.f.body,14*s,{x+28*s,c.h-112*s},ui::kInk,
             "Shortcuts: Up = capture, Down = latest checkpoint, Right = browser.\nArrows / D-pad: browse    Enter / confirm: choose    Esc / back: close",w-56*s);
}
}
