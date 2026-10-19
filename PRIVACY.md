# Local data and publication boundaries

The application reads Codex rollout files locally. This source repository does not bundle real logs, snapshots, native databases, source configurations, tokens, account credentials, recovery archives, or investigation reports. Regression tests create synthetic records in temporary directories.

Dashboard responses, exports and session details can contain conversation text, project paths, device identifiers and tool data. Keep the service bound to loopback (`127.0.0.1`); it is not an authenticated multi-user or internet-facing service. Do not expose its port publicly.

The dashboard maintains its own parse cache and optional remote snapshot files. It does not rewrite source rollout logs or native Codex databases. The optional partial native-history exporter writes a separate destination only; its outputs are private even when they look like reports.

`.gitignore` excludes common runtime artifacts as a convenience, not as a complete privacy guarantee. Before sharing a reproduction, replace all data with synthetic inputs and inspect both files and Git history. Do not post real exports, screenshots with private details, `auth.json`, source configurations, `.env` files, SQLite files, or native-history recovery output to issues or pull requests.

API-equivalent cost estimates are analytical estimates, not subscription invoices. Partial native metadata counters are not used to invent missing token usage.
