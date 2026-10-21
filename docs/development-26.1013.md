# Development source profiles

## Development profiles for 26.1013

Source profiles `desktop-26.1013.3656.0-sqlite-v2` and `desktop-26.1013.4894.0-sqlite-v2` pin upstream `4ebc485ca321243727539187169425fcf972f2c4`, Rust 1.95.0 and compatibility version `0.163.0-alpha.10.2`. Each binds its own official backend identity and all 77 migrations across six database families. The 4894 profile retains the predecessor's patch semantics and migration bytes with a separate source identity.

These are development source profiles. The stable release remains v0.2.3; a new installable desktop release requires independent public-source build, installer and runtime acceptance. Existing profile identities, default selection and legacy apply entry points are preserved.

The synthetic multi-page replay accepts an explicitly supplied backend and checks cold history restoration against a loopback service. It creates only synthetic task data and makes no paid model requests.
