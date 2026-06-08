import time
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

console = Console()

PHOTOS_API = "https://photoslibrary.googleapis.com/v1"
REQUESTS_PER_SECOND = 5  # conservative — Photos API has no published quota but throttles aggressively
BATCH_SIZE = 100


def scan(creds: Credentials, cache, resume: bool = True) -> dict:
    existing = cache.get("photos", {}) if resume else {}
    seen: dict[str, int] = existing.get("items_by_id", {})

    console.print(
        f"[yellow]Photos slow-scan: ~{REQUESTS_PER_SECOND} req/s. "
        "This may take a while for large libraries. Ctrl+C saves progress.[/yellow]"
    )

    items = _list_all_items(creds)
    unseen = [it for it in items if it["id"] not in seen]

    console.print(f"Found [bold]{len(items)}[/bold] items ({len(unseen)} not yet sized).")

    try:
        _fetch_sizes(creds, unseen, seen)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted — saving progress.[/yellow]")

    total = sum(seen.values())
    sorted_items = sorted(
        [{"id": k, "size": v} for k, v in seen.items()],
        key=lambda x: x["size"],
        reverse=True,
    )

    result = {
        "total": total,
        "scanned": len(seen),
        "total_items": len(items),
        "largest": sorted_items[:100],
        "items_by_id": seen,
    }
    cache["photos"] = result
    return result


def _list_all_items(creds: Credentials) -> list[dict]:
    items = []
    page_token = None
    session = _auth_session(creds)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]Listing Photos library..."),
        TextColumn("{task.fields[count]} items"),
        console=console,
    ) as progress:
        task = progress.add_task("list", total=None, count=0)

        while True:
            params = {"pageSize": BATCH_SIZE}
            if page_token:
                params["pageToken"] = page_token

            resp = session.get(f"{PHOTOS_API}/mediaItems", params=params)
            resp.raise_for_status()
            data = resp.json()

            batch = data.get("mediaItems", [])
            items.extend(batch)
            progress.update(task, count=len(items))

            page_token = data.get("nextPageToken")
            if not page_token:
                break

            time.sleep(1 / REQUESTS_PER_SECOND)

    return items


def _fetch_sizes(creds: Credentials, items: list[dict], seen: dict[str, int]) -> None:
    session = _auth_session(creds)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]Fetching photo sizes..."),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("sizes", total=len(items))
        failures = 0

        for i, item in enumerate(items):
            meta = item.get("mediaMetadata", {})
            is_video = "video" in meta

            base_url = item.get("baseUrl", "")
            if not base_url:
                # Legitimately sizeless (no content behind it) — safe to record and never retry.
                seen[item["id"]] = 0
                progress.update(task, advance=1)
                continue

            # =dv → download video original, =d → download photo original
            # Photos API doesn't return sizes; HEAD on the download URL gives Content-Length
            download_url = base_url + ("=dv" if is_video else "=d")

            try:
                head = session.head(download_url, allow_redirects=True, timeout=10)
                head.raise_for_status()
                size = int(head.headers.get("Content-Length", 0))
                seen[item["id"]] = size
            except Exception:
                # Don't record on failure (timeout, 429, expired baseUrl, etc.) — leaving the
                # item out of `seen` means it gets retried on the next `--resume` run instead
                # of being silently undercounted as 0 forever.
                failures += 1

            progress.update(task, advance=1)

            if i % REQUESTS_PER_SECOND == REQUESTS_PER_SECOND - 1:
                time.sleep(1)

        if failures:
            console.print(
                f"[yellow]{failures} item(s) failed to size and will be retried on the next run.[/yellow]"
            )


def _auth_session(creds: Credentials) -> requests.Session:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {creds.token}"
    return session
