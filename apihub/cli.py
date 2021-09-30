import sys
import json
import time
import fileinput
from datetime import datetime, timedelta

try:
    import click
except ImportError:
    sys.stderr.write('Please install "apihub[cli] to install cli option"')
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

from apihub.client import Client


@click.group()
def cli():
    pass


def try_load_state(username):
    client = Client.load_state(filename=f"{username}.apihub")
    if client.token is None:
        click.echo("You need to login first")
        sys.exit(1)
    return client


@cli.command()
@click.option(
    "--endpoint", "-e", type=str, default="http://localhost:5000", help="endpoint"
)
@click.argument("username", nargs=1)
@click.argument("password", nargs=1)
def login(endpoint, username, password):
    client = Client({"endpoint": endpoint})
    client.authenticate(username=username, password=password)
    client.save_state(filename=f"{username}.apihub")


@cli.command()
@click.option("--admin", "-a", type=str, default="", help="manager username")
@click.option("--manager", "-m", type=str, default="", help="manager username")
@click.option("--username", "-u", type=str, default="", help="username")
@click.option("--expires", "-e", type=int, default=1, help="expires time in days")
@click.argument("application", nargs=1)
def refresh_token(admin, manager, username, expires, application):

    if admin:
        admin_client = Client.load_state(filename=f"{admin}.apihub")
    elif manager:
        admin_client = Client.load_state(filename=f"{manager}.apihub")
    else:
        admin_client = None
        client = Client.load_state(filename=f"{username}.apihub")

    if admin_client:
        if admin_client.token is None:
            click.echo("You need to login first")
            sys.exit(1)
        token = admin_client.refresh_application_token(application, username, expires)
        client.applications[application] = token
    else:
        if client.token is None:
            click.echo("You need to login first")
            sys.exit(1)

        client.refresh_application_token(application)
    client.save_state(filename=f"{username}.apihub")


@cli.command()
@click.option("--admin", "-a", type=str, default="", help="admin username")
def list_users(admin):
    client = Client.load_state(filename=f"{admin}.apihub")
    if client.token is None:
        click.echo("You need to login first")
        sys.exit(1)


@cli.command()
@click.option("--admin", "-a", type=str, default="", help="admin username")
@click.option(
    "--role", "-r", type=str, default="user", help="role [admin, manager, user]"
)
@click.argument("username", nargs=1)
@click.argument("password", nargs=1)
@click.argument("email", nargs=1)
def create_user(admin, role, username, password, email):
    client = Client.load_state(filename=f"{admin}.apihub")
    if client.token is None:
        click.echo("You need to login first")
        sys.exit(1)

    client.create_user(
        {
            "username": username,
            "password": password,
            "role": role,
            "email": email,
        }
    )


@cli.command()
@click.option("--admin", "-a", type=str, default="", help="admin username")
@click.option("--limit", "-l", type=int, default=1000, help="limit")
@click.option("--days", "-d", type=int, default=None, help="subscription valid days")
@click.option(
    "--recurring", "-r", type=bool, default=False, help="recurring subscription"
)
@click.argument("username", nargs=1)
@click.argument("application", nargs=1)
def create_subscription(admin, limit, days, recurring, username, application):
    client = Client.load_state(filename=f"{admin}.apihub")
    if client.token is None:
        click.echo("You need to login first")
        sys.exit(1)

    expires_at = datetime.now() + timedelta(days=days) if days else None
    client.create_subscription(
        {
            "username": username,
            "application": application,
            "starts_at": datetime.now(),
            "credit": limit,
            "expires_at": expires_at,
            "recurring": recurring,
        }
    )


@cli.command()
@click.option("--username", "-u", type=str, default="", help="username")
@click.argument("application", nargs=1)
def post_request(username, application):
    client = try_load_state(username)

    data = json.loads(sys.stdin.read())
    response = client.async_request(application, data)
    print(response)
    return

    MARKER = "# Please write body in json above"
    message = click.edit("\n\n" + MARKER)
    if message is not None:
        data = json.loads(message.split(MARKER, 1)[0])
        response = client.async_request(application, data)
        print(response)
    else:
        click.echo("input cannot be empty")
        sys.exit(1)


@cli.command()
@click.option("--username", "-u", type=str, default="", help="username")
@click.argument("application", nargs=1)
@click.argument("key", nargs=1)
def fetch_result(username, application, key):
    client = try_load_state(username)

    response = client.async_result(application, key)
    print(response)


@cli.command()
@click.option("--username", "-u", type=str, default="", help="username")
@click.argument("application", nargs=1)
def batch_request(username, application):
    client = try_load_state(username)
    for i, line in enumerate(fileinput.input(files=[])):
        data = json.loads(line)
        response = client.async_request(application, data)
        if "success" not in response or not response["success"]:
            print(f"Failed on input line {i}, request failed", file=sys.stderr)
            sys.exit(1)

        key = response["key"]

        for n in range(10):
            response = client.async_result(application, key)
            if response["success"]:
                data.updates(response["result"])
                print(json.dumps(response["result"]))
                break
            time.sleep(1)
        else:
            print(f"Failed on input line {i}, retry failed", file=sys.stderr)


if __name__ == "__main__":
    cli()
