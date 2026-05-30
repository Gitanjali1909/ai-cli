import typer
from ai_cli.cli.commands import explain, fix, last, review

app = typer.Typer()

app.command()(explain)
app.command()(fix)
app.command()(review)
app.command()(last)

if __name__ == "__main__":
    app()
