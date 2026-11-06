from collections.abc import Iterator

import httpx
import pytest
from lxml import etree  # ty: ignore

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


@pytest.fixture(scope="session")
def du_schema(config: settings.Settings) -> etree.XMLSchema:
    """The DU wrapper. It's licensed, so a missing copy skips what needs it."""
    if not config.schema_path.is_file():
        pytest.skip(f"no DU schema at {config.schema_path}; run `just stage-schema`")
    return etree.XMLSchema(etree.parse(str(config.schema_path), PARSER))
