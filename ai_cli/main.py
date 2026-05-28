import typer
from ai_cli.cli.commands import explain_code, fix_bug

app = typer.Typer()

app.command()(explain_code)
app.command()(fix_bug)

if __name__ == "__main__":
    app()