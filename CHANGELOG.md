# Changelog

## v0.2.7

Adds the independent `desktop-26.1016.8120.0-sqlite-v2` configuration for `codex-cli 0.163.0-alpha.11.1.1`, with unchanged compatibility semantics and all 77 official migration checksums. Previous profiles remain available.

The Windows source build passed 15 module tests, HTTP and real WebSocket replay, cold task-setting restoration, local and remote V2 compaction, database startup and 105-turn pagination. Tests used synthetic data and local services. Public build inputs are pinned to `8bdfd1e3a92be0cb24ff415ecc45e247ca24e6ac`.

Assets contain source and checksums. Build the optional backend locally; the desktop installer continues to use the official backend by default.


## v0.2.5

Adds the independent `desktop-26.1016.6573.0-sqlite-v2` configuration for `codex-cli 0.163.0-alpha.11.1`, with unchanged compatibility semantics and all 77 official migration checksums. Previous profiles remain available.

The Windows source build passed 15 module tests, HTTP and real WebSocket replay, cold task-setting restoration, local and remote V2 compaction, database startup and 105-turn pagination. Tests used synthetic data and local services. Public build inputs are pinned to `7cf7c00b0b7ce435e2264c04f5b88e0068e41ae2`.

Assets contain source and checksums. Build the optional backend locally; the desktop installer continues to use the official backend by default.


## v0.2.2 - 2026-09-27

- Add the independent sqlite-v2 profile covering all 72 migrations across six databases.
- Verify the complete official migration inventory before changing source bytes.
- Recompile stale SQLx migration caches and honor explicit source paths during verified reuse.
- Retain upstream, dependency, legacy profile and apply-interface identities.

## v0.2.1 - 2026-09-27

- Add the independent `desktop-26.924.2738.0` profile for upstream `0.158.0-alpha.2.1`.
- Bind the changed official backend through the matching upstream release and executable identity, retaining compatibility semantics and all 57 migration checksums.
- Retain existing profiles, apply interfaces, source-build defaults and dependency pins.

## v0.2.0 - 2026-09-26

- Add the `0.158.0-alpha.2` profile, Windows source build, migration checks and explicit desktop integration.

## v0.1.0

- Publish the original commit-bound history compatibility patch and synthetic fixture.

## 0.2.4

- Add Desktop 26.1013.4894.0 profile and paginated-history validation.
- Support an existing pinned Rust toolchain and separate release cache.
- Isolate the version probe in replay tests from the normal user profile.
