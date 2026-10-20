import os

from dotenv import load_dotenv

load_dotenv()

# Default matches compose.yaml's dev database; compose overrides it inside containers.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://core:core@localhost:5432/core",
)
