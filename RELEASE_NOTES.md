# v0.2.4

Adds the independent `desktop-26.1013.4894.0-sqlite-v2` profile for `codex-cli 0.163.0-alpha.10.2`. It preserves all 77 official database migration checksums and existing profiles.

An independently built Windows backend passed compatibility module tests, HTTP and real WebSocket replay, local and remote V2 compaction, task-setting restoration, and 105-turn paginated history checks. All model-service tests used local synthetic fixtures.

Build inputs are pinned to `1ce7f5f12e912596195f70dede49c3a50c452fbc`; documentation and acceptance records follow that revision. The optional existing-toolchain and separate-release-cache arguments make Windows builds reproducible without installing tools. Assets contain source and checksums. The desktop installer is released separately after its own runtime checks.
