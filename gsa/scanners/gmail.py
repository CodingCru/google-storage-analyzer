import time
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from rich.progress import Progress, SpinnerColumn, TextColumn, TaskProgressColumn
from rich.console import Console

console = Console()


def scan(creds: Credentials, cache) -> dict:
    service = build("gmail", "v1", credentials=creds)

    profile = service.users().getProfile(userId="me").execute()
    total_bytes = profile.get("messagesTotal", 0)

    message_ids = _list_all_messages(service)
    senders = {}
    largest = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Scanning Gmail..."),
        TaskProgressColumn(),
        TextColumn("{task.fields[done]}/{task.fields[total]} messages"),
        console=console,
    ) as progress:
        task = progress.add_task("gmail", total=len(message_ids), done=0, total=len(message_ids))

        for i, mid in enumerate(message_ids):
            msg = service.users().messages().get(
                userId="me", id=mid, format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()

            size = msg.get("sizeEstimate", 0)
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            sender = headers.get("From", "Unknown")
            subject = headers.get("Subject", "(no subject)")

            senders[sender] = senders.get(sender, 0) + size
            largest.append({"id": mid, "sender": sender, "subject": subject, "size": size})

            progress.update(task, advance=1, done=i + 1)

            if i % 10 == 9:
                time.sleep(0.1)

    largest.sort(key=lambda x: x["size"], reverse=True)
    top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)

    result = {
        "total": sum(senders.values()),
        "top_senders": [{"sender": s, "size": sz} for s, sz in top_senders[:50]],
        "largest_messages": largest[:100],
    }
    cache["gmail"] = result
    return result


def _list_all_messages(service) -> list[str]:
    ids = []
    page_token = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Listing Gmail messages..."),
        TextColumn("{task.fields[count]} found"),
        console=console,
    ) as progress:
        task = progress.add_task("list", total=None, count=0)

        while True:
            resp = service.users().messages().list(
                userId="me", pageToken=page_token, maxResults=500
            ).execute()

            batch = [m["id"] for m in resp.get("messages", [])]
            ids.extend(batch)
            progress.update(task, count=len(ids))

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    return ids
