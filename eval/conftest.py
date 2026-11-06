from collections.abc import Iterator

import httpx
import psycopg
import pytest
from lxml import etree  # ty: ignore
from psycopg.rows import dict_row

from support import settings
from support.clients import (
    BorrowerClient,
    LenderClient,
    core_client,
    mock_lender_client,
)
from support.xml import PARSER

pytest_plugins = ["support.report"]


@pytest.fixture(scope="session")
def config() -> settings.Settings:
    try:
        return settings.load()
    except settings.MissingSettings as e:
        pytest.exit(str(e), returncode=3)


@pytest.fixture(scope="session", autouse=True)
def services_up(config: settings.Settings) -> None:
    """Stop the run with one clear message if the stack isn't up."""
    checks = {
        "core": f"{config.core_url}/health",
        "mock-lender": f"{config.mock_lender_url}/",
    }
    for name, url in checks.items():
        try:
            httpx.get(url, timeout=5).raise_for_status()
        except httpx.HTTPError as e:
            pytest.exit(f"eval: {name} is not reachable at {url} ({e})", returncode=3)


@pytest.fixture(scope="session")
def anon(config: settings.Settings) -> Iterator[httpx.Client]:
    with core_client(config.core_url) as client:
        yield client


def _borrower(config: settings.Settings, username: str) -> Iterator[BorrowerClient]:
    # Already open (it logged in), so not a `with` block.
    client = BorrowerClient(config.core_url, username, config.passwords[username])
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="session")
def alice(config: settings.Settings) -> Iterator[BorrowerClient]:
    yield from _borrower(config, "alice")


@pytest.fixture(scope="session")
def bob(config: settings.Settings) -> Iterator[BorrowerClient]:
    yield from _borrower(config, "bob")


def _lender(config: settings.Settings, client_id: str) -> Iterator[LenderClient]:
    with LenderClient(config.core_url, client_id, config.secrets[client_id]) as client:
        yield client


@pytest.fixture(scope="session")
def lender_a(config: settings.Settings) -> Iterator[LenderClient]:
    yield from _lender(config, "lender-a")


@pytest.fixture(scope="session")
def lender_b(config: settings.Settings) -> Iterator[LenderClient]:
    yield from _lender(config, "lender-b")


@pytest.fixture(scope="session")
def lender_c(config: settings.Settings) -> Iterator[LenderClient]:
    yield from _lender(config, "lender-c")


@pytest.fixture(scope="session")
def mock_lender(config: settings.Settings) -> Iterator[httpx.Client]:
    with mock_lender_client(config.mock_lender_url) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def du_schema(config: settings.Settings) -> etree.XMLSchema:
    """The DU wrapper. FR-03 can't be shown without it, so stop the run if missing."""
    if not config.schema_path.is_file():
        pytest.exit(
            f"eval: no DU schema at {config.schema_path}; run `just stage-schema`",
            returncode=3,
        )
    return etree.XMLSchema(etree.parse(str(config.schema_path), PARSER))


@pytest.fixture(scope="session", autouse=True)
def core_db(config: settings.Settings) -> Iterator[psycopg.Connection]:
    """A connection to core's database. Stops the run if it can't be reached.

    The lock timeout stops a test hanging if it holds a lock core is waiting on.
    """
    try:
        connection = psycopg.connect(
            config.core_database_url, row_factory=dict_row, options="-c lock_timeout=5s"
        )
    except psycopg.OperationalError as e:
        pytest.exit(f"eval: core's database is not reachable ({e})", returncode=3)
    with connection:
        yield connection


@pytest.fixture
def db(core_db: psycopg.Connection) -> Iterator[psycopg.Connection]:
    """core's database, with everything the test did rolled back afterward.

    A test must not call core while it holds changes here: they aren't committed,
    and core could end up waiting on the same locks.
    """
    try:
        yield core_db
    finally:
        core_db.rollback()
