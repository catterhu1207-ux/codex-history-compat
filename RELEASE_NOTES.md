# v0.2.7

Adds the independent `desktop-26.1016.8120.0-sqlite-v2` configuration for `codex-cli 0.163.0-alpha.11.1.1`, with unchanged compatibility semantics and all 77 official migration checksums. Previous profiles remain available.

The Windows source build passed 15 module tests, HTTP and real WebSocket replay, cold task-setting restoration, local and remote V2 compaction, database startup and 105-turn pagination. Tests used synthetic data and local services. Public build inputs are pinned to `8bdfd1e3a92be0cb24ff415ecc45e247ca24e6ac`.

Assets contain source and checksums. Build the optional backend locally; the desktop installer continues to use the official backend by default.
