"""Typer Command Line Interface for MECH AI ADDON."""

import asyncio
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

from mech_cad.config import settings
from mech_cad.persistence.database import init_db
from mech_cad.pipeline.orchestrator import run_pipeline

app = typer.Typer(help="MECH AI ADDON - 2D Drawing to 3D CAD Platform CLI")
console = Console()


@app.command()
def db_upgrade():
    """Initialize database tables and migrations."""
    console.print("[yellow]Initializing database tables...[/yellow]")
    init_db()
    console.print("[green]Database initialized successfully.[/green]")


@app.command()
def convert(
    image_path: Path = typer.Argument(..., help="Path to 2D drawing file"),
    job_id: str = typer.Option("cli_job_001", help="Job ID identifier"),
):
    """Run 2D drawing to 3D CAD conversion via CLI."""
    console.print(f"[bold blue]Starting conversion for:[/] {image_path}")
    init_db()
    state = asyncio.run(run_pipeline(job_id=job_id, input_path=image_path))

    table = Table(title="Conversion Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Job ID", state.job_id)
    table.add_row("Final Stage", state.stage)
    table.add_row("STEP Path", str(state.step_path) if state.step_path else "None")
    table.add_row("Acceptance", state.acceptance.status if state.acceptance else "failed")
    if state.error:
        table.add_row("Error", state.error)

    console.print(table)


if __name__ == "__main__":
    app()
