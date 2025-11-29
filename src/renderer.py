from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from dateutil import parser

class Renderer:
    """
    Renders GitHub activity items into a formatted console table.
    """
    def __init__(self):
        """Initialize the renderer with a rich console."""
        self.console = Console()

    def render(self, items):
        """
        Render a list of activity items to the console.

        Deduplicates items by URL, groups them by repository, and sorts by update time.

        Args:
            items (list): A list of dictionaries representing GitHub items (Issues, PRs).
        """
        if not items:
            self.console.print("[yellow]No new activity found.[/yellow]")
            return

        # Deduplicate by URL
        unique_items = {item['url']: item for item in items}.values()
        
        # Sort by Repo then Date
        sorted_items = sorted(unique_items, key=lambda x: (x['repository']['nameWithOwner'], x['updatedAt']))

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Type", style="dim", width=8)
        table.add_column("Title", style="cyan", no_wrap=False) # Allow wrapping
        table.add_column("Author", style="green")
        table.add_column("Updated", style="yellow")

        current_repo = None
        
        for item in sorted_items:
            repo_name = item['repository']['nameWithOwner']
            
            if repo_name != current_repo:
                if current_repo is not None:
                    table.add_section()
                table.add_row(f"[bold]{repo_name}[/bold]", "", "", "")
                current_repo = repo_name

            item_type = item.get("type", "Unknown")
            
            # Format title with link
            title_text = f"[link={item['url']}]{item['title']} (#{item['number']})[/link]"
            
            # Add extra context (last comment) if available
            context = ""
            if "comments" in item and item["comments"]["nodes"]:
                last_comment = item["comments"]["nodes"][0]
                author = last_comment["author"]["login"] if last_comment["author"] else "Unknown"
                context = f" [dim]Last comment by {author}[/dim]"
            elif "reviews" in item and item["reviews"]["nodes"]:
                 last_review = item["reviews"]["nodes"][0]
                 author = last_review["author"]["login"] if last_review["author"] else "Unknown"
                 context = f" [dim]Reviewed by {author}[/dim]"
            
            final_title = title_text + context
            
            author_login = item['author']['login'] if item['author'] else "Bot"
            
            # Simple date formatting
            date_str = item['updatedAt'][:10]

            table.add_row(item_type, final_title, author_login, date_str)

        self.console.print(table)
