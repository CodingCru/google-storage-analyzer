from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

console = Console()


def scan(creds: Credentials, cache) -> dict:
    service = build("drive", "v3", credentials=creds)

    files = []
    page_token = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scanning Drive..."),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("{task.fields[count]} files"),
        console=console,
    ) as progress:
        task = progress.add_task("drive", total=None, count=0)

        while True:
            resp = service.files().list(
                pageSize=1000,
                fields="nextPageToken, files(id, name, size, mimeType, parents, trashed)",
                pageToken=page_token,
                includeItemsFromAllDrives=False,
                corpora="user",
            ).execute()

            batch = resp.get("files", [])
            files.extend(batch)
            progress.update(task, count=len(files))

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    result = _build_tree(service, files)
    cache["drive"] = result
    return result


def _build_tree(service, files: list) -> dict:
    by_id = {f["id"]: f for f in files}
    children = {}

    for f in files:
        for parent in f.get("parents", []):
            children.setdefault(parent, []).append(f["id"])

    def folder_size(fid: str) -> int:
        f = by_id.get(fid, {})
        if f.get("mimeType") == "application/vnd.google-apps.folder":
            return sum(folder_size(c) for c in children.get(fid, []))
        return int(f.get("size", 0))

    top_level = [
        f for f in files
        if not f.get("parents") or all(p not in by_id for p in f.get("parents", []))
    ]

    items = []
    for f in files:
        size = int(f.get("size", 0)) if f.get("mimeType") != "application/vnd.google-apps.folder" else folder_size(f["id"])
        items.append({
            "id": f["id"],
            "name": f["name"],
            "size": size,
            "mimeType": f.get("mimeType"),
            "trashed": f.get("trashed", False),
            "parents": f.get("parents", []),
        })

    items.sort(key=lambda x: x["size"], reverse=True)
    total = sum(int(f.get("size", 0)) for f in files if f.get("mimeType") != "application/vnd.google-apps.folder")

    return {"total": total, "items": items}
