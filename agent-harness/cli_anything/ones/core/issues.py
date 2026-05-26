from .api import is_invalid_project_filter, is_not_found
from .errors import ApiError


PAGE_LIMIT = 100
DEFAULT_ISSUE_LIST_LIMIT = 100
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


def fetch_issue_list(
    client,
    config,
    parsed,
    project_id=None,
    component_id=None,
    sprint_id=None,
    issue_type_id=None,
    assignee_id=None,
    exclude_statuses=None,
    limit=DEFAULT_ISSUE_LIST_LIMIT,
    max_pages=DEFAULT_MAX_PAGES,
):
    project_id = project_id if project_id is not None else parsed.project_id
    component_id = component_id if component_id is not None else parsed.component_id
    sprint_id = sprint_id if sprint_id is not None else parsed.sprint_id
    issue_type_id = issue_type_id if issue_type_id is not None else parsed.issue_type_id
    search_params = {
        "projectID": project_id,
        "componentID": component_id,
        "sprintID": sprint_id,
        "issueTypeID": issue_type_id,
    }
    assignee_id = _normalize_filter_value(assignee_id)
    exclude_statuses = _normalize_status_filter_values(exclude_statuses)

    try:
        return fetch_issue_list_with_params(
            client,
            config,
            parsed,
            search_params,
            assignee_id,
            exclude_statuses,
            limit,
            max_pages,
        )
    except Exception as error:
        if not is_invalid_project_filter(error) or not project_id:
            raise

    search_params["projectID"] = None
    report = fetch_issue_list_with_params(
        client,
        config,
        parsed,
        search_params,
        assignee_id,
        exclude_statuses,
        limit,
        max_pages,
    )
    report["warnings"].append(
        f"Dropped projectID filter {project_id} because ONES rejected it as invalid."
    )
    return report


def fetch_issue_list_with_params(
    client,
    config,
    parsed,
    search_params,
    assignee_id,
    exclude_statuses,
    limit,
    max_pages,
):
    issues = []
    cursor = None
    seen_cursors = set()

    for _page in range(max_pages):
        remaining = limit - len(issues)
        if remaining <= 0:
            return build_issue_list_report(
                parsed, config, search_params, assignee_id, issues, has_more=True
            )

        response = client.request(
            "/project/issues",
            {
                "teamID": config.team_id,
                **search_params,
                "limit": _issue_list_page_limit(
                    search_params,
                    assignee_id,
                    exclude_statuses,
                    remaining,
                ),
                "cursor": cursor,
            },
        )
        item_list = _data_list(response)
        matching_items = [
            item
            for item in item_list
            if _matches_issue_list_filters(
                item,
                search_params,
                assignee_id,
                exclude_statuses,
            )
        ]
        issues.extend(
            normalize_issue_summary(item, parsed, search_params.get("projectID"))
            for item in matching_items[:remaining]
        )

        page_info = _page_info(response)
        next_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
        if len(issues) >= limit:
            return build_issue_list_report(
                parsed,
                config,
                search_params,
                assignee_id,
                issues,
                has_more=bool(next_cursor) or len(matching_items) > remaining,
            )
        if not next_cursor:
            return build_issue_list_report(
                parsed, config, search_params, assignee_id, issues, has_more=False
            )
        if next_cursor in seen_cursors:
            raise ApiError("ONES API returned a repeated issue-list cursor.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise ApiError(f"Issue-list pagination exceeded {max_pages} pages.")


def _issue_list_page_limit(search_params, assignee_id, exclude_statuses, remaining):
    if (
        search_params.get("componentID")
        or search_params.get("sprintID")
        or assignee_id
        or exclude_statuses
    ):
        return PAGE_LIMIT
    return min(PAGE_LIMIT, remaining)


def _matches_issue_list_filters(item, search_params, assignee_id, exclude_statuses):
    project_id = search_params.get("projectID")
    if project_id and _nested_id(item, "project") and _nested_id(item, "project") != project_id:
        return False

    component_id = search_params.get("componentID")
    item_component_id = _nested_id(item, "component") or item.get("componentID")
    if component_id and item_component_id and item_component_id != component_id:
        return False

    sprint_id = search_params.get("sprintID")
    if sprint_id and _nested_id(item, "sprint") and _nested_id(item, "sprint") != sprint_id:
        return False

    issue_type_id = search_params.get("issueTypeID")
    if issue_type_id and _nested_id(item, "issueType") and _nested_id(item, "issueType") != issue_type_id:
        return False

    if assignee_id and _field_id(item, "assignee") != assignee_id:
        return False

    if exclude_statuses and _status_values(item).intersection(exclude_statuses):
        return False

    return True


def _normalize_filter_value(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_status_filter_values(values):
    if not values:
        return set()
    if isinstance(values, str):
        values = [values]

    normalized = set()
    for value in values:
        text = str(value).strip()
        if text:
            normalized.add(text)
    return normalized


def _status_values(item):
    status = item.get("status")
    if isinstance(status, dict):
        values = set()
        for key in ("id", "name", "value", "title"):
            value = status.get(key)
            if value is not None and str(value).strip():
                values.add(str(value).strip())
        return values
    if status is None or not str(status).strip():
        return set()
    return {str(status).strip()}


def _nested_id(item, key):
    value = item.get(key)
    if isinstance(value, dict):
        return value.get("id")
    return None


def _field_id(item, key):
    value = item.get(key)
    if isinstance(value, dict):
        return value.get("id")
    if isinstance(value, str):
        return value
    value = item.get(f"{key}ID")
    if isinstance(value, str):
        return value
    return None


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


def _page_info(response):
    data = response.get("data")
    if isinstance(data, dict):
        return data.get("pageInfo", {}) or {}
    return {}


def build_issue_list_report(
    parsed,
    config,
    search_params,
    assignee_id,
    issues,
    has_more,
):
    return {
        "source": {
            "baseURL": config.base_url,
            "teamID": config.team_id,
            "projectID": search_params.get("projectID"),
            "componentID": search_params.get("componentID"),
            "sprintID": search_params.get("sprintID"),
            "issueTypeID": search_params.get("issueTypeID"),
            "assigneeID": assignee_id,
        },
        "issues": issues,
        "pageInfo": {
            "count": len(issues),
            "hasMore": has_more,
        },
        "warnings": [],
    }


def normalize_issue_summary(issue, parsed, project_id):
    return {
        "id": issue.get("id"),
        "key": _issue_key(issue, parsed, project_id),
        "title": issue.get("title"),
        "number": issue.get("number"),
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
    }


def _issue_key(issue, parsed, project_id):
    for key in ("key", "issueKey"):
        if issue.get(key):
            return issue[key]

    number = issue.get("number")
    if number is None:
        return None

    project = issue.get("project") if isinstance(issue.get("project"), dict) else {}
    project_key = project.get("key") or parsed.project_key or project_id
    if not project_key:
        return None
    return f"{project_key}-{number}"


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


def validate_issue_list_limit(value: int) -> int:
    if value <= 0:
        raise ValueError("Expected a positive integer.")
    if value > PAGE_LIMIT * MAX_MAX_PAGES:
        raise ValueError(f"Expected a value <= {PAGE_LIMIT * MAX_MAX_PAGES}.")
    return value
