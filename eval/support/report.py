import json
import os
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, Literal

from pytest import (
    Config,
    ExitCode,
    Item,
    Parser,
    Session,
    TestReport,
    UsageError,
)

DEFAULT_REQUIREMENTS = Path(__file__).parents[2] / "docs" / "requirements.md"
RESULTS_DIRECTORY = Path(__file__).parents[1] / "results"
REQUIREMENTS_PATH = Path(os.getenv("REQUIREMENTS_PATH", DEFAULT_REQUIREMENTS))
MARKER_MAP: defaultdict[str, set[str]] = defaultdict(set)
REQ_MAP: dict[str, "Requirement"] = {}
RESULT_MAP: dict[str, "Outcome"] = {}


class Outcome(IntEnum):
    FAILED = 1
    ERROR = 2
    SKIPPED = 3
    PASSED = 4

    def __str__(self):
        return self.name.lower()

    @staticmethod
    def from_str(item: Literal["failed", "error", "skipped", "passed"]) -> "Outcome":
        return Outcome[item.upper()]


class CombinedResults:
    def __init__(self):
        self.outcomes: dict[str, Outcome] = {}

    def add_result(self, test_id: str, outcome: Outcome):
        self.outcomes[test_id] = outcome

    @property
    def overall_result(self) -> str:
        return str(min(self.outcomes.values())) if self.outcomes else "not tested"


@dataclass
class Requirement:
    rid: str
    req_text: str
    verification: str
    table: str


def parse_requirements(text: str) -> dict[str, Requirement]:
    row_map = {}
    headers: list[str] = []

    for line in text.splitlines():
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


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--report",
        action="store_true",
        help="write results/results.md/results.json",
    )


def pytest_configure(config: Config) -> None:
    try:
        global REQ_MAP
        REQ_MAP = parse_requirements(REQUIREMENTS_PATH.read_text())
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


def pytest_runtest_logreport(report: TestReport) -> None:
    if report.nodeid not in RESULT_MAP:
        RESULT_MAP[report.nodeid] = Outcome.PASSED

    if report.when == "setup" and report.outcome in ("skipped", "failed"):
        RESULT_MAP[report.nodeid] = (
            Outcome.ERROR
            if report.outcome == "failed"
            else Outcome.from_str(report.outcome)
        )
    elif report.when == "call" and report.outcome in ("skipped", "failed"):
        RESULT_MAP[report.nodeid] = Outcome.from_str(report.outcome)
    elif (
        report.when == "teardown"
        and report.outcome == "failed"
        and RESULT_MAP[report.nodeid] == Outcome.PASSED
    ):
        RESULT_MAP[report.nodeid] = Outcome.ERROR


def combined_results(
    req_map: dict[str, Requirement],
    res_map: dict[str, Outcome],
    mark_map: dict[str, set[str]],
) -> dict[str, CombinedResults]:
    req_results = {key: CombinedResults() for key in req_map}

    for nid, result in res_map.items():
        markers = mark_map[nid]

        for marker in markers:
            req_results[marker].add_result(nid, result)

    return req_results


def generate_json_report(
    req_map: dict[str, Requirement],
    comb_results: dict[str, CombinedResults],
    res_map: dict[str, Outcome],
    marker_map: dict[str, set[str]],
    exit_status: int,
) -> dict[str, Any]:
    json_out = {
        "testTimestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "totalTestsRun": 0,
        "totalTestsPassed": 0,
        "totalTestsFailed": 0,
        "totalTestsSkipped": 0,
        "totalTestsError": 0,
        "exitStatus": exit_status,
        "tests": [],
    }
    table_mapping = {}

    for req in req_map.values():
        if req.table not in table_mapping:
            table_mapping[req.table] = []

        results = comb_results[req.rid]

        row = {
            "requirementId": req.rid,
            "description": req.req_text,
            "totalNumberOfTests": len(results.outcomes),
            "totalTestsPassed": len(
                [r for r in results.outcomes.values() if r == Outcome.PASSED]
            ),
            "overallResult": results.overall_result,
            "verification": req.verification,
        }

        table_mapping[req.table].append(row)

    for outcome in res_map.values():
        json_out["totalTestsRun"] += 1

        match outcome:
            case Outcome.PASSED:
                json_out["totalTestsPassed"] += 1
            case Outcome.FAILED:
                json_out["totalTestsFailed"] += 1
            case Outcome.ERROR:
                json_out["totalTestsError"] += 1
            case Outcome.SKIPPED:
                json_out["totalTestsSkipped"] += 1

    for name, out in res_map.items():
        json_out["tests"].append(
            {
                "testid": name,
                "outcome": str(out),
                "requirements": sorted(marker_map[name]),
            }
        )

    json_out["tables"] = table_mapping
    return json_out


def generate_table(table: str, rows: list[dict[str, Any]]) -> str:
    out = ""
    match table:
        case "FR":
            out += "### Functional Requirements\n\n"
        case "NFR":
            out += "### Non-functional and Security Requirements\n\n"
        case "L":
            out += "### Known Limitations to Demonstrate\n\n*A result of `passed` means the limitation was demonstrated*\n\n"

    out += "| ID | Result | Tests passed | "
    if table == "L":
        out += "Limitation |\n"
    else:
        out += "Requirement |\n"

    out += "|---|---|---|---|\n"

    for row in rows:
        tests_n = row["totalNumberOfTests"]
        passed = row["totalTestsPassed"]
        desc = textwrap.shorten(row["description"], 80, placeholder="...")

        out += f"| {row['requirementId']} | {row['overallResult']} | {passed}/{tests_n} | {desc} |\n"

    out += "\n"

    return out


def generate_md_report(json_out: dict[str, Any]) -> str:
    out = "# Results\n\n"
    total = json_out["totalTestsRun"]
    passed = json_out["totalTestsPassed"]
    skipped = json_out["totalTestsSkipped"]
    error = json_out["totalTestsError"]
    failed = json_out["totalTestsFailed"]

    out += f"Run {json_out['testTimestamp']}. {total} tests: {passed} passed, {failed} failed, {skipped} skipped, {error} errors.\n\n"

    out += "## Results by table\n\n"

    for table, rows in json_out["tables"].items():
        out += generate_table(table, rows)

    no_pass = [t for t in json_out["tests"] if t["outcome"] != "passed"]

    out += "## Tests that did not pass\n\n"

    if no_pass:
        for test in no_pass:
            markers = ", ".join(test["requirements"])
            out += f"- `{test['testid']}`: {test['outcome']} ({markers})\n"
    else:
        out += "None\n"

    out += "\n## Not tested by `eval/`\n\n| ID | Intended Check |\n|---|---|\n"

    for trows in json_out["tables"].values():
        for row in trows:
            if row["overallResult"] != "not tested":
                continue

            out += f"| {row['requirementId']} | {row['verification']} |\n"

    return out


def pytest_sessionfinish(session: Session, exitstatus: int) -> None:
    report_flag: bool = session.config.getoption("report")

    if not report_flag or exitstatus not in (ExitCode.OK, ExitCode.TESTS_FAILED):
        return

    comb_results = combined_results(REQ_MAP, RESULT_MAP, MARKER_MAP)
    json_out = generate_json_report(
        REQ_MAP, comb_results, RESULT_MAP, MARKER_MAP, exitstatus
    )

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with open(RESULTS_DIRECTORY / "results.json", "w") as f:
        json.dump(json_out, f, indent=2)

    md_results = generate_md_report(json_out)

    with open(RESULTS_DIRECTORY / "results.md", "w") as f:
        f.write(md_results)
