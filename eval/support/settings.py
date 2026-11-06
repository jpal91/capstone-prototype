"""Where the services are and the demo credentials, from the environment.

URLs default to the ports compose publishes on localhost, for running the
suite natively; the eval service in compose.yml points them at the service
names. Credentials have no defaults here: compose.yml is their one source. The
exception is core's database URL, whose dev default core/settings.py also has.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# The audit checks read core's database directly, as core's own role (L-06).
DEFAULT_CORE_DATABASE = "postgresql://core:core@localhost:5432/core"

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

# The licensed DU wrapper, staged by `just stage-schema`. Not in the repository.
DEFAULT_SCHEMA = (
    Path(__file__).parents[2]
    / "mismo"
    / "schema"
    / "staged"
    / "DU_Wrapper_3.4.0_B324.xsd"
)


class MissingSettings(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    core_url: str
    mock_lender_url: str
    schema_path: Path
    core_database_url: str
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
        schema_path=Path(os.environ.get("MISMO_SCHEMA", DEFAULT_SCHEMA)),
        core_database_url=os.environ.get("CORE_DATABASE_URL", DEFAULT_CORE_DATABASE),
        passwords={user: os.environ[var] for user, var in BORROWERS.items()},
        secrets={client_id: os.environ[var] for client_id, (_, var) in LENDERS.items()},
    )
