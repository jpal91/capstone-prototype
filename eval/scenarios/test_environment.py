"""NFR-07: the suite runs in the same environment as the system.

This is weak evidence, and it can't be much stronger. From inside the run, a test
can see that it's in a container and reached the services by the names only the
compose network resolves. It can't see how the stack was started, whether the
host needed anything but Docker, or that `docker compose down -v` removes it.
What shows those is doing it: `just eval-fresh`, reported in the paper's Ch. 8.
"""

from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from support.settings import Settings


@pytest.mark.req("NFR-07")
def test_runs_in_a_container_on_the_compose_network(config: Settings):
    if not Path("/.dockerenv").exists():
        pytest.skip("running natively, so this run says nothing about compose")

    assert urlsplit(config.core_url).hostname == "core"
    assert urlsplit(config.mock_lender_url).hostname == "mock-lender"
    assert httpx.get(f"{config.core_url}/health").status_code == 200
    assert httpx.get(f"{config.mock_lender_url}/").status_code == 200
