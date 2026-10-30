"""Where the services are and the demo credentials, from the environment.

URLs default to the ports compose publishes on localhost, for running the
suite natively; the eval service in compose.yml points them at the service
names. Credentials have no defaults here: compose.yml is their one source.
"""

import os
from dataclasses import dataclass

# username -> environment variable holding the password (as in core-seed)
BORROWERS = {
    "alice": "ALICE_PASSWORD",
    "bob": "BOB_PASSWORD",
}

# client_id -> (name core shows borrowers, environment variable holding the
# client secret), as in core-seed
LENDERS = {
    "lender-a": ("Lender A", "LENDER_A_SECRET"),
    "lender-b": ("Lender B", "LENDER_B_SECRET"),
    "lender-c": ("Lender C", "LENDER_C_SECRET"),
}


class MissingSettings(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    core_url: str
    mock_lender_url: str
    passwords: dict[str, str]
    secrets: dict[str, str]


def load() -> Settings:
    required = [*BORROWERS.values(), *(var for _, var in LENDERS.values())]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        raise MissingSettings(
            f"eval: missing {', '.join(missing)}. "
            "compose.yml sets demo values; when running natively, export them."
        )

    return Settings(
        core_url=os.environ.get("CORE_URL", "http://localhost:8000"),
        mock_lender_url=os.environ.get("MOCK_LENDER_URL", "http://localhost:3001"),
        passwords={user: os.environ[var] for user, var in BORROWERS.items()},
        secrets={client_id: os.environ[var] for client_id, (_, var) in LENDERS.items()},
    )
