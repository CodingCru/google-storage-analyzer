from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def fmt_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def show_quota(about: dict) -> None:
    quota = about.get("storageQuota", {})
    total = int(quota.get("limit", 0))
    used = int(quota.get("usage", 0))
    drive = int(quota.get("usageInDrive", 0))
    gmail = int(quota.get("usageInDriveTrash", 0))  # repurposed field name from API

    pct = (used / total * 100) if total else 0

    console.rule("[bold]Google Storage Quota[/bold]")
    console.print(f"  Total:  [bold]{fmt_size(total)}[/bold]")
    console.print(f"  Used:   [bold cyan]{fmt_size(used)}[/bold cyan]  ({pct:.1f}%)")
    console.print(f"  Drive:  {fmt_size(drive)}")
    console.print()


def show_drive(data: dict, top: int = 20) -> None:
    if not data:
        return
    console.rule("[bold blue]Google Drive — Largest Files[/bold blue]")
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Size", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Trashed", justify="center")

    for item in data["items"][:top]:
        table.add_row(
            fmt_size(item["size"]),
            item["name"],
            "[red]yes[/red]" if item["trashed"] else "",
        )

    console.print(table)
    console.print(f"  Drive total (owned files): [bold]{fmt_size(data['total'])}[/bold]\n")


def show_gmail(data: dict, top: int = 20) -> None:
    if not data:
        return
    console.rule("[bold green]Gmail — Top Senders by Storage[/bold green]")
    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Size", justify="right", style="cyan")
    table.add_column("Sender")

    for row in data["top_senders"][:top]:
        table.add_row(fmt_size(row["size"]), row["sender"])

    console.print(table)

    console.rule("[bold green]Gmail — Largest Individual Messages[/bold green]")
    table2 = Table(box=box.SIMPLE, show_header=True)
    table2.add_column("Size", justify="right", style="cyan")
    table2.add_column("From")
    table2.add_column("Subject")

    for msg in data["largest_messages"][:top]:
        table2.add_row(fmt_size(msg["size"]), msg["sender"][:40], msg["subject"][:60])

    console.print(table2)
    console.print(f"  Gmail estimated total: [bold]{fmt_size(data['total'])}[/bold]\n")


def show_photos(data: dict, top: int = 20) -> None:
    if not data:
        return
    scanned = data.get("scanned", 0)
    total_items = data.get("total_items", 0)
    console.rule("[bold magenta]Google Photos[/bold magenta]")
    console.print(f"  Scanned: {scanned}/{total_items} items")
    console.print(f"  Estimated total: [bold]{fmt_size(data['total'])}[/bold]")
    if scanned < total_items:
        console.print(f"  [yellow]Run `gsa scan --photos` again to finish sizing remaining {total_items - scanned} items.[/yellow]")
    console.print()
