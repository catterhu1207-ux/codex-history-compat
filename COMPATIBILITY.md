# Compatibility

| Profile | Upstream commit | Backend version | Desktop |
|---|---|---|---|
| `desktop-26.1016.6573.0-sqlite-v2` | `5425d3e625daa58eea3ad1de27c087eb3b2ffbd3` | `0.163.0-alpha.11.1` | `26.1016.6573.0` (77 migrations) |
| `desktop-26.1007.9446.0-sqlite-v2` | `740e5af33c71225640e0c1c1555c514c2c93ab74` | `0.162.0-alpha.17.2` | `26.1007.9446.0` (75 migrations) |
| `desktop-26.928.4866.0-sqlite-v2` | `ff6aec96948b70d94983af2641a6b67c94faeff5` | `0.159.2` | `26.928.4866.0` (73 migrations) |
| `desktop-26.924.2738.0-sqlite-v2` | `0d9c7cbfa6cf1489f55a8a9542b75ddd2c061807` | `0.158.0-alpha.2.1` | `26.924.2738.0` (72 migrations) |
| `desktop-26.924.2738.0` | `0d9c7cbfa6cf1489f55a8a9542b75ddd2c061807` | `0.158.0-alpha.2.1` | `26.924.2738.0` |
| `0.158.0-alpha.2` | `10382da79a2a2d6e8ae221fa63077215389c1ad2` | `0.158.0-alpha.2` | `26.924.1866.0` |
| Legacy apply entry point | `b5bffd3ec4db487e7e3dec59663875b0ef7b72ca` | Commit-bound | Original patch |

`build_backend.py` retains `0.158.0-alpha.2` as its default; select the new profile explicitly. `apply.ps1` and `apply.sh` without a profile retain their original legacy behavior. Desktop integration supplies the exact matching profile automatically when compatibility mode is selected.

The two earlier desktop profiles share compatibility semantics and 57 migration byte identities. Their upstream commits, version strings and official backend identities are distinct. Remote compaction V1 is absent from both current upstream versions and is not restored.

## Development profiles for 26.1013

Source profiles `desktop-26.1013.3656.0-sqlite-v2` and `desktop-26.1013.4894.0-sqlite-v2` pin upstream `4ebc485ca321243727539187169425fcf972f2c4`, Rust 1.95.0 and compatibility version `0.163.0-alpha.10.2`. Each binds its own official backend identity and all 77 migrations across six database families. The 4894 profile retains the predecessor's patch semantics and migration bytes with a separate source identity.

The 4894 source profile was qualified in v0.2.4. Desktop installation remains a separate acceptance scope; the 3656 profile retains its development status. Existing profile identities, default selection and legacy apply entry points are preserved.

The synthetic multi-page replay accepts an explicitly supplied backend and checks cold history restoration against a loopback service. It creates only synthetic task data and makes no paid model requests.

## Desktop 26.1013.4894.0

Profile: `desktop-26.1013.4894.0-sqlite-v2`; upstream `4ebc485ca321243727539187169425fcf972f2c4`; compatibility source `1ce7f5f12e912596195f70dede49c3a50c452fbc`; Rust 1.95.0; 77 unchanged migrations. Existing profiles remain available.
