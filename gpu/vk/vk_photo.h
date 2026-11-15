#pragma once
#include <cstdint>
#include "longshot_photo_options.h"
namespace mkwvk::ui { struct Ctx; }
namespace mkwvk::photo {
bool active();
bool tick(uint32_t raw, bool foreground, int back, const bool* keys);
void draw(ui::Ctx&);
void ready(bool value);
void activity();
int hud();
int fov();
}
