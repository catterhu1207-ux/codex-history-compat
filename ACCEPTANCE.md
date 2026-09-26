# v0.2.0 acceptance

The Windows x64 public-source backend was built from upstream commit `10382da79a2a2d6e8ae221fa63077215389c1ad2` with Rust 1.95.0 and the 0.158.0-alpha.2 profile.

| Check | Result |
|---|---|
| Packaging and rejection tests | 7 passed |
| Compatibility module tests | 15 passed |
| Ordinary HTTP and real WebSocket replay | Both passed; four image tool calls remained paired with four outputs; notices were folded into their corresponding outputs |
| Cold task restoration | Saved model and high reasoning effort retained after the global defaults changed |
| Local compaction and remote compaction V2 | Both completed and restored the task in a fresh app-server process |
| Database migrations | All 57 source, compiled and synthetic database migration checksums matched |
| External dependencies | Locked package versions unchanged |

The replay used four generated images, synthetic tasks and a loopback service. Request content remained in memory. The official backend was checked against the same request scenario as a control. No credentials or paid model service were used.

`ACCEPTANCE.json` binds the results to the public source inputs. The recorded binary digest identifies this Windows build; another machine's source build may have a different binary digest.
