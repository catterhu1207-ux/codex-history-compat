# v0.2.8

Adds the independent `desktop-26.1016.8622.0-sqlite-v2` configuration for `codex-cli 0.163.0-alpha.11.2.1` and all 77 official migration identities. Previous profiles retain their source and build identities.

The Windows build passed 35 packaging/profile tests, 15 compatibility-module tests with real upstream types and all seven backend replay groups. The same replay groups passed against the official backend. The complete CLI is built from immutable public-source revision `ad057a0ade9a99eb84161a23c8462ac0f68e8f1a` with Rust 1.99.1 and locked dependencies.

Assets contain source and checksums. The desktop installer continues to use the official backend by default; the compatibility backend is compiled locally only when selected.
