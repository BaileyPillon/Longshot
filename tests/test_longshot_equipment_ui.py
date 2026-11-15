"""Exercise the real item wheel's selection and history with stubbed renderer input."""
import argparse
from pathlib import Path
import subprocess
import tempfile

RUN_ALL_ARGS = ["--cxx", "{cxx}"]
ROOT = Path(__file__).resolve().parents[1]

STUBS = r"""
#include <cstdint>
#include <cstdio>
#include "gpu/vk/vk_api.h"
#include "gpu/vk/longshot_items.h"
struct Vec { float x,y; };
struct Draw {
    void AddRectFilled(Vec,Vec,int,float) {}
    void AddRect(Vec,Vec,int,float,int,float) {}
};
namespace mkwvk {
struct { int item_wheel=1, equipped_hud=1, quick_up, quick_right, quick_down, quick_left; } opts;
const MkwVkHost* host=nullptr;
constexpr int VK_F4=0x73, VK_F7=0x76, VK_SHIFT=16;
int GetAsyncKeyState(int) { return 0; }
void menu_save() {}
namespace ui {
enum { kBox,kInkBright,kSoft,kCellNameSel,kCellDark,kGold,kGoldHi,kInk };
struct Ctx { float w=1280,h=720; Draw* d; struct { int body,heading,strong; } f; };
void text(Ctx&,int,float,Vec,int,const char*,float=0) {}
}
}
"""

CASES = r"""
#include <cassert>
int main() {
    using namespace mkwvk::quick;
    bool keys[8]{};
    update(HOS_OPT_QUICK_OWNED, (1u<<0) | (1u<<2) | (1u<<17));
    update(HOS_OPT_QUICK_EQUIPPED, 1);
    assert(hud_visible());
    assert(tick(0,false,0,1,keys,true,false) && visible() && !hud_visible());
    keys[4]=true;
    tick(0,false,0,1,keys,false,false);
    keys[4]=false;
    keys[7]=true;
    tick(0,false,0,1,keys,false,false);
    assert(!visible() && take_action()==3);
    keys[7]=false;
    update(HOS_OPT_QUICK_EQUIPPED,3);
    tick(0,false,0,1,keys,false,true);
    assert(take_action()==1);
    update(HOS_OPT_QUICK_EQUIPPED,-9);
    tick(0,false,0,1,keys,false,true);
    assert(!take_action());
    update(HOS_OPT_QUICK_OWNED,0);
    tick(0,false,0,1,keys,true,false);
    keys[7]=true;
    tick(0,false,0,1,keys,false,false);
    assert(visible() && !take_action());
    keys[5]=true;
    tick(0,false,0,1,keys,false,false);
    assert(!visible());
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cxx", default="clang++")
    args = parser.parse_args()
    wheel = (ROOT / "gpu/vk/vk_quick_items.cpp").read_text(encoding="utf-8")
    wheel = "\n".join(line for line in wheel.splitlines() if not line.startswith('#include "'))
    with tempfile.TemporaryDirectory(prefix="longshot-equipment-") as temporary:
        source = Path(temporary) / "equipment.cpp"
        binary = Path(temporary) / "equipment.exe"
        source.write_text(STUBS + wheel + CASES, encoding="utf-8")
        subprocess.run([args.cxx, "-std=c++20", "-Wall", "-Wextra", "-Werror",
                        "-I", str(ROOT), str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print("PASS: equipment wheel skips unowned items, selects, recalls, and clears on age change")


if __name__ == "__main__":
    main()
