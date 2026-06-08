# Architecture

## Overview

```
gsa/
├── cli.py          # Entry point — typer commands
├── auth.py         # Google OAuth flow + token persistence
├── cache.py        # diskcache wrapper for persisting scan results
├── scanners/
│   ├── drive.py    # Google Drive API scanner
│   ├── gmail.py    # Gmail API scanner
│   └── photos.py   # Google Photos API scanner (slow-fetch mode)
└── report/
    └── display.py  # Rich tables + quota summary renderer
```

## Data flow

```
gsa scan --gmail
    → auth.py: load/refresh OAuth token
    → scanners/gmail.py: list all message IDs, fetch each for size + sender
    → cache.py: persist results to ~/.gsa/cache/ (diskcache)

gsa report
    → auth.py: load token
    → Drive API about.get: fetch live quota numbers
    → cache.py: load cached scan results
    → report/display.py: render tables to terminal
```

## Auth

OAuth 2.0 via `google-auth-oauthlib`. Scopes are read-only for all three services:
- `drive.readonly`
- `gmail.readonly`
- `photoslibrary.readonly`

Token auto-refreshes on expiry. Stored at `~/.gsa/token.json`.

## Scanners

### Drive (`scanners/drive.py`)

Uses `files.list` with `pageSize=1000` to walk all user-owned files. Builds an in-memory tree to compute folder sizes recursively. Returns items sorted by size descending.

**Limitation:** Only sees files owned by the user. Files shared with you but owned by others don't count toward your quota and aren't returned.

### Gmail (`scanners/gmail.py`)

Two-phase:
1. `messages.list` — paginate to collect all message IDs (~39,888 for this account)
2. `messages.get` (format=metadata) — fetch size estimate + From/Subject headers per message

Aggregates: top senders by total bytes, largest individual messages.

**Rate limiting:** Sleeps 0.1s every 10 requests. Exponential backoff (2^n seconds) on HTTP 429.

**Limitation:** No resume — if interrupted, restarts from zero. Fix: cache results keyed by message ID and skip already-fetched ones.

**Time estimate:** ~2 hours for 40k messages at ~200ms/request.

### Photos (`scanners/photos.py`)

Three-phase:
1. `photoslibrary.googleapis.com/v1/mediaItems` — list all items (no sizes in response)
2. For each item: build download URL (`baseUrl=d` for photos, `baseUrl=dv` for videos)
3. HEAD request on download URL → read `Content-Length` header

**Rate:** 5 req/s with 1s sleep every batch. Resumable — progress saved to diskcache keyed by media item ID. Ctrl+C saves state, next run skips already-sized items.

**Limitation:** Google Photos API intentionally omits file sizes. The HEAD request workaround is the only way to get exact sizes without downloading files.

## Cache

`diskcache.Cache` stored at `~/.gsa/cache/`. Keys:
- `"drive"` → `{total, items: [{id, name, size, mimeType, trashed, parents}]}`
- `"gmail"` → `{total, top_senders: [{sender, size}], largest_messages: [{id, sender, subject, size}]}`
- `"photos"` → `{total, scanned, total_items, largest: [{id, size}], items_by_id: {id: size}}`

Cache persists between runs. Clear with `gsa clear-cache`.

## Report

`report/display.py` renders three sections using `rich` tables:
1. Quota summary (live from Drive API `about.get`)
2. Drive largest files
3. Gmail top senders + largest messages
4. Photos total + largest items (when scanned)

## Google Cloud setup

- Project: `gsa-personal`
- OAuth client type: Desktop app (required for `run_local_server` flow)
- Consent screen: External, test user only (not published)
- APIs: Drive API v3, Gmail API v1, Photos Library API v1
