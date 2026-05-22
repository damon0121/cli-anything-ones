from .api import is_invalid_project_filter, is_not_found
from .errors import ApiError


PAGE_LIMIT = 100
DEFAULT_MAX_PAGES = 200
MAX_MAX_PAGES = 1000


def fetch_issue(client, config, parsed, max_pages=DEFAULT_MAX_PAGES, include_attachment_urls=False):
    warnings = []
    issue_id = parsed.issue_key
    issue = None

    try:
        issue = get_issue_detail(client, config, issue_id)
        issue_id = issue.get("id") or issue_id
    except Exception as error:
        if not is_not_found(error):
            raise
        warnings.append(
            f"Direct lookup by {parsed.issue_key} failed; searching issue list by project/type/number."
        )

    if not issue:
        list_issue = find_issue_from_list(client, config, parsed, max_pages)
        if not list_issue:
            raise ApiError(f"Could not find ONES issue {parsed.issue_key} in the issue list.")
        issue_id = list_issue["id"]
        issue = get_issue_detail(client, config, issue_id)

    comments = _settle(lambda: get_issue_comments(client, config, issue_id), [], warnings, "comments")
    attachments = _settle(
        lambda: get_issue_attachments(client, config, issue_id, max_pages),
        [],
        warnings,
        "attachments",
    )
    field_map = _settle(
        lambda: get_issue_field_map(client, config, max_pages),
        {},
        warnings,
        "issue fields",
    )

    return build_issue_report(
        parsed=parsed,
        config=config,
        issue=issue,
        issue_id=issue_id,
        comments=comments,
        attachments=attachments,
        field_map=field_map,
        warnings=warnings,
        include_attachment_urls=include_attachment_urls,
    )


def get_issue_detail(client, config, issue_id):
    response = client.request(
        f"/project/issues/{issue_id}",
        {"teamID": config.team_id},
    )
    return response.get("data") or response


def find_issue_from_list(client, config, parsed, max_pages):
    search_params_list = []
    if parsed.project_id or parsed.issue_type_id:
        search_params_list.append(
            {"projectID": parsed.project_id, "issueTypeID": parsed.issue_type_id}
        )
    if parsed.issue_type_id:
        search_params_list.append({"issueTypeID": parsed.issue_type_id})
    search_params_list.append({})

    for search_params in _unique_search_params(search_params_list):
        try:
            issue = find_issue_from_list_with_params(
                client, config, parsed, max_pages, search_params
            )
            if issue:
                return issue
        except Exception as error:
            if not is_invalid_project_filter(error):
                raise
    return None


def _unique_search_params(search_params_list):
    seen = set()
    for params in search_params_list:
        key = tuple(sorted((k, v) for k, v in params.items() if v is not None))
        if key in seen:
            continue
        seen.add(key)
        yield params


def find_issue_from_list_with_params(client, config, parsed, max_pages, search_params):
    cursor = None
    seen_cursors = set()

    for _page in range(max_pages):
        response = client.request(
            "/project/issues",
            {
                "teamID": config.team_id,
                **search_params,
                "limit": PAGE_LIMIT,
                "cursor": cursor,
            },
        )
        item_list = response.get("data", {}).get("list", [])
        for item in item_list:
            if _matches_issue(item, parsed, search_params):
                return item

        page_info = response.get("data", {}).get("pageInfo", {})
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
        if not next_cursor:
            return None
        if next_cursor in seen_cursors:
            raise ApiError("ONES API returned a repeated issue-list cursor.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise ApiError(f"Issue-list pagination exceeded {max_pages} pages.")


def get_issue_comments(client, config, issue_id):
    response = client.request(
        f"/project/issues/{issue_id}/comments",
        {"teamID": config.team_id},
    )
    return _data_list(response)


def get_issue_attachments(client, config, issue_id, max_pages):
    attachments = []
    cursor = None
    seen_cursors = set()

    for _page in range(max_pages):
        response = client.request(
            f"/project/issues/{issue_id}/attachments",
            {"teamID": config.team_id, "limit": PAGE_LIMIT, "cursor": cursor},
        )
        attachments.extend(_data_list(response))
        page_info = response.get("data", {}).get("pageInfo", {})
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
        if not next_cursor:
            return attachments
        if next_cursor in seen_cursors:
            raise ApiError("ONES API returned a repeated attachment cursor.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise ApiError(f"Attachment pagination exceeded {max_pages} pages.")


def get_issue_field_map(client, config, max_pages):
    fields = []
    cursor = None
    seen_cursors = set()

    for _page in range(max_pages):
        response = client.request(
            "/project/issueFields",
            {"teamID": config.team_id, "limit": 500, "cursor": cursor},
        )
        fields.extend(_data_list(response))
        page_info = response.get("data", {}).get("pageInfo", {})
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
        if not next_cursor:
            return {field.get("id"): field for field in fields}
        if next_cursor in seen_cursors:
            raise ApiError("ONES API returned a repeated issue-field cursor.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise ApiError(f"Issue-field pagination exceeded {max_pages} pages.")


def _settle(callback, fallback, warnings, label):
    try:
        return callback()
    except Exception as error:
        warnings.append(f"Failed to fetch {label}: {error}")
        return fallback


def _matches_issue(item, parsed, search_params):
    if item.get("id") == parsed.issue_key:
        return True
    if parsed.issue_number is None or item.get("number") != parsed.issue_number:
        return False

    if parsed.issue_type_id:
        item_issue_type_id = (item.get("issueType") or {}).get("id")
        if item_issue_type_id != parsed.issue_type_id:
            return False
        return True

    if search_params.get("projectID"):
        return True

    return False


def _data_list(response):
    data = response.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("list", [])
    return []


def build_issue_report(
    parsed,
    config,
    issue,
    issue_id,
    comments,
    attachments,
    field_map,
    warnings,
    include_attachment_urls,
):
    custom_fields = []
    for field_value in issue.get("fieldValues", []):
        field = field_map.get(field_value.get("fieldID"), {})
        value = field_value.get("value")
        custom_fields.append(
            {
                "id": field_value.get("fieldID"),
                "name": field.get("name") or field_value.get("fieldID"),
                "type": field.get("typeLabel") or field_value.get("type"),
                "value": value,
                "text": stringify_value(value),
            }
        )

    return {
        "source": {
            "baseURL": config.base_url,
            "teamID": config.team_id,
            "projectID": parsed.project_id,
            "issueTypeID": parsed.issue_type_id,
            "issueKey": parsed.issue_key,
            "issueID": issue_id,
        },
        "issue": {
            "id": issue.get("id"),
            "key": parsed.issue_key,
            "title": issue.get("title"),
            "number": issue.get("number"),
            "descriptionText": issue.get("descriptionText") or html_to_text(issue.get("description") or ""),
            "description": issue.get("description"),
            "status": pick_named_value(issue.get("status")),
            "priority": pick_named_value(issue.get("priority")),
            "severityLevel": pick_named_value(issue.get("severityLevel")),
            "defectType": pick_named_value(issue.get("defectType")),
            "assignee": pick_named_value(issue.get("assignee")),
            "creator": pick_named_value(issue.get("creator")),
            "project": pick_named_value(issue.get("project")),
            "sprint": pick_named_value(issue.get("sprint")),
            "issueType": pick_named_value(issue.get("issueType")),
            "createTime": issue.get("createTime"),
            "dueDate": issue.get("dueDate"),
            "customFields": custom_fields,
            "attachments": [
                normalize_attachment(attachment, include_attachment_urls)
                for attachment in attachments
            ],
            "comments": [normalize_comment(comment) for comment in comments],
        },
        "warnings": warnings,
    }


def pick_named_value(value):
    if not isinstance(value, dict):
        return value
    return {"id": value.get("id"), "name": value.get("name") or value.get("value") or value.get("title")}


def normalize_comment(comment):
    return {
        "id": comment.get("id"),
        "createTime": comment.get("createTime"),
        "owner": pick_named_value(comment.get("owner")),
        "text": comment.get("text"),
    }


def normalize_attachment(attachment, include_attachment_url):
    normalized = {
        "id": attachment.get("id"),
        "name": attachment.get("name"),
        "createTime": attachment.get("createTime"),
        "creator": pick_named_value(attachment.get("creator")),
        "mime": attachment.get("mime"),
        "sizeByte": attachment.get("sizeByte"),
        "description": attachment.get("description"),
    }
    if include_attachment_url:
        normalized["tempURL"] = attachment.get("tempURL")
    return normalized


def stringify_value(value):
    if value is None or value == "":
        return ""
    if isinstance(value, list):
        return ", ".join(filter(None, (stringify_value(item) for item in value)))
    if isinstance(value, dict):
        for key in ("name", "value", "title", "text", "id"):
            if key in value:
                return stringify_value(value[key])
        return str(value)
    return str(value)


def html_to_text(value):
    import html
    import re

    text = re.sub(r"<\s*br\s*/?>", "\n", value, flags=re.I)
    text = re.sub(r"</(p|div|li|h[1-6])\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_max_pages(value: int) -> int:
    if value <= 0:
        raise ValueError("Expected a positive integer.")
    if value > MAX_MAX_PAGES:
        raise ValueError(f"Expected a value <= {MAX_MAX_PAGES}.")
    return value
