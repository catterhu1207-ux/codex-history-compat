# Desktop 26.928.4866.0 acceptance

An independent Windows build from compatibility commit `f14ab65de66b4e107f962ced5022be07c8a36cc1` passed all six runtime checks:

| Check | Result |
|---|---|
| Profile and migration regression | 17 tests passed |
| HTTP and WebSocket | Both passed; tool calls and outputs remained paired and four notices were folded into their outputs |
| Cold restoration | Saved model settings and existing history retained |
| Local and remote compaction | Both passed against an isolated service |
| Database compatibility | 73 migration checksums across six databases verified; existing migration records unchanged |
| Process cleanup | Test process groups exited without retained descendants |

The recipe used Rust 1.95.0, locked dependencies, x64 MSVC and the pinned upstream `0.159.2` source. It built only the consumed binary. The first build left a signed MSVC helper inside its managed process group; the supervisor stopped it. Cached build revalidation and all subsequent runtime groups completed with no remaining owned processes.

The replay tools are maintained in `codex-desktop-workflow/tools/backend`, with their origin and adjustments recorded in `SOURCE.json`. All data were synthetic. No official or modified executable is distributed by this repository.

# v0.2.2 acceptance

The sqlite-v2 public source profile was built with the pinned upstream revision, Rust 1.95.0 and unchanged external dependencies.

| Check | Result |
|---|---|
| Packaging, rejection and cached-migration regression | 16 passed |
| Rust compatibility module | 15 passed |
| Ordinary HTTP and real WebSocket | Passed; four image tool calls and outputs remained paired |
| Local compaction and remote compaction V2 | Passed against the loopback service |
| Cold task restoration | Saved model and reasoning effort retained after default changes |
| SQLite compatibility | 72 source and compiled checksums matched across six databases; native app-server startup and normal exit passed; migration records unchanged |

All tasks, images and databases were synthetic. The source recipe revalidated the cached binary and its official migration identities. `ACCEPTANCE.json` binds these checks to the public source inputs and identifies this local build.

[v0.2.1 acceptance](acceptance/v0.2.1.md) is retained as historical evidence. That release checked 57 state migrations; this release also covers the 15 auxiliary migrations.
