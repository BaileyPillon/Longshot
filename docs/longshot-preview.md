# Longshot Windows preview

1. Download `HookshotBuilder.exe` from the [Longshot prerelease](https://github.com/BaileyPillon/Longshot/releases).
   Its window is named **Longshot Builder**. The asset filename is used by the update protocol.
2. Select your own supported Ocarina of Time remake dump
   (program `0400486024DEC000`, update `v131072`, build `e0f3ccfa`).
   Select the `.nup` or both extracted game folders. The builder performs the conversion locally.
3. Use the proposed Longshot game folder or choose an empty folder. Allow about 60 GB of free space while building.
   On Windows, you'll need a current Vulkan driver with mesh shader support and 16 GB of RAM or more.
4. Click **Play**, or choose **Player tools** for save profiles, checkpoints, the Adventure Journal and the mod manager.
   To bring in existing progress, close the game, then import a copied save folder or save ZIP into a new profile.
   Keep the source save as your backup.

Initial shader preparation can take time. Start with frame generation and HDR off.
Linux builds, multiplayer and multiworld are outside the Windows preview. Optional companion setup remains in the source guide.

Report problems in [Longshot Issues](https://github.com/BaileyPillon/Longshot/issues) with the exact preview tag,
Windows version, GPU and the steps to reproduce. Keep game dumps, generated game files and saves private.
