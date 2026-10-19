# Historical sources and accounting

The dashboard reads local rollout logs. Backup/profile homes are opt-in. A home without readable session files is shown as unavailable; it does not become zero-cost proof of missing history.

Use `--sources-config PATH` with a version-1 configuration. These are fictional example paths, not a configuration to copy unchanged:

```json
{
  "version": 1,
  "sources": [
    {"id": "current", "label": "Current", "codex_home": "C:/Users/example/.codex", "origin_id": "example-workstation"},
    {"id": "backup", "label": "Backup", "codex_home": "D:/ExampleArchive/codex-home", "origin_id": "example-workstation"}
  ]
}
```

Shared `origin_id` is an explicit assertion that homes belong to the same logical device/origin. Only use it after confirming that relationship. Independent devices remain separate by default. Similar titles, token totals or timestamps are not grounds for merging sessions.

On Windows, persistent configuration lives under `%APPDATA%/cousash/`; other systems use the existing platform configuration location. `--codex-home` overrides the configured source list. Keep configurations and exported snapshots private.

Continuation fragments preserve distinct event occurrences and counter-reset behavior. Provenance identifies contributing files. Model totals use token-event attribution; unresolved models remain unknown. Cached input is a subset of input and reasoning is a subset of output, not additional totals. The model filter selects conversations containing a model; it does not change a mixed-model conversation into a single-model record.

## Partial native-history projection

`tools/native_history_export.py` is an optional Python utility, not an automatic recovery process. Call `export_native(state_path, history_path, thread_ids, empty_destination)` only against databases you own and an existing empty local output directory. Its read-only SQLite connections deny writes to the input databases.

Outputs may contain private conversation content and filesystem paths. A conservative pattern guard withholds suspicious items; it is **not a guarantee that all secrets are detected**. Never publish its output. Exported native projections are explicitly partial and excluded from dashboard usage; they cannot supply original per-event token counts or missing rollout boundaries. The utility expects the supported native table layout and does not promise compatibility with every application/database version.
