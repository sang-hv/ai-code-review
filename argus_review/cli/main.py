import asyncio

import typer

app = typer.Typer(help="ArgusReview CLI")


@app.command("run")
def run():
    """Run the full AI review pipeline"""
    from argus_review.cli.commands.run_review import run_review_command

    typer.secho("Starting full AI review...", fg=typer.colors.CYAN, bold=True)
    asyncio.run(run_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-inline")
def run_inline():
    """Run only the inline review"""
    from argus_review.cli.commands.run_inline_review import run_inline_review_command

    typer.secho("Starting inline AI review...", fg=typer.colors.CYAN)
    asyncio.run(run_inline_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-context")
def run_context():
    """Run only the context review"""
    from argus_review.cli.commands.run_context_review import run_context_review_command

    typer.secho("Starting context AI review...", fg=typer.colors.CYAN)
    asyncio.run(run_context_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-summary")
def run_summary():
    """Run only the summary review"""
    from argus_review.cli.commands.run_summary_review import run_summary_review_command

    typer.secho("Starting summary AI review...", fg=typer.colors.CYAN)
    asyncio.run(run_summary_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-inline-reply")
def run_inline_reply():
    """Run only the inline reply review"""
    from argus_review.cli.commands.run_inline_reply_review import run_inline_reply_review_command

    typer.secho("Starting inline reply AI review...", fg=typer.colors.CYAN)
    asyncio.run(run_inline_reply_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-summary-reply")
def run_summary_reply():
    from argus_review.cli.commands.run_summary_reply_review import run_summary_reply_review_command

    typer.secho("Starting summary reply AI review...", fg=typer.colors.CYAN)
    asyncio.run(run_summary_reply_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-agent")
def run_agent():
    """Run the full agent-light review pipeline (inline + summary, low quota)"""
    from argus_review.cli.commands.run_agent_review import run_agent_review_command

    typer.secho("Starting agent-light AI review...", fg=typer.colors.CYAN, bold=True)
    asyncio.run(run_agent_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-agent-inline")
def run_agent_inline():
    """Run only the agent-light inline review (single session, low quota)"""
    from argus_review.cli.commands.run_agent_inline_review import run_agent_inline_review_command

    typer.secho("Starting agent-light inline AI review...", fg=typer.colors.CYAN)
    asyncio.run(run_agent_inline_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("run-agent-summary")
def run_agent_summary():
    """Run only the agent-light summary review (single session, low quota)"""
    from argus_review.cli.commands.run_agent_summary_review import run_agent_summary_review_command

    typer.secho("Starting agent-light summary AI review...", fg=typer.colors.CYAN)
    asyncio.run(run_agent_summary_review_command())
    typer.secho("AI review completed successfully!", fg=typer.colors.GREEN, bold=True)


@app.command("clear-inline")
def clear_inline():
    """Remove all AI-generated inline review comments"""
    from argus_review.cli.commands.run_clear_inline_review import run_clear_inline_review

    typer.secho("Clearing inline AI review comments...", fg=typer.colors.YELLOW)
    asyncio.run(run_clear_inline_review())
    typer.secho("Inline AI comments cleared", fg=typer.colors.GREEN, bold=True)


@app.command("clear-summary")
def clear_summary():
    """Remove all AI-generated summary review comments"""
    from argus_review.cli.commands.run_clear_summary_review import run_clear_summary_review

    typer.secho("Clearing summary AI review comments...", fg=typer.colors.YELLOW)
    asyncio.run(run_clear_summary_review())
    typer.secho("Summary AI comments cleared", fg=typer.colors.GREEN, bold=True)


@app.command("show-config")
def show_config():
    """Show the current resolved configuration"""
    from argus_review.config import settings

    typer.secho("Loaded ArgusReview configuration:", fg=typer.colors.CYAN, bold=True)
    typer.echo(settings.model_dump_json(indent=2, exclude_none=True))


@app.command("dump-schema")
def dump_schema(
        output: str = typer.Option(
            None, "--output", "-o",
            help="Write the schema to this file instead of stdout.",
        ),
):
    """
    Dump the configuration JSON Schema.

    This is the single source of truth for every config option (providers,
    fields, defaults). It does not require a valid config to run, so it can be
    used to drive docs or a config generator UI.
    """
    import json
    from pathlib import Path

    from argus_review.config import Settings

    schema = Settings.model_json_schema()
    text = json.dumps(schema, indent=2, ensure_ascii=False)

    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        typer.secho(f"Schema written to {output}", fg=typer.colors.GREEN, bold=True)
        return

    typer.echo(text)


if __name__ == "__main__":
    app()
