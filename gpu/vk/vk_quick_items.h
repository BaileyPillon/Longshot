#pragma once
#include <cstdint>
#include "longshot_items.h"
namespace mkwvk::ui { struct Ctx; }
namespace mkwvk::quick {
bool visible();
bool tick(uint32_t raw, bool foreground, int confirm, int back, const bool* keys);
void draw(ui::Ctx&);
void update(int id, int value);
int take_action();
const char* item_name(int value);
}
