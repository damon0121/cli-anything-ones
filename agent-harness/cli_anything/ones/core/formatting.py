import json


def print_payload(payload, output_format):
    if output_format == "json":
        return f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
    if "issues" in payload:
        return format_issue_list_markdown(payload)
    if "issue" in payload:
        return format_issue_markdown(payload)
    return format_parse_only(payload)


def format_parse_only(parsed):
    return "\n".join(
        [
            f"baseURL: {parsed.get('baseURL')}",
            f"teamID: {parsed.get('teamID')}",
            f"projectID: {parsed.get('projectID') or '-'}",
            f"issueTypeID: {parsed.get('issueTypeID') or '-'}",
            f"issueKey: {parsed.get('issueKey')}",
            f"issueNumber: {parsed.get('issueNumber') or '-'}",
        ]
    ) + "\n"


def format_issue_markdown(report):
    issue = report["issue"]
    lines = [f"# {issue.get('key') or issue.get('id')} {issue.get('title') or ''}".strip(), ""]
    lines.extend(
        [
            f"- ONES ID: {issue.get('id')}",
            f"- 状态: {_name(issue.get('status'))}",
            f"- 优先级: {_name(issue.get('priority'))}",
            f"- 严重程度: {_name(issue.get('severityLevel'))}",
            f"- 缺陷类型: {_name(issue.get('defectType'))}",
            f"- 负责人: {_name(issue.get('assignee'))}",
            f"- 创建人: {_name(issue.get('creator'))}",
            f"- 项目: {_name(issue.get('project')) or report['source'].get('projectID') or '-'}",
            f"- 迭代: {_name(issue.get('sprint'))}",
            "",
        ]
    )
    _section(lines, "描述", issue.get("descriptionText") or "-")
    _section(lines, "自定义字段", _format_custom_fields(issue.get("customFields") or []))
    _section(lines, "评论", _format_comments(issue.get("comments") or []))
    _section(lines, "附件", _format_attachments(issue.get("attachments") or []))
    if report.get("warnings"):
        _section(lines, "读取警告", "\n".join(f"- {warning}" for warning in report["warnings"]))
    return "\n".join(lines) + "\n"


def format_issue_list_markdown(report):
    source = report["source"]
    lines = ["# ONES 工作项列表", ""]
    lines.extend(
        [
            f"- teamID: {source.get('teamID')}",
            f"- projectID: {source.get('projectID') or '-'}",
            f"- componentID: {source.get('componentID') or '-'}",
            f"- sprintID: {source.get('sprintID') or '-'}",
            f"- issueTypeID: {source.get('issueTypeID') or '-'}",
            f"- assigneeID: {source.get('assigneeID') or '-'}",
            f"- count: {report.get('pageInfo', {}).get('count', 0)}",
            f"- hasMore: {str(report.get('pageInfo', {}).get('hasMore', False)).lower()}",
            "",
        ]
    )
    _section(lines, "工作项", _format_issue_list(report.get("issues") or []))
    if report.get("warnings"):
        _section(lines, "读取警告", "\n".join(f"- {warning}" for warning in report["warnings"]))
    return "\n".join(lines) + "\n"


def _section(lines, title, content):
    lines.extend([f"## {title}", "", content or "-", ""])


def _name(value):
    if isinstance(value, dict):
        return value.get("name") or "-"
    return value or "-"


def _format_custom_fields(fields):
    lines = [f"- {field.get('name')}: {field.get('text')}" for field in fields if field.get("text")]
    return "\n".join(lines) if lines else "-"


def _format_comments(comments):
    if not comments:
        return "-"
    return "\n".join(
        f"- {_name(comment.get('owner')) or 'unknown'}: {comment.get('text') or ''}"
        for comment in comments
    )


def _format_attachments(attachments):
    if not attachments:
        return "-"
    lines = []
    for attachment in attachments:
        meta = ", ".join(
            item
            for item in (attachment.get("mime"), format_bytes(attachment.get("sizeByte")))
            if item
        )
        line = f"- {attachment.get('name')}{f' ({meta})' if meta else ''}"
        if attachment.get("tempURL"):
            line = f"{line}\n  URL: {attachment['tempURL']}"
        lines.append(line)
    return "\n".join(lines)


def _format_issue_list(issues):
    if not issues:
        return "-"
    lines = []
    for issue in issues:
        key = issue.get("key") or issue.get("id") or "-"
        title = issue.get("title") or ""
        meta = ", ".join(
            item
            for item in (
                _name(issue.get("status")),
                _name(issue.get("assignee")),
                _name(issue.get("issueType")),
            )
            if item and item != "-"
        )
        lines.append(f"- {key} {title}{f' ({meta})' if meta else ''}".rstrip())
    return "\n".join(lines)


def format_bytes(value):
    if not isinstance(value, (int, float)):
        return ""
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / 1024 / 1024:.1f} MB"
