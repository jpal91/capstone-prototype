from collections import defaultdict

from pytest import Config, Item, Session, UsageError

REQ_MAP: defaultdict[str, set[str]] = defaultdict(set)


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", "req(*names): The requirement to test against")


def pytest_collection_modifyitems(
    session: Session, config: Config, items: list[Item]
) -> None:
    empty_reqs = []

    for item in items:
        nodeid = item.nodeid
        for mark in item.iter_markers("req"):
            for arg in mark.args:
                REQ_MAP[nodeid].add(arg)

        if nodeid not in REQ_MAP:
            empty_reqs.append(f"{item.path.name}::{item.name}")

    if empty_reqs:
        names = "\n".join(empty_reqs)
        raise UsageError(
            f"These tests have no req marker, or one with no requirement ID:\n{names}"
        )

    print(REQ_MAP)
