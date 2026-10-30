import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pytest import Config, Item, Session, TestReport, UsageError

DEFAULT_REQUIREMENTS = Path(__file__).parents[2] / "docs" / "requirements.md"
REQUIREMENTS_PATH = Path(os.getenv("REQUIREMENTS_PATH", DEFAULT_REQUIREMENTS))
MARKER_MAP: defaultdict[str, set[str]] = defaultdict(set)
REQ_MAP: dict[str, "Requirement"] = {}
RESULT_MAP: dict[str, str] = {}


@dataclass
class Requirement:
    rid: str
    req_text: str
    verification: str
    table: str


def pytest_configure(config: Config) -> None:
    try:
        with open(REQUIREMENTS_PATH) as f:
            global REQ_MAP
            REQ_MAP = parse_requirements(f.read())
    except FileNotFoundError:
        raise UsageError(
            f"requirements file not found: {REQUIREMENTS_PATH} (set REQUIREMENTS_PATH)"
        )
    config.addinivalue_line("markers", "req(*names): The requirement to test against")


def pytest_collection_modifyitems(
    session: Session, config: Config, items: list[Item]
) -> None:
    bad_reqs = []

    for item in items:
        nodeid = item.nodeid
        for mark in item.iter_markers("req"):
            for arg in mark.args:
                if arg not in REQ_MAP:
                    bad_reqs.append((nodeid, f"{arg} is not an ID in requirements.md"))
                MARKER_MAP[nodeid].add(arg)

        if nodeid not in MARKER_MAP:
            bad_reqs.append((nodeid, "missing or empty marker"))

    if bad_reqs:
        tests = "\n".join([f"{a} - {b}" for a, b in bad_reqs])
        raise UsageError(f"These tests have improperly set up `req` markers:\n{tests}")

    print(MARKER_MAP)


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


def parse_requirements(lines: str) -> dict[str, Requirement]:
    row_map = {}
    headers: list[str] = []

    for line in lines.splitlines():
        if not headers and line.startswith("|"):
            headers = [l.strip() for l in line.split("|")[1:-1]]
            continue
        elif not headers or line.startswith("|-"):
            continue
        elif not line.startswith("|"):
            headers = []
            continue

        row_items = [l.strip() for l in line.split("|")[1:-1]]
        row_dict = dict(zip(headers, row_items))

        row = Requirement(
            rid=row_dict["ID"],
            req_text=row_dict.get("Requirement") or row_dict["Limitation"],
            verification=row_dict.get("Verified by") or row_dict["Shown by"],
            table=row_dict["ID"].partition("-")[0],
        )

        row_map[row.rid] = row

    return row_map
