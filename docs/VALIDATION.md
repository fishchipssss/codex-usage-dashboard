# Validation of the community changes

Local validation on Windows / Python 3.12:

- 115 unittest cases: 114 passed, one filesystem-ctime-dependent case skipped.
- Tests generate synthetic rollout records, source homes, cache files and native-history tables inside temporary directories. No native/user databases or real rollout fixtures are needed.
- Coverage includes filesystem identity bounds, persistent cache behavior, same-origin deduplication, independent devices, continuation resets, repeated event occurrences, per-event model accounting, date filtering, fork dependencies and read-only partial history export.
- Portable frontend contracts cover total/subset labels, theme/reduced-motion tokens, keyboard/dialog behavior, local assets, source provenance and responsive breakpoints.
- Installer JavaScript syntax checked with Node.js.
- Fixture temporary roots are canonicalized so hosted Windows 8.3 aliases and long paths refer to the same expected files; path/count assertions remain unchanged.
- Public-worktree service verified on loopback port 8765 using four synthetic sessions. README screenshot shows those synthetic sessions, not a user's usage history.

The desktop UI was also exercised locally at 1920, 1440, 1366, 1024 and 390 CSS px in light and dark appearances during the redesign. Keyboard sorting, selection, filters, calendar, source disclosure and dialog dismissal were exercised. Physical Windows scaling and screen-reader speech were not tested. The GitHub Actions matrix is separate evidence; local passing results do not imply that hosted CI has passed.

Run locally:

```bash
python -B -m unittest discover -s tests -v
node --check bin/install.js
```

Historical reconstruction does not certify missing event data or native database compatibility beyond tested layouts. The optional exporter retains partial/withheld status rather than manufacturing complete conversations or token usage.
