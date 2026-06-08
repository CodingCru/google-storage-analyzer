import typer
from googleapiclient.discovery import build
from rich.console import Console

from gsa.auth import get_credentials
from gsa.cache import get_cache
from gsa.report.display import show_quota, show_drive, show_gmail, show_photos
from gsa import scanners

app = typer.Typer(help="Analyze what's eating your Google storage.")
console = Console()


@app.command()
def scan(
    drive: bool = typer.Option(False, "--drive", help="Scan Google Drive"),
    gmail: bool = typer.Option(False, "--gmail", help="Scan Gmail"),
    photos: bool = typer.Option(False, "--photos", help="Scan Google Photos (slow)"),
    all_services: bool = typer.Option(False, "--all", help="Scan all services"),
    no_resume: bool = typer.Option(False, "--no-resume", help="Ignore cached progress and start fresh"),
):
    """Scan your Google account storage."""
    if all_services:
        drive = gmail = photos = True

    if not any([drive, gmail, photos]):
        console.print("[red]Specify at least one of --drive, --gmail, --photos, or --all[/red]")
        raise typer.Exit(1)

    creds = get_credentials()
    cache = get_cache()

    if drive:
        from gsa.scanners import drive as drive_scanner
        drive_scanner.scan(creds, cache)
        console.print("[bold blue]Drive scan complete.[/bold blue]")

    if gmail:
        from gsa.scanners import gmail as gmail_scanner
        gmail_scanner.scan(creds, cache)
        console.print("[bold green]Gmail scan complete.[/bold green]")

    if photos:
        from gsa.scanners import photos as photos_scanner
        photos_scanner.scan(creds, cache, resume=not no_resume)
        console.print("[bold magenta]Photos scan complete (or paused).[/bold magenta]")

    console.print("\nRun [bold]gsa report[/bold] to see results.")


@app.command()
def report(
    top: int = typer.Option(20, "--top", help="Number of top items to show"),
):
    """Display cached scan results."""
    creds = get_credentials()
    cache = get_cache()

    service = build("drive", "v3", credentials=creds)
    about = service.about().get(fields="storageQuota").execute()
    show_quota(about)

    show_drive(cache.get("drive"), top=top)
    show_gmail(cache.get("gmail"), top=top)
    show_photos(cache.get("photos"), top=top)


@app.command()
def auth():
    """Authenticate with Google (run this first)."""
    get_credentials()
    console.print("[bold green]Authentication successful.[/bold green]")
    console.print("Token saved to ~/.config/gsa/token.json")


@app.command()
def clear_cache():
    """Clear all cached scan data."""
    cache = get_cache()
    cache.clear()
    console.print("[yellow]Cache cleared.[/yellow]")


if __name__ == "__main__":
    app()
