#!/usr/bin/env python3
"""Print the zones of a GCP region that are up.

Usage: gcp_region_zones.py <project> <region> [--all]
Prints JSON {"zones": [...]} (with --all: every zone, whatever its status) or {"error"}; exits 0
either way so the caller can report the reason. The service account's JSON comes on stdin (not
the environment: Ansible prints a task's environment at -vvv, no_log or not).
google.cloud 1.4 has no zone or region info module, so the Compute API is read directly.
"""
import json
import sys

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

SCOPE = "https://www.googleapis.com/auth/compute.readonly"


def region_zones(project, region, every):
    creds = service_account.Credentials.from_service_account_info(json.loads(sys.stdin.read()), scopes=[SCOPE])
    session = AuthorizedSession(creds)
    url = f"https://compute.googleapis.com/compute/v1/projects/{project}/zones"
    zones, token = [], None
    while True:
        params = {"filter": f'region eq ".*/regions/{region}"'}
        if token:
            params["pageToken"] = token
        reply = session.get(url, params=params, timeout=30)
        reply.raise_for_status()
        body = reply.json()
        zones += [z["name"] for z in body.get("items", []) if every or z.get("status") == "UP"]
        token = body.get("nextPageToken")
        if not token:
            return sorted(zones)


def main():
    try:
        print(json.dumps({"zones": region_zones(sys.argv[1], sys.argv[2], "--all" in sys.argv[3:])}))
    except Exception as e:  # noqa: BLE001 - the reason is reported, not raised
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))


if __name__ == "__main__":
    main()
