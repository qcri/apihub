import sys

try:
    import click
except ImportError:
    sys.stderr.write('Please install "apihub[cli] to install cli option"')
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

from apihub.client import Client


@click.command()
@click.option("--username", "-u", type=str, default="", help="username")
@click.option("--password", "-p", type=str, default="", help="password")
@click.option("--endpoint", "-e", type=str, default="http://localhost", help="endpoint")
def login(username, password, endpoint):
    client = Client({"endpoint": endpoint})
    client.authenticate(username=username, password=password)
    client.save_state()


@click.command()
@click.argument("application", nargs=1)
def refresh_token(application):
    # check if login
    client = Client.load_state()
    if client.token is None:
        sys.stderr.write("You need to login first")
        sys.exit(1)

    client.refresh_application_token(application)
