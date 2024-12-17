import click
import os
import subprocess

@click.group()
def cli():
    pass

@cli.command()
def init():
    """Initialize the database and migrations"""
    subprocess.run(["alembic", "init", "alembic"])
    click.echo("Initialized alembic migrations")

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
def migrate(message):
    """Generate a new migration"""
    subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])
    click.echo(f"Created new migration: {message}")

@cli.command()
def upgrade():
    """Apply all pending migrations"""
    subprocess.run(["alembic", "upgrade", "head"])
    click.echo("Applied all migrations")

@cli.command()
def downgrade():
    """Rollback the last migration"""
    subprocess.run(["alembic", "downgrade", "-1"])
    click.echo("Rolled back one migration")

if __name__ == '__main__':
    cli() 