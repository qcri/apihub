import sys
import json
import time
import asyncio
import fileinput
from datetime import datetime, timedelta

try:
    import typer
except ImportError:
    sys.stderr.write('Please install "apihub[cli] to install cli option"')
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

from apihub.client import Client
from .subscription.schemas import SubscriptionIn


cli = typer.Typer()


def try_load_state(username):
    client = Client.load_state(filename=f"{username}.apihub")
    if client.token is None:
        typer.echo("You need to login first")
        sys.exit(1)
    return client


@cli.command()
def login(username: str, password: str, endpoint: str = "http://localhost:5000"):
    client = Client({"endpoint": endpoint})
    client.authenticate(username=username, password=password)
    client.save_state(filename=f"{username}.apihub")


@cli.command()
def refresh_token(
    application: str,
    admin: str = "",
    manager: str = "",
    username: str = "",
    expires: int = 1,
):
    if admin:
        admin_client = Client.load_state(filename=f"{admin}.apihub")
    elif manager:
        admin_client = Client.load_state(filename=f"{manager}.apihub")
    else:
        admin_client = None
        client = Client.load_state(filename=f"{username}.apihub")

    if admin_client:
        if admin_client.token is None:
            cli.echo("You need to login first")
            sys.exit(1)
        token = admin_client.refresh_application_token(application, username, expires)
        client.applications[application] = token
    else:
        if client.token is None:
            cli.echo("You need to login first")
            sys.exit(1)

        client.refresh_application_token(application, username, expires)
    client.save_state(filename=f"{username}.apihub")


@cli.command()
def list_users(role: str, admin: str = ""):
    client = Client.load_state(filename=f"{admin}.apihub")
    if client.token is None:
        cli.echo("You need to login first")
        sys.exit(1)

    users = client.get_users_by_role(role)
    for user in users:
        print(user)


@cli.command()
def create_user(
    username: str, password: str, email: str, admin: str = "", role: str = "user"
):
    client = Client.load_state(filename=f"{admin}.apihub")
    if client.token is None:
        cli.echo("You need to login first")
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
def create_subscription(
    username: str,
    application: str,
    admin: str = "",
    limit: int = 1000,
    days: int = 0,
    recurring: bool = False,
):
    client = Client.load_state(filename=f"{admin}.apihub")
    if client.token is None:
        cli.echo("You need to login first")
        sys.exit(1)

    expires_at = datetime.now() + timedelta(days=days) if days else None
    client.create_subscription(
        SubscriptionIn(
            username=username,
            application=application,
            starts_at=datetime.now(),
            expires_at=expires_at,
            recurring=recurring,
        )
    )


@cli.command()
def post_request(application: str, username: str):
    client = try_load_state(username)

    data = json.loads(sys.stdin.read())
    response = client.async_request(application, data)
    print(response)
    return

    MARKER = "# Please write body in json above"
    message = cli.edit("\n\n" + MARKER)
    if message is not None:
        data = json.loads(message.split(MARKER, 1)[0])
        response = client.async_request(application, data)
        print(response)
    else:
        cli.echo("input cannot be empty")
        sys.exit(1)


@cli.command()
def fetch_result(application: str, key: str, username: str = ""):
    client = try_load_state(username)

    response = client.async_result(application, key)
    print(response)


@cli.command()
def batch_request(
    username: str, application: str, filename: str = "", parallel: int = 10
):
    jobs = []
    client = try_load_state(username)
    files = [filename] if filename else []
    for i, line in enumerate(fileinput.input(files=files)):
        data = json.loads(line)
        response = client.async_request(application, data)
        if "success" not in response or not response["success"]:
            print(f"Failed on input line {i}, request failed", file=sys.stderr)
            print(response)
            sys.exit(1)

        key = response["key"]
        if len(jobs) < parallel:
            jobs.append((i, data, key))
        else:
            unfinished_jobs = []
            for i, data, key in jobs:
                response = client.async_result(application, key)
                if "success" in response and response["success"]:
                    data.update(response["result"])
                    print(i, json.dumps(response["result"]))
                else:
                    print(i, response)
                    unfinished_jobs.append((i, data, key))

            jobs = unfinished_jobs

            time.sleep(1)

    while len(jobs) > 0:
        unfinished_jobs = []
        for i, data, key in jobs:
            response = client.async_result(application, key)
            if "success" in response and response["success"]:
                data.update(response["result"])
                print(i, json.dumps(response["result"]))
            else:
                print(i, response)
                unfinished_jobs.append((i, data, key))

        jobs = unfinished_jobs


@cli.command()
def batch_sync_request(
    username: str, application: str, filename: str = "", parallel: int = 10
):
    queue = asyncio.Queue()

    async def request_routine(client, application, data):
        response = await client.sync_request(application, data)
        if "success" in response and response["success"]:
            data.update(response["result"])
            print(i, json.dumps(response["result"]))
        else:
            print(i, response)

    client = try_load_state(username)
    files = [filename] if filename else []
    for i, line in enumerate(fileinput.input(files=files)):
        data = json.loads(line)

        queue.put(request_routine(client, application, data))
        time.sleep(1)


if __name__ == "__main__":
    cli()
