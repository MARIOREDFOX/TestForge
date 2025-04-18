import click
from testforge_cli_utils.core.executor import run_tests


@click.group()
def cli():
    """TestForge - Hardware Automation CLI"""
    pass


# @cli.command()
# @click.option('--tag', default=None, help="Run tests by tag")
# @click.option('--test', default=None, help="Run specific test file")
# def run(tag, test):
#    """Run tests"""
#    run_tests(tag=tag, test=test)


@click.command()
@click.option("--tag", default=None, help="Tag to filter tests.")
@click.option("--test", default=None, help="Test name to run.")
@click.option("--env", required=True, help="Path to the environment YAML file.")
@click.option(
    "--config-file",
    default="examples/test_config.yaml",
    help="Path to the config YAML file.",
)
def run(tag, test, env, config_file):
    """Run the test suite."""
    run_tests(config_file=config_file, tag=tag, test=test, env_file=env)


@cli.command()
def version():
    """Display version"""
    click.echo("TestForge v0.1.6")


cli.add_command(run)
# Add this line to make it executable when run directly
if __name__ == "__main__":
    cli()
