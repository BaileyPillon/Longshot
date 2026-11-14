#pragma once
#include <cstdint>
namespace mkwvk::ui { struct Ctx; }
namespace mkwvk::longshot {
bool available();
bool visible();
void show();
bool tick(uint32_t raw, bool foreground, int confirm, int back, const bool* keys);
void draw(ui::Ctx& c);
}
