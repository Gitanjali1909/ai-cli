import typer
from ai_cli.cli.commands import explain, review, fix, last

app = typer.Typer()
app.command()(explain)
app.command()(review)
app.command()(fix)
app.command()(last) 

if __name__ == "__main__":
    app()
app.command()(explain.explain)
app.command()(review.review)
app.command()(fix.fix)
app.command()(last.last)
