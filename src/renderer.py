from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from dateutil import parser

class Renderer:
    def __init__(self):
        self.console = Console()

    def render(self, items):
        if not items:
            self.console.print(Panel("No new activity found.", style="yellow"))
            return

        # Deduplicate by URL
        unique_items = {item['url']: item for item in items}.values()
        
        # Sort by UpdatedAt (newest first)
        sorted_items = sorted(unique_items, key=lambda x: x['updatedAt'], reverse=True)

        # Group by Repo
        grouped = {}
        for item in sorted_items:
            repo = item['repository']['nameWithOwner']
            if repo not in grouped:
                grouped[repo] = []
            grouped[repo].append(item)

        for repo_name, repo_items in grouped.items():
            table = Table(title=f"Activity in [bold cyan]{repo_name}[/]", box=box.SIMPLE, expand=True)
            table.add_column("Type", style="magenta", width=10)
            table.add_column("Title", style="white")
            table.add_column("Author", style="green")
            table.add_column("Last Update", style="dim")

            for item in repo_items:
                updated_at = parser.isoparse(item['updatedAt']).strftime("%Y-%m-%d %H:%M")
                
                title_link = f"[link={item['url']}]{item['title']}[/link] (#{item['number']})"
                
                # Check for new comments
                comments = item.get('comments', {}).get('nodes', [])
                if comments:
                    last_comment = comments[0]
                    comment_info = f" (Comment by {last_comment['author']['login']})"
                else:
                    comment_info = ""

                table.add_row(
                    item.get('type', 'Unknown'),
                    title_link + comment_info,
                    item['author']['login'],
                    updated_at
                )

            self.console.print(table)
            self.console.print() # Empty line
