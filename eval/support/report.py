from collections import defaultdict

from pytest import Config, Item, Session, TestReport, UsageError

REQ_MAP: defaultdict[str, set[str]] = defaultdict(set)
RESULT_MAP: dict[str, str] = {}


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
            empty_reqs.append(item.nodeid)

    if empty_reqs:
        names = "\n".join(empty_reqs)
        raise UsageError(
            f"These tests have no req marker, or one with no requirement ID:\n{names}"
        )

    print(REQ_MAP)


def pytest_runtest_logreport(report: TestReport) -> None:
    if report.nodeid not in RESULT_MAP:
        RESULT_MAP[report.nodeid] = "passed"

    if report.when == "setup" and report.outcome in ("skipped", "failed"):
        RESULT_MAP[report.nodeid] = (
            "error" if report.outcome == "failed" else report.outcome
        )
    elif report.when == "call" and report.outcome in ("skipped", "failed"):
        RESULT_MAP[report.nodeid] = report.outcome
    elif (
        report.when == "teardown"
        and report.outcome == "failed"
        and RESULT_MAP[report.nodeid] == "passed"
    ):
        RESULT_MAP[report.nodeid] = "error"

    if report.when == "teardown":
        print(RESULT_MAP)
