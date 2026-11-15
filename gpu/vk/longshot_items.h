/* Longshot quick-select catalog. Enum names identify the game's existing item
   assignments; these controls never grant inventory or equip the other age. */
#pragma once
/* Existing option channel, no renderer ABI or shader-cache stamp change. */
enum { HOS_OPT_ITEM_WHEEL = 60, HOS_OPT_QUICK_ACTION, HOS_OPT_QUICK_OWNED,
       HOS_OPT_QUICK_RESULT, HOS_OPT_QUICK_LEFT, HOS_OPT_QUICK_RIGHT };
enum { HOS_OPT_EQUIPPED_HUD = 70, HOS_OPT_QUICK_EQUIPPED };
#define LONGSHOT_EQUIP_CHILD 0xa0029837u
#define LONGSHOT_EQUIP_ADULT 0xbc32ce24u
#define LONGSHOT_QUICK_CHORD_PARTS ((1u << HOS_PAD_RSTICK) | (1u << HOS_PAD_LSHOULDER) | \
    (1u << HOS_PAD_UP) | (1u << HOS_PAD_RIGHT) | (1u << HOS_PAD_DOWN) | (1u << HOS_PAD_LEFT))
#define LONGSHOT_ITEMS(X) \
 X("Slingshot", "SlingShot", "Weapon_Range_SlingShot", 1, 0) \
 X("Deku stick", "DekuStick", "Item_DekuStick", 1, 0) \
 X("Deku nut", "DekuNut", "Item_DekuNut", 3, 0) \
 X("Boomerang", "Boomerang", "Item_Boomerang", 1, 0) \
 X("Bomb", "Bomb", "Item_Bomb", 3, 0) \
 X("Bombchu", "Bombchu", "Item_Bombchu", 3, 0) \
 X("Magic bean", "MagicBean", "Item_MagicBean", 1, 0) \
 X("Lens of Truth", "GlassTruth", "Item_GlassTruth", 3, 0) \
 X("Bow", "Bow", "Weapon_Range_Bow", 2, 0) \
 X("Hookshot", "Hookshot", "Item_Hookshot", 2, 0) \
 X("Longshot", "Longshot", "Item_Longshot", 2, 0) \
 X("Hammer", "Hammer", "Item_Hammer", 2, 0) \
 X("Iron boots", "HeavyBoot", "Armor_Adult_HeavyBoot", 2, 0) \
 X("Hover boots", "HoverBoot", "Armor_Adult_HoverBoot", 2, 0) \
 X("Din's Fire", "DinFire", "Item_DinFire", 3, 0) \
 X("Farore's Wind", "FaroreWind", "Item_FaroreWind", 3, 0) \
 X("Nayru's Love", "NayruLove", "Item_NayruLove", 3, 0) \
 X("Bottle A", "BottleA", "", 3, 0xf39ce410u) \
 X("Bottle B", "BottleB", "", 3, 0x000ff6eau) \
 X("Bottle C", "BottleC", "", 3, 0xf63b1194u) \
 X("Bottle D", "BottleD", "", 3, 0xb7f052ceu) \
 X("Bottle E", "BottleE", "", 3, 0xe27b136du) \
 X("Fire arrow", "FireArrow", "Item_Arrow_Fire", 2, 0) \
 X("Ice arrow", "IceArrow", "Item_Arrow_Ice", 2, 0) \
 X("Light arrow", "LightArrow", "Item_Arrow_Light", 2, 0) \
 X("Keaton mask", "KeatonMask", "Armor_Child_Mask_Keaton", 1, 0) \
 X("Skull mask", "SkullMask", "Armor_Child_Mask_Skull", 1, 0) \
 X("Spooky mask", "SpookyMask", "Armor_Child_Mask_Spooky", 1, 0) \
 X("Bunny hood", "BunnyMask", "Armor_Child_Mask_Bunny", 1, 0) \
 X("Goron mask", "GoronMask", "Armor_Child_Mask_Goron", 1, 0) \
 X("Zora mask", "ZoraMask", "Armor_Child_Mask_Zora", 1, 0) \
 X("Mask of Truth", "TruthMask", "Armor_Child_Mask_Truth", 1, 0)
#define LONGSHOT_ITEM_COUNT 32
