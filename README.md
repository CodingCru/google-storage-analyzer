# google-storage-analyzer

Find what's eating your Google Drive, Gmail, and Photos storage — from the terminal.

## Why

Google's built-in storage UI barely shows you anything useful. This tool gives you:

- **Drive**: folder tree with sizes, largest files, items in trash
- **Gmail**: top senders by bytes consumed, largest individual messages
- **Photos**: exact file sizes via slow-fetch (resumable, runs overnight if needed)

## Setup

### 1. Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Drive API**, **Gmail API**, **Photos Library API**
3. Create OAuth 2.0 credentials (Desktop app type)
4. Download the JSON and save it to `~/.config/gsa/credentials.json`

### 2. Install

```bash
pip install google-storage-analyzer
```

Or from source:

```bash
git clone https://github.com/CodingCru/google-storage-analyzer
cd google-storage-analyzer
pip install -e .
```

### 3. Authenticate

```bash
gsa auth
```

This opens a browser window for Google OAuth. Token is saved locally.

## Usage

```bash
# Scan Drive and Gmail (fast — seconds to minutes)
gsa scan --drive --gmail

# Scan Photos (slow — may take 30+ minutes for large libraries, resumable)
gsa scan --photos

# Scan everything
gsa scan --all

# Show results
gsa report

# Show top 50 instead of 20
gsa report --top 50

# Clear cached data and rescan from scratch
gsa clear-cache && gsa scan --all
```

## How Photos scanning works

The Google Photos API doesn't expose file sizes directly. `gsa` fetches a download URL for each photo/video and sends a `HEAD` request to get the `Content-Length` header. It runs at ~5 requests/second to stay polite. Progress is saved automatically — interrupt with `Ctrl+C` and resume later with `gsa scan --photos`.

## Privacy

All data stays local. Nothing is uploaded anywhere. Credentials and scan results are stored in `~/.config/gsa/`.
