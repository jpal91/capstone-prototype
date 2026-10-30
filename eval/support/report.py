from pytest import Config


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", "req(*names): The requirement to test against")
