# Compatibility

| Profile | Upstream commit | Backend version | Desktop |
|---|---|---|---|
| `desktop-26.924.2738.0-sqlite-v2` | `0d9c7cbfa6cf1489f55a8a9542b75ddd2c061807` | `0.158.0-alpha.2.1` | `26.924.2738.0` (72 migrations) |
| `desktop-26.924.2738.0` | `0d9c7cbfa6cf1489f55a8a9542b75ddd2c061807` | `0.158.0-alpha.2.1` | `26.924.2738.0` |
| `0.158.0-alpha.2` | `10382da79a2a2d6e8ae221fa63077215389c1ad2` | `0.158.0-alpha.2` | `26.924.1866.0` |
| Legacy apply entry point | `b5bffd3ec4db487e7e3dec59663875b0ef7b72ca` | Commit-bound | Original patch |

`build_backend.py` retains `0.158.0-alpha.2` as its default; select the new profile explicitly. `apply.ps1` and `apply.sh` without a profile retain their original legacy behavior. Desktop integration supplies the exact matching profile automatically when compatibility mode is selected.

The two current desktop profiles share compatibility semantics and 57 migration byte identities. Their upstream commits, version strings and official backend identities are distinct. Remote compaction V1 is absent from both current upstream versions and is not restored.
