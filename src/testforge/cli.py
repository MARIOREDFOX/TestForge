import click
from testforge.core.executor import run_tests

@click.group()
def cli():
    """TestForge - Hardware Automation CLI"""
    pass

@cli.command()
@click.option('--tag', default=None, help="Run tests by tag")
@click.option('--test', default=None, help="Run specific test file")
def run(tag, test):
    """Run tests"""
    run_tests(tag=tag, test=test)

@cli.command()
def version():
    """Display version"""
    click.echo("TestForge v0.1.0")

# Add this line to make it executable when run directly
if __name__ == "__main__":
    cli()

