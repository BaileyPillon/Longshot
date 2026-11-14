#pragma once
#include <cstdint>
#include "longshot_items.h"
namespace mkwvk::ui { struct Ctx; }
namespace mkwvk::quick {
bool visible();
bool tick(uint32_t raw, bool foreground, int confirm, int back, const bool* keys,
          bool scripted_open = false, bool scripted_previous = false);
void draw(ui::Ctx&);
bool hud_visible();
void draw_hud(ui::Ctx&);
void update(int id, int value);
int take_action();
const char* item_name(int value);
}
