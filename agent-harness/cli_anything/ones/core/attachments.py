import os
import re
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .config import is_trusted_ones_host
from .errors import ApiError, UsageError


MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024
MAX_ATTACHMENT_REDIRECTS = 5


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirectHandler)


def download_attachments(
    report,
    output_dir,
    allowed_hosts=None,
    allow_external_attachment_hosts=False,
):
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []
    for attachment in report["issue"].get("attachments", []):
        temp_url = attachment.get("tempURL")
        if not temp_url:
            continue
        target_path = _unique_path(output_dir, _safe_filename(attachment.get("name") or attachment.get("id") or "attachment"))
        _download_file(
            temp_url,
            target_path,
            allowed_hosts=allowed_hosts,
            allow_external_attachment_hosts=allow_external_attachment_hosts,
        )
        downloaded.append(
            {
                "id": attachment.get("id"),
                "name": attachment.get("name"),
                "path": target_path,
                "mime": attachment.get("mime"),
                "sizeByte": os.path.getsize(target_path),
            }
        )
    return downloaded


def _download_file(
    url,
    target_path,
    allowed_hosts=None,
    allow_external_attachment_hosts=False,
):
    _validate_attachment_url(url, allowed_hosts, allow_external_attachment_hosts)
    total = 0
    try:
        with _open_attachment_response(
            url,
            allowed_hosts,
            allow_external_attachment_hosts,
        ) as response, open(target_path, "wb") as output:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_ATTACHMENT_BYTES:
                raise UsageError("Attachment exceeds the 100 MB download limit.")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_ATTACHMENT_BYTES:
                    raise UsageError("Attachment exceeds the 100 MB download limit.")
                output.write(chunk)
    except Exception as exc:
        if os.path.exists(target_path):
            os.remove(target_path)
        if isinstance(exc, UsageError):
            raise
        raise ApiError(f"Failed to download attachment to {target_path}: {exc}") from exc


def _open_attachment_response(
    url,
    allowed_hosts=None,
    allow_external_attachment_hosts=False,
):
    current_url = url
    for _redirect in range(MAX_ATTACHMENT_REDIRECTS + 1):
        _validate_attachment_url(
            current_url,
            allowed_hosts=allowed_hosts,
            allow_external_attachment_hosts=allow_external_attachment_hosts,
        )
        request = Request(
            current_url,
            headers={"User-Agent": "cli-anything-ones/0.1.0"},
        )
        try:
            return _NO_REDIRECT_OPENER.open(request, timeout=60)
        except HTTPError as error:
            if error.code not in {301, 302, 303, 307, 308}:
                raise
            location = error.headers.get("Location")
            if error.fp:
                error.fp.close()
            if not location:
                raise UsageError("Attachment redirect response did not include a Location header.")
            current_url = urljoin(current_url, location)

    raise UsageError("Attachment download exceeded the redirect limit.")


def _validate_attachment_url(url, allowed_hosts=None, allow_external_attachment_hosts=False):
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise UsageError("Refusing to download a non-HTTPS attachment URL.")
    if allow_external_attachment_hosts:
        return
    allowed = set(allowed_hosts or [])
    hostname = parsed.hostname or ""
    if hostname in allowed or is_trusted_ones_host(hostname):
        return
    raise UsageError(
        f"Refusing to download attachment from untrusted host {hostname}. Use --allow-external-attachment-hosts if this ONES instance uses an external CDN."
    )


def _safe_filename(value):
    filename = re.sub(r"[\\/\0]+", "-", value).strip().strip(".")
    return filename or "attachment"


def _unique_path(output_dir, filename):
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(output_dir, filename)
    index = 2
    while os.path.exists(candidate):
        candidate = os.path.join(output_dir, f"{base}-{index}{ext}")
        index += 1
    return candidate
