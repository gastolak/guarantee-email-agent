"""CLI interface for the guarantee email agent."""

import typer

app = typer.Typer(
    name="agent",
    help="Instruction-driven AI agent for warranty email automation"
)


@app.command()
def run():
    """Start the warranty email agent for continuous processing."""
    typer.echo("Agent run command - to be implemented in Epic 4")


@app.command()
def eval():
    """Execute the complete evaluation test suite."""
    typer.echo("Agent eval command - to be implemented in Epic 5")


if __name__ == "__main__":
    app()
