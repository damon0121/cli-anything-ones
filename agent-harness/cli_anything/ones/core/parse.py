import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .errors import UsageError


@dataclass(frozen=True)
class ParsedIssueUrl:
    origin: str
    host: str
    team_id: str | None
    project_id: str | None
    component_id: str | None
    sprint_id: str | None
    issue_type_id: str | None
    issue_key: str
    issue_number: int | None
    project_key: str | None

    def to_dict(self):
        return {
            "origin": self.origin,
            "host": self.host,
            "teamID": self.team_id,
            "projectID": self.project_id,
            "componentID": self.component_id,
            "sprintID": self.sprint_id,
            "issueTypeID": self.issue_type_id,
            "issueKey": self.issue_key,
            "issueNumber": self.issue_number,
            "projectKey": self.project_key,
        }


def parse_ones_issue_url(value: str) -> ParsedIssueUrl:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise UsageError(f"Invalid ONES issue URL: {value}")

    hash_path = parsed.fragment[1:] if parsed.fragment.startswith("/") else parsed.fragment
    candidate_path = hash_path or parsed.path
    segments = [segment for segment in candidate_path.split("/") if segment]
    issue_key = _value_after(segments, "issue")
    project_id = _value_after(segments, "project")

    if not issue_key:
        raise UsageError(
            "Could not find issue key in URL. Expected a segment like /issue/JHWX-10218."
        )

    issue_number_match = re.search(r"-(\d+)$", issue_key)
    issue_number = int(issue_number_match.group(1)) if issue_number_match else None
    project_key = (
        issue_key[: -len(issue_number_match.group(1)) - 1]
        if issue_number_match
        else project_id
    )

    return ParsedIssueUrl(
        origin=f"{parsed.scheme}://{parsed.netloc}",
        host=parsed.netloc,
        team_id=_value_after(segments, "team"),
        project_id=project_id,
        component_id=_value_after(segments, "component"),
        sprint_id=_value_after(segments, "sprint"),
        issue_type_id=_value_after(segments, "issue_type"),
        issue_key=issue_key,
        issue_number=issue_number,
        project_key=project_key,
    )


def _value_after(segments, name):
    try:
        index = segments.index(name)
    except ValueError:
        return None
    next_index = index + 1
    return segments[next_index] if next_index < len(segments) else None
