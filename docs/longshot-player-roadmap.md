# Features players will notice

Updated 14 November 2026. This is the **new-feature queue** for BaileyPillon/Longshot, separate from the
[engineering acceptance backlog](longshot-roadmap.md). It uses the [49-repository review](longshot-fork-research.md),
reopened community discussions and the user's requests. The order weighs visible impact, evidence of demand,
fit with the existing fork and implementation risk. It is an editorial ranking, not a Reddit vote count.

## Initial ranking and rationale

The table below records the original candidate assessment. Current implementation and validation status appears in the follow-up.

| Rank | Feature | What changes for the player | Demand evidence | Initial delivery boundary |
|---|---|---|---|---|
| 1 | **Quick item wheel and D-pad favorites** | Choose weapons, bottles and boots quickly; keep camera control while running. | Multiple participants request a wheel, more item bindings and easier boot switching in the [QoL thread](https://www.reddit.com/r/zelda/comments/1xs0xds/oothd_possible_qol_features_to_patch_in/), alongside the [control discussion](https://www.reddit.com/r/OcarinaOfTime/comments/1xp7ph6/i_wish_they_hadnt_botwified_the_controls/). Strongest direct control requests in this sample; preferences differ. | New wheel and item-action backend remain to implement. Existing per-button hold toggles are already integrated and are not counted as a new wheel. Test consumable use, aiming, menus and controller conflicts. |
| 2 | **Live Adventure Journal** | See the current area, live collection counters and pickup changes; mark places to revisit and follow a movement trail on a second screen. | [Boomerang](https://www.reddit.com/r/OcarinaOfTime/comments/1xtthaw/boomerang_tracker_a_save_progress_tracker_for_the/) and [Atlas](https://www.reddit.com/r/EmulationPiracy/comments/1xvpf5d/ocarina_atlas_live_companion_map_secondscreen/) independently implement completion assistance. This is convergent author interest with small discussions, not broad consensus. | First implementation: original local companion, per-profile waypoints, distance/direction, session trail and sampled counters. No copied Atlas base/art; no guess that a token count identifies a particular collectible. Illustrated maps and full live item identification remain separate work. |
| 3 | **Pause-menu checkpoints and PS5 shortcuts** | Browse named saved moments from the game and recover without manually moving folders. | Repeated explicit request from this fork's user; Sunshine-inspired save design. [Save-transfer discussion](https://www.reddit.com/r/SwitchPirates2/comments/1xtaz11/transfer_saves_between_hookshot_and_fritchii_or/) supports preservation/migration, not proof of community demand for instant states. | Existing launcher archives are native saved-game snapshots. First deliver an honest in-game browser with a safe reload boundary; genuine instant state restoration needs GPU/audio/actor reconstruction and remains a distinct milestone. |
| 4 | **Co-op party setup and customization** | Host/join with clear status, choose tunic colors and player names, and reconnect without confusing save profiles. | The [co-op announcement](https://www.reddit.com/r/decomps/comments/1xuw3wk/ocarina_of_time_recomp_multiplayer/) draws installation, alternate-character and couch-play requests. | Native module/join form already exist. Add visible hosting/customization around them, then verify two clients. Split-screen and playable NPCs are requests, not present capabilities. No automatic router changes. |
| 5 | **Smart HUD and proper photo controls** | Contextual health/item information during combat, a clean view while exploring, and accessible camera/screenshot controls. | Several [QoL participants](https://www.reddit.com/r/zelda/comments/1xs0xds/oothd_possible_qol_features_to_patch_in/) request Pro HUD improvements and clearer equipped items. Photo workflow is our extension of that idea; it is not claimed as repeated demand in this sample. | Debug free camera already exists. A photo feature must add deliberate controls, HUD behavior, safe resume and screenshot management; simply exposing the debug toggle is insufficient. |
| 6 | **Randomizer playthrough presets and multiworld** | Start a curated shuffled adventure, see seed identity and logic, and exchange progression with friends. | [OoTrR announcement](https://www.reddit.com/r/OcarinaOfTime/comments/1xu81uk/ocarina_of_time_remake_randomizer/) and [cross-post](https://www.reddit.com/r/SwitchPirates2/comments/1xu892p/randomizer_for_the_remake/); noteworthy but small discussion. | Logic randomizer/Archipelago companion already integrated separately. New preset UX and seed sharing must retain isolated mods/saves; full progression and item delivery need gameplay acceptance. |
| 7 | **Switchable mod loadouts** | Keep separate vanilla, visual, challenge and co-op setups with conflict previews and rollback. | Sunshine's integrated-mod workflow supplied by the user; Mako and launcher comparisons in the repository survey. Useful synthesis, not a measured Reddit consensus. | Mod ordering/conflict inspection already exists. Named loadouts and compatibility checks are new work; never auto-download arbitrary packs or overwrite a running mode. |

## 14 November follow-up

This follows the earlier 49-repository review with current release tags, recent repository activity, GitHub stars,
local bookmarks and Reddit discussions. The signed-in account had no relevant starred repositories. Six Chromium
bookmark files and one Firefox database yielded no matching bookmarks. The original Hookshot GitHub URL returned
404. The [MagicBeanDev continuation](https://git.magicbean.dev/MagicBeanDev/Longshot) is a separate project from this
GitHub fork. Reddit reports disagree on which port runs best across hardware. This queue weighs player requests,
visibility and the ability to verify the feature here.

| Rank | Next improvement | Status and evidence |
|---:|---|---|
| 1 | **Item wheel, favorites and contextual HUD** | Code in the working branch. The native item fixture passed. Verify equip, cancellation and controller chords in gameplay. [Reddit requests](https://www.reddit.com/r/zelda/comments/1xs0xds/oothd_possible_qol_features_to_patch_in/) |
| 2 | **Faster starts and fewer traversal hitches** | Compare shader reuse after menu updates and time the same route before and after. Mako 4.1 and NX2navi 0.10.2-rc4 report gains on their own renderers. MagicBean's cache change `26a2eab0` is a separate candidate. [Mako 4.1](https://github.com/Shakoquo/Mako/releases/tag/mako-4.1) · [NX2navi preview](https://github.com/tangerineturtle1/NX2navi/releases/tag/v0.10.2-rc4) |
| 3 | **Portable saves and pause checkpoints** | Implemented save ZIP export and import into a new profile. Validate capture, restart and load through the in-game browser. [NX2navi ZIP format](https://github.com/tangerineturtle1/NX2navi/blob/v0.10.2-rc4/launcher/saves.py) · [Reddit save transfer](https://www.reddit.com/r/SwitchPirates2/comments/1xtaz11/transfer_saves_between_hookshot_and_fritchii_or/) |
| 4 | **Randomizer recipes and replay** | Updated to OoTrR 0.5.2 for Mido's progression wall, unsafe ocarina placements, Lost Dog logic and tracker fixes. Recipe identity follows the pinned generator. [OoTrR 0.5.2](https://github.com/Mozencaz/OotrR/releases/tag/v0.5.2) · [Reddit release discussion](https://www.reddit.com/r/shipofharkinian/comments/1xvr2fc/ootrr_a_randomizer_for_the_ocarina_of_time_remake/) |
| 5 | **Local mod import and switchable loadouts** | Added RomFS folder installation. New layers start disabled and appear in the existing conflict and load order view. [Mako 4.1](https://github.com/Shakoquo/Mako/releases/tag/mako-4.1) · [NX2navi launcher](https://github.com/tangerineturtle1/NX2navi/blob/main/docs/launcher.md) |
| 6 | **Multiplayer from the game menu** | Co-op 0.10.1 introduced game-menu Host/Join and moved to protocol 11, incompatible with test10. It runs on the MagicBean continuation. Plan a compatible migration and test two clients before changing this fork's pin. [Co-op release](https://github.com/daurosk/oot-remake-multiplayer/releases/tag/v0.10.1) · [Reddit playtest](https://www.reddit.com/r/decomps/comments/1xuw3wk/ocarina_of_time_recomp_multiplayer/) |
| 7 | **Visual accuracy and customization** | Reproduce Lichii's water-shadow and distant-forest cases in Longshot. ReLink reports an RTX 50 water workaround. Check HDR and frame generation against this PC's prior blur and flicker. [Lichii build 177](https://github.com/zortos293/Lichii/releases/tag/build-177) · [ReLink v0.6.9](https://github.com/pixl27/ProjectReLink/releases/tag/v0.6.9) |

Fritchii 5.8.4 is a reference for shader preparation progress and save management. ReTuned 0.7.1 is a reference
for controller menus from the 3DS lineage. Miojo's ray tracing experiments come after this fork's frame pacing and
scene accuracy work. [Fritchii releases](https://github.com/ZuanCrisp/Fritchii/releases) · [ReTuned](https://github.com/OTPR26/Ocarina-ReTuned/releases/tag/v0.7.1) · [Miojo](https://github.com/sostenesfreitas/miojo-recomp)

Rekarina appeared in a developer discussion without publicly reviewable source. The verified Clawshot repository is
an item randomizer. A similarly named Reddit renderer announcement did not provide a verifiable source link.
[Rekarina discussion](https://www.reddit.com/r/SwitchPirates2/comments/1xvo2jw/a_little_story_about_my_own_recompilation_rekarina/) · [Clawshot source](https://github.com/hiKareeem/Clawshot)

## 14 November release refresh and implementation

The refresh checked the earlier 49-repository shortlist against new pushes, public stars, local bookmarks and player
threads. No relevant matches appeared in the checked personal stars or bookmarks. The ranking weighs player requests,
how noticeable the changes are in play and what can be verified on the current branch.

| Rank | Improvement | Current result |
|---:|---|---|
| 1 | Quick items, smart HUD and photo mode | Source for the wheel, favorites, contextual HUD and photo camera is on the branch. The item fixture passes. Equip, HUD transitions and camera controls still need gameplay acceptance. [Player QoL requests](https://www.reddit.com/r/zelda/comments/1xs0xds/oothd_possible_qol_features_to_patch_in/) |
| 2 | Continue straight to a save and recover a checkpoint | Added **Continue save**, **Skip title screen** and automatic continuation from the checkpoint service's restored profile. Both paths reached gameplay using a copied Deku Tree save. [MagicBean skip-title change](https://git.magicbean.dev/MagicBeanDev/Longshot/commit/ecb0f612) |
| 3 | Install mod ZIPs and switch setups | Added direct single-layer RomFS ZIP import. New layers start disabled and appear in the conflict and loadout view. [Mako 4.1](https://github.com/Shakoquo/Mako/releases/tag/mako-4.1) · [NX2navi launcher](https://github.com/tangerineturtle1/NX2navi/blob/main/docs/launcher.md) |
| 4 | Faster restarts and smoother travel | Removed the renderer API header from all four translator stamp producers. Menu-only edits now preserve cache identity. Older caches need one refresh. NX2navi's new preview also changes texture residency and fade transitions. Those policies need a same-route comparison on Longshot. [MagicBean cache change](https://git.magicbean.dev/MagicBeanDev/Longshot/commit/26a2eab0) · [NX2navi v0.11.0-rc4](https://github.com/tangerineturtle1/NX2navi/releases/tag/v0.11.0-rc4) |
| 5 | Featured randomizer challenges and shareable seeds | Added Kokiri Trial, Hyrule Relay and Lost Measure for the OoTrR 0.5.2 pin. Clawshot v0.2.1 provides examples of versioned settings and public seed recipes. [Clawshot v0.2.1](https://github.com/hiKareeem/Clawshot/releases/tag/v0.2.1) · [Clawshot discussion](https://www.reddit.com/r/OcarinaOfTime/comments/1xw8gey/clawshot_an_oot_remake_randomizer/) |
| 6 | Easier parties and in-game multiplayer | Added clipboard address handoff to the launcher. Passwords are entered separately. Co-op 0.10.1's in-game Host/Join, protocol 11 and save synchronization depend on a different native build. The existing integration remains pinned pending a compatible port and two-client testing. [Co-op v0.10.1](https://github.com/daurosk/oot-remake-multiplayer/releases/tag/v0.10.1) · [Player co-op discussion](https://www.reddit.com/r/decomps/comments/1xuw3wk/ocarina_of_time_recomp_multiplayer/) |
| 7 | Keyboard walking, water and foliage | Added the rebindable Walk modifier with Hold and Toggle modes and adjustable speed. Input fixtures preserve existing bindings and controller movement. Longshot contains shadow-table code and passes the descriptor-array fixture. Lichii's visual cases still need side-by-side scene captures. [Lichii build 177](https://github.com/zortos293/Lichii/releases/tag/build-177) · [MagicBean Walk key](https://git.magicbean.dev/MagicBeanDev/Longshot/commit/8c1844a9) |

The [validation record](longshot-validation.md) covers what ran. The player threads establish individual
requests and release reports. A community-wide preference could not be established from this sample.

## 14 November gameplay feature iteration

The second refresh checked recently pushed repositories, the account's stars, local bookmarks, upstream commits,
release notes, and independent remake player threads. The local bookmarks and account stars had no matching entries.
The searchable sample is described in the [fork research](longshot-fork-research.md).

| Rank | Feature | Status and evidence |
|---:|---|---|
| 1 | **Quick equipment with previous-item recall** | The wheel now pages only through owned items for the current age. F4 or L3 + L1 returns to the previously equipped item. The game retains its normal item-use button and restrictions. Direct multi-item activation needs a separate gameplay change. [Equip discussion](https://www.reddit.com/r/zelda/comments/1xqdww4/oothd_thoughts_about_the_new_item_equip_process/) · [C-button and wheel requests](https://www.reddit.com/r/zelda/comments/1xp1fhi/oothd_kokiri_why_for_the_love_godesses_why/) · [Ship of Harkinian](https://www.shipofharkinian.com/changelog) |
| 2 | **Minimal HUD that remembers your equipment** | The equipped-item overlay has its own option. It reads the remake's current equipment and can be combined with the contextual status HUD. [Remake QoL requests](https://www.reddit.com/r/zelda/comments/1xs0xds/oothd_possible_qol_features_to_patch_in/) · [HUD and sprint requests](https://www.reddit.com/r/OcarinaOfTime/comments/1xr0vll/i_only_have_two_big_complaints_about_the_remake/) |
| 3 | **Practice routes and personal bests** | The Adventure Journal now auto-splits three child routes on area arrival and saves completed times per profile. This is original work informed by practice-menu and autosplitter workflows. A boss-rush editor and safe-position visualization would require further game integration. [Sloperina 0.0.5](https://github.com/PracticeROM/sloperina/releases/tag/v0.0.5) · [LiveSplit](https://github.com/LiveSplit/LiveSplit) |
| 4 | **Sprint while aiming the camera** | Players repeatedly ask for a hands-free sprint. Existing binding and hold-toggle controls cover a manually configured button, but automatic sprint still needs the game's own sprint/action state so it cannot interact with nearby objects or advance dialogue. [Remap discussion](https://www.reddit.com/r/zelda/comments/1xqtr1k/oothd_sprinting_while_moving_the_camera/) |
| 5 | **Co-op story progression and smoother traversal** | Ported the replay-core affinity fallback fix for restricted CPU sets. Co-op v0.10.1 remains an ABI migration. NX2navi's preview and MagicBean's CPU-target option remain controlled comparison candidates. Frame generation stays off for this PC's prior flicker. [Co-op release](https://github.com/daurosk/oot-remake-multiplayer/releases/tag/v0.10.1) · [NX2navi preview](https://github.com/tangerineturtle1/NX2navi/releases/tag/v0.11.0-rc4) · [MagicBean CPU target](https://git.magicbean.dev/MagicBeanDev/Longshot/commit/7ff5256e) |

## Atlas boundary discovered during implementation

The reviewed [Atlas README](https://github.com/antonioalvromero/Ocarina-Atlas#license) explicitly licenses its newly
authored components, but says the inherited `oot-remake-map` base lacks a license and its art belongs to other owners.
The prior catalog's short MIT label was insufficient for bundling the complete application. No Atlas code, map art,
item dataset or analytics was imported for the original journal. A complete illustrated atlas needs a separately
reviewed source of code and assets, or extraction from the user's own local game.

## Preserved choices

Keep the regular Hookshot installation and active experimental profile progress intact. New notes live outside native
saves. Frame generation and HDR stay off after this PC's confirmed flicker. Preserve PS5 prompts, bindings, 15% deadzone,
2× text and the small top-right FPS counter. Keep Blender and other active work running; report functional verification
separately from a clean 60 FPS benchmark. The fork retains its current name until the user chooses a replacement.
