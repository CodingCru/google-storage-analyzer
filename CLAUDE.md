# CLAUDE.md — google-storage-analyzer

## What this project is

A CLI tool (`gsa`) that analyzes what's eating your Google account storage across Drive, Gmail, and Photos. Built because Google's own UI is too shallow — especially for Gmail, where there's no native way to see top senders by storage or largest messages.

## Repo & CLI naming

- **GitHub repo:** `google-storage-analyzer` (SEO-optimized)
- **CLI command:** `gsa`
- **GitHub org:** CodingCru

## Stack

- Python 3.10+
- `typer` — CLI framework
- `rich` — terminal UI (progress bars, tables)
- `google-api-python-client` + `google-auth-oauthlib` — Google APIs
- `diskcache` — local cache for scan results
- `requests` — HTTP for Photos HEAD requests

## Local setup

```bash
pip install -e ~/REPOS/GITHUB/CodingCru/google-storage-analyzer
gsa auth   # opens browser OAuth flow
```

## Credentials location

- `~/.gsa/credentials.json` — OAuth client secret (downloaded from Google Cloud Console)
- `~/.gsa/token.json` — auto-saved after first auth
- `~/.gsa/cache/` — diskcache scan results

**Note:** We use `~/.gsa/` not `~/.config/gsa/` because macOS blocks terminal writes to `~/.config` without Full Disk Access.

## Google Cloud project

- Project: `gsa-personal`
- Project ID: `gsa-personal`
- APIs enabled: Google Drive API, Gmail API, Photos Library API
- OAuth client: `gsa-cli` (Desktop app type)
- Test user added: `<your Google account email>` (add yourself as a test user in the OAuth consent screen while the app is unpublished/Testing)

## CLI commands

```bash
gsa auth                        # one-time OAuth
gsa scan --drive                # scan Drive (fast, seconds)
gsa scan --gmail                # scan Gmail (slow, ~2hrs for 40k messages)
gsa scan --photos               # scan Photos (slow, resumable)
gsa scan --all                  # all three
gsa scan --photos --no-resume   # start Photos from scratch
gsa report                      # show cached results
gsa report --top 50             # show top 50 instead of 20
gsa clear-cache                 # wipe cached scan data
```

## Current status (as of 2026-08-08)

- Drive scan: working.
- Gmail scan: working, completed a full end-to-end scan successfully (tens of thousands of messages).
- Photos scan: **item-level scanning is not viable.** `mediaItems.list` returns `403 Forbidden` — Google restricts this endpoint (as of policy changes in 2025) to app-created content only, for OAuth clients that haven't completed Google's additional access verification review. Our `gsa-cli` client is in Testing mode and will never pass this without a formal review. `gsa scan --photos` is now a no-op that prints an explanation instead of attempting the scan.
- Photos usage is instead **estimated via quota math** in `gsa report`: `Photos ≈ Used − Drive − Gmail`.

## Known issues / next up

- Gmail scan has no resume capability — if interrupted, it restarts from zero. Should add incremental caching keyed by message ID (same pattern as Photos scanner already has).
- **Google OAuth token expiry**: refresh tokens for apps in Testing publishing status expire after ~7 days of inactivity, causing `RefreshError: invalid_grant`. Fix is `rm ~/.gsa/token.json && gsa auth`. `get_credentials()` doesn't currently catch this and fall back to a fresh login automatically — would be a good robustness fix.
- Gmail is read-only (`gmail.readonly` scope) by design — the CLI cannot delete or modify anything. If we want a "purge these senders" feature (e.g. clearing out LinkedIn Job Alerts), it needs a new command that requests `gmail.modify` (or the narrower `gmail.readonly` + move-to-trash isn't possible without modify), which means a fresh OAuth consent. Not yet built. Until then, use Gmail's own search UI (e.g. `from:jobalerts-noreply@linkedin.com`) to review/delete manually.
- `gsa/report/display.py` previously read a nonexistent `usageInGmail` field from Drive API's `about.get`. **Fixed 2026-08-08**: verified live API response only has `limit`, `usage`, `usageInDrive`, `usageInDriveTrash` — no separate Gmail field exists. Quota display now computes `Other = Used − Drive − Trash` and further splits Gmail/Photos using the Gmail scan cache when available.
- `photos.py` previously recorded failed size lookups (timeout/429/expired URL) as a permanent `0`, silently undercounting on resume. **Fixed 2026-08-08**: failures are now left out of `seen` so they retry on the next run. (Moot for now given the `mediaItems.list` 403 issue above, but the fix stands if/when Photos scanning becomes viable again, e.g. via the Photos Picker API.)
- `__pycache__` directories: already covered in `.gitignore` — this note was stale, no action needed.

## Rich Progress gotcha

Do NOT use custom task fields named `total` — it conflicts with rich's built-in `task.total`. Use `task.completed` and `task.total` directly in TextColumn format strings instead of `task.fields[total]`.
