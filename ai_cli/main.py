import typer
from ai_cli.cli.commands import explain_code, fix_bug, review

app = typer.Typer()

app.command()(explain_code)
app.command()(fix_bug)
app.command()(review)

if __name__ == "__main__":
    app()
