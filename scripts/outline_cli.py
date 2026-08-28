#!/usr/bin/env python3
import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid


def die(message, code=1):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def config():
    base = os.environ.get("OUTLINE_URL", "").strip().rstrip("/")
    key = os.environ.get("OUTLINE_API_KEY", "").strip()
    if not base:
        die("OUTLINE_URL is not set.")
    if not key:
        die("OUTLINE_API_KEY is not set.")
    return base, key


def call(endpoint, payload=None):
    base, key = config()
    url = f"{base}/api/{endpoint}"
    body = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "claude-outline-skill/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"Outline API HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        die(f"Outline API connection error: {exc.reason}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        die(f"Outline API returned non-JSON response: {raw[:1000]}")

    if isinstance(data, dict) and data.get("ok") is False:
        die("Outline API error: " + json.dumps(data, ensure_ascii=False))
    return data


def output(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def read_text(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def text_from_args(args):
    if getattr(args, "file", None):
        return read_text(args.file)
    if getattr(args, "text", None) is not None:
        return args.text
    die("Provide --text or --file")


def prosemirror_doc(text):
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


def multipart_upload(url, fields, file_path, file_field="file", auth_header=None):
    boundary = uuid.uuid4().hex
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    filename = os.path.basename(file_path)

    parts = []
    for key, value in (fields or {}).items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode(
                "utf-8"
            )
        )
    with open(file_path, "rb") as f:
        file_data = f.read()
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(file_data)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "claude-outline-skill/1.0",
    }
    if auth_header:
        headers["Authorization"] = auth_header
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        die(f"Attachment upload HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        die(f"Attachment upload connection error: {exc.reason}")


def cmd_collections(args):
    output(call("collections.list", {"limit": args.limit}))


def cmd_documents(args):
    payload = {"limit": args.limit}
    if args.collection:
        payload["collectionId"] = args.collection
    output(call("documents.list", payload))


def cmd_search(args):
    payload = {"query": args.query, "limit": args.limit}
    if args.collection:
        payload["collectionId"] = args.collection
    output(call("documents.search", payload))


def cmd_read(args):
    output(call("documents.info", {"id": args.id}))


def cmd_create(args):
    payload = {
        "title": args.title,
        "text": read_text(args.file),
        "collectionId": args.collection,
        "publish": not args.draft,
    }
    if args.parent:
        payload["parentDocumentId"] = args.parent
    output(call("documents.create", payload))


def cmd_replace(args):
    payload = {
        "id": args.id,
        "text": read_text(args.file),
    }
    if args.title:
        payload["title"] = args.title
    output(call("documents.update", payload))


def cmd_append(args):
    payload = {
        "id": args.id,
        "text": read_text(args.file),
        "append": True,
    }
    output(call("documents.update", payload))


def cmd_move(args):
    payload = {"id": args.id, "collectionId": args.collection}
    if args.parent:
        payload["parentDocumentId"] = args.parent
    output(call("documents.move", payload))


def cmd_restore(args):
    payload = {"id": args.id}
    if args.revision:
        payload["revisionId"] = args.revision
    output(call("documents.restore", payload))


def cmd_templates(args):
    payload = {"limit": args.limit, "template": True}
    if args.collection:
        payload["collectionId"] = args.collection
    output(call("documents.list", payload))


def cmd_users(args):
    output(call("users.list", {"limit": args.limit}))


def cmd_collection_create(args):
    payload = {"name": args.name}
    if args.description:
        payload["description"] = args.description
    if args.color:
        payload["color"] = args.color
    output(call("collections.create", payload))


def cmd_collection_update(args):
    payload = {"id": args.id}
    if args.name:
        payload["name"] = args.name
    if args.description:
        payload["description"] = args.description
    if args.color:
        payload["color"] = args.color
    output(call("collections.update", payload))


def cmd_comments(args):
    output(call("comments.list", {"documentId": args.document, "limit": args.limit}))


def cmd_comment_create(args):
    payload = {"documentId": args.document, "data": prosemirror_doc(text_from_args(args))}
    if args.parent:
        payload["parentCommentId"] = args.parent
    output(call("comments.create", payload))


def cmd_comment_update(args):
    payload = {"id": args.id, "data": prosemirror_doc(text_from_args(args))}
    output(call("comments.update", payload))


def cmd_attachment_create(args):
    size = os.path.getsize(args.file)
    content_type = mimetypes.guess_type(args.file)[0] or "application/octet-stream"
    payload = {
        "name": os.path.basename(args.file),
        "contentType": content_type,
        "size": size,
    }
    if args.document:
        payload["documentId"] = args.document
    result = call("attachments.create", payload)
    data = result.get("data", {})
    upload_url = data.get("uploadUrl")
    if upload_url:
        base, key = config()
        if upload_url.startswith("/"):
            # Local/self-hosted storage: relative endpoint on the Outline origin,
            # requires the same Bearer auth as the rest of the API.
            upload_url = base + upload_url
            auth_header = f"Bearer {key}"
        else:
            # External object storage (e.g. S3 presigned POST): no auth header,
            # the URL itself is the credential.
            auth_header = None
        multipart_upload(upload_url, data.get("form"), args.file, auth_header=auth_header)
    output({"attachment": data.get("attachment", data)})


def build_parser():
    p = argparse.ArgumentParser(
        description="Minimal Outline REST API CLI for Claude Code skills."
    )
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("collections", help="List collections")
    c.add_argument("--limit", type=int, default=100)
    c.set_defaults(func=cmd_collections)

    d = sub.add_parser("documents", help="List documents")
    d.add_argument("--collection", help="Collection ID")
    d.add_argument("--limit", type=int, default=100)
    d.set_defaults(func=cmd_documents)

    s = sub.add_parser("search", help="Search documents")
    s.add_argument("query")
    s.add_argument("--collection", help="Collection ID")
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_search)

    r = sub.add_parser("read", help="Read a document")
    r.add_argument("id", help="Document ID or urlId")
    r.set_defaults(func=cmd_read)

    cr = sub.add_parser("create", help="Create a document from Markdown")
    cr.add_argument("--collection", required=True, help="Collection ID")
    cr.add_argument("--title", required=True)
    cr.add_argument("--file", required=True, help="Markdown file path, or - for stdin")
    cr.add_argument("--parent", help="Parent document ID")
    cr.add_argument("--draft", action="store_true", help="Create as draft")
    cr.set_defaults(func=cmd_create)

    rp = sub.add_parser("replace", help="Replace complete document Markdown")
    rp.add_argument("id")
    rp.add_argument("--file", required=True, help="Markdown file path, or - for stdin")
    rp.add_argument("--title")
    rp.set_defaults(func=cmd_replace)

    ap = sub.add_parser("append", help="Append Markdown to a document")
    ap.add_argument("id")
    ap.add_argument("--file", required=True, help="Markdown file path, or - for stdin")
    ap.set_defaults(func=cmd_append)

    mv = sub.add_parser("move", help="Move a document to another collection/parent")
    mv.add_argument("id")
    mv.add_argument("--collection", required=True, help="Destination collection ID")
    mv.add_argument("--parent", help="Destination parent document ID")
    mv.set_defaults(func=cmd_move)

    rs = sub.add_parser("restore", help="Restore a deleted/archived document, or roll back to a prior revision")
    rs.add_argument("id")
    rs.add_argument("--revision", help="Revision ID to roll back to, instead of un-trashing")
    rs.set_defaults(func=cmd_restore)

    tp = sub.add_parser("templates", help="List templates")
    tp.add_argument("--collection", help="Collection ID")
    tp.add_argument("--limit", type=int, default=100)
    tp.set_defaults(func=cmd_templates)

    us = sub.add_parser("users", help="List workspace users")
    us.add_argument("--limit", type=int, default=100)
    us.set_defaults(func=cmd_users)

    cc = sub.add_parser("collection-create", help="Create a collection")
    cc.add_argument("--name", required=True)
    cc.add_argument("--description")
    cc.add_argument("--color")
    cc.set_defaults(func=cmd_collection_create)

    cu = sub.add_parser("collection-update", help="Update a collection")
    cu.add_argument("id")
    cu.add_argument("--name")
    cu.add_argument("--description")
    cu.add_argument("--color")
    cu.set_defaults(func=cmd_collection_update)

    cl = sub.add_parser("comments", help="List comments on a document")
    cl.add_argument("document", help="Document ID")
    cl.add_argument("--limit", type=int, default=100)
    cl.set_defaults(func=cmd_comments)

    ccm = sub.add_parser("comment-create", help="Create a comment on a document")
    ccm.add_argument("document", help="Document ID")
    ccm.add_argument("--text")
    ccm.add_argument("--file", help="Markdown file path, or - for stdin")
    ccm.add_argument("--parent", help="Parent comment ID, for replies")
    ccm.set_defaults(func=cmd_comment_create)

    cum = sub.add_parser("comment-update", help="Update a comment")
    cum.add_argument("id")
    cum.add_argument("--text")
    cum.add_argument("--file", help="Markdown file path, or - for stdin")
    cum.set_defaults(func=cmd_comment_update)

    at = sub.add_parser("attachment-create", help="Upload a file as an attachment")
    at.add_argument("--file", required=True)
    at.add_argument("--document", help="Associate with a document ID")
    at.set_defaults(func=cmd_attachment_create)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
