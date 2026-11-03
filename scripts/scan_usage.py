#!/usr/bin/env python3
"""Measure how much each tech-stack item is used across my repos.

Covers every repo (own, org, collaborator) I have commits in. Languages are
the share of all code bytes (GitHub's language stats); everything else is the
share of repos that use it, found by shallow-cloning each repo and matching
manifests, configs and source. Writes assets/usage.json for build_assets.py.

Needs a token that can read the private/org repos, so run it locally:
    python3 scripts/scan_usage.py && python3 scripts/build_assets.py
"""
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

from generate import gql

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "usage.json"
CACHE = Path(os.environ.get("SCAN_CACHE", Path.home() / ".cache" / "profile-scan"))

SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "dist", "build", ".next", "dbt_packages",
             "site-packages", "vendor", "__pycache__", ".terraform"}
TEXT_EXT = {".json", ".toml", ".txt", ".yml", ".yaml", ".sh", ".tf", ".py", ".ts", ".tsx",
            ".js", ".jsx", ".mjs", ".cfg", ".ini", ".sql"}
MAX_BYTES = 512_000

# key: (content regex, path regex) -- either matching counts the repo as using it
RULES = {
    "react": (r'"react"\s*:', None),
    "nextjs": (r'"next"\s*:', r"(^|/)next\.config\.[mc]?[jt]s$"),
    "threejs": (r'"three"\s*:', None),
    "tailwind": (r'"tailwindcss"\s*:', r"(^|/)tailwind\.config\."),
    "docker": (None, r"(^|/)(dockerfile[^/]*|docker-compose[^/]*\.ya?ml|compose\.ya?ml)$"),
    "vercel": (None, r"(^|/)vercel\.json$"),
    "git": (None, r"."),
    "bigquery": (r"google-cloud-bigquery|@google-cloud/bigquery|dbt-bigquery|bigquery\.client\(", None),
    "gcs": (r"google-cloud-storage|@google-cloud/storage|storage\.client\(|gcsfs|gsutil|gs://", None),
    "cloudrun": (r"gcloud run |\.run\.app|deploy-cloudrun", None),
    "functions": (r"functions-framework|gcloud functions |cloudfunctions\.net", r"(^|/)cloud_functions/"),
    "composer": (r"gcloud composer |composer_environment", r"(^|/)cloud_composer/"),
    "dataflow": (r"gcloud dataflow |[\"']dataflow[\"'],|dataflow_v1beta3|dataflowrunner|google-cloud-dataflow|apache[-_]beam|dataflow\.googleapis", None),
    "apigateway": (r"gcloud api-gateway |apigateway\.googleapis", r"(^|/)api_gateway/"),
    "artifactregistry": (r"docker\.pkg\.dev|artifactregistry", None),
    "secretmanager": (r"google-cloud-secret-manager|secretmanager|gcloud secrets ", None),
    "logging": (r"google-cloud-logging|from google\.cloud import logging|logging_v2", None),
}
RULES = {k: (c and re.compile(c), p and re.compile(p)) for k, (c, p) in RULES.items()}


REPO_FIELDS = """nameWithOwner isFork deployments(first:5){nodes{creator{login}}}
  languages(first:30){edges{size node{name}}}
  defaultBranchRef{target{...on Commit{history(author:{id:$id}){totalCount}}}}"""


def repos():
    """Every non-fork repo I own, collaborate on, or can see through an org, that has my commits."""
    viewer = gql("query{viewer{id}}")["viewer"]["id"]
    found = {}

    def collect(nodes):
        for r in nodes:
            ref = r["defaultBranchRef"]
            if not r["isFork"] and ref and ref["target"]["history"]["totalCount"]:
                found[r["nameWithOwner"]] = r

    cursor = None
    while True:
        page = gql(
            f"""query($id:ID!,$after:String){{viewer{{repositories(first:50,after:$after,
                ownerAffiliations:[OWNER,ORGANIZATION_MEMBER,COLLABORATOR]){{
              pageInfo{{hasNextPage endCursor}} nodes{{{REPO_FIELDS}}}}}}}}}""",
            id=viewer, after=cursor,
        )["viewer"]["repositories"]
        collect(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    # org repos reached through teams don't show up above
    orgs = gql("query{viewer{organizations(first:50){nodes{login}}}}")["viewer"]["organizations"]["nodes"]
    for org in orgs:
        cursor = None
        while True:
            page = gql(
                f"""query($id:ID!,$login:String!,$after:String){{organization(login:$login){{
                  repositories(first:50,after:$after){{
                    pageInfo{{hasNextPage endCursor}} nodes{{{REPO_FIELDS}}}}}}}}}""",
                id=viewer, login=org["login"], after=cursor,
            )["organization"]["repositories"]
            collect(page["nodes"])
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
    return list(found.values())


def checkout(name):
    path = CACHE / name.replace("/", "__")
    if path.exists():
        subprocess.run(["git", "-C", path, "fetch", "-q", "--depth", "1", "origin", "HEAD"], check=True)
        subprocess.run(["git", "-C", path, "reset", "-q", "--hard", "FETCH_HEAD"], check=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["gh", "repo", "clone", name, str(path), "--", "-q", "--depth", "1"], check=True)
    return path


def detect(path):
    found = set()
    for dirpath, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            full = Path(dirpath, f)
            rel = full.relative_to(path).as_posix().lower()
            text = None
            for key, (content, paths) in RULES.items():
                if key in found:
                    continue
                if paths and paths.search(rel):
                    found.add(key)
                    continue
                if content and full.suffix.lower() in TEXT_EXT:
                    if text is None:
                        try:
                            text = full.read_bytes()[:MAX_BYTES].decode("utf-8", "ignore").lower()
                        except OSError:
                            text = ""
                    if content.search(text):
                        found.add(key)
    return found


def main():
    rs = repos()
    langs, using = Counter(), Counter()
    for r in rs:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
        found = detect(checkout(r["nameWithOwner"]))
        if any((d["creator"] or {}).get("login") == "vercel" for d in r["deployments"]["nodes"]):
            found.add("vercel")
        using.update(found)
        print(f"{r['nameWithOwner']:<55} {' '.join(sorted(found - {'git'}))}")

    total = sum(langs.values()) or 1
    OUT.write_text(json.dumps({
        "repos": len(rs),
        "languages": {k: round(v / total * 100, 1) for k, v in langs.most_common()},
        "repo_share": {k: round(v / len(rs) * 100) for k, v in using.most_common()},
    }, indent=2) + "\n")
    print(f"wrote {OUT} ({len(rs)} repos)")


if __name__ == "__main__":
    main()
