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
