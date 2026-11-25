# History compatibility source for Desktop 26.1120.6357.0

The Desktop 26.1120.5083.0 source profile pins the Codex 0.171.0-alpha.13.2 upstream revision, Rust 1.99.1, and 81 SQLite migrations. It includes the history compatibility patch and its synthetic fixtures.

The signed 5083 and 6357 desktop backends match after removal of Authenticode certificate metadata and the PE checksum. Their SQLite migration definitions also match. Use the exact desktop version when checking the signed backend input for a build.

This checkpoint provides source and build inputs. Installer release status is tracked on the desktop workflow repository's Releases page.
