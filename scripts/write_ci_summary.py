"""Summarize the pytest phases from their JUnit reports in GitHub Actions."""
import os
from pathlib import Path
from xml.etree import ElementTree


def phase_row(label, outcome, report):
    outcome = outcome or "not run"
    try:
        suite = ElementTree.parse(report).getroot().find("testsuite")
        if suite is None:
            raise ValueError("missing testsuite")
        tests, failed, errors, skipped = (int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped"))
        passed = tests - failed - errors - skipped
        duration = float(suite.attrib["time"])
    except (OSError, ElementTree.ParseError, ValueError, KeyError):
        return f"| {label} | {outcome} | — | — | — | — | — |"
    return f"| {label} | {outcome} | {passed} | {failed} | {errors} | {skipped} | {duration:.2f} s |"


def main():
    mode = os.environ["SUITE"]
    tests_commit = os.getenv("TESTS_COMMIT") or os.getenv("GITHUB_SHA", "unavailable")
    api_commit = os.getenv("API_COMMIT") or "unavailable"
    stand = os.getenv("STAND_OUTCOME") or "not run"
    lines = [
        f"## API tests · {mode}", "",
        f"- Tests commit `{tests_commit}`",
        f"- API commit `{api_commit}`",
        f"- Test stand `{stand}`", "",
        "| Phase | CI status | Passed | Failed | Errors | Skipped | Pytest time |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        phase_row("Smoke" if mode == "smoke" else "Main regression",
                  os.getenv("REGRESSION_OUTCOME"), "artifacts/junit.xml"),
    ]
    if mode == "full":
        lines.append(phase_row("Last active administrator", os.getenv("LAST_ADMIN_OUTCOME"),
                               "artifacts/junit-last-admin.xml"))
    artifact_url = os.getenv("ARTIFACT_URL")
    if artifact_url:
        lines.extend(["", f"[Download run artifacts]({artifact_url})"])
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
        summary.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
