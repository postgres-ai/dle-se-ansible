#!/usr/bin/env python3
"""A fresh DBLab box survives transient network trouble during the install (#35).

On 2026-10-08 two `pgai dblab deploy` boxes failed pulling postgresai/instance-jobs
(a DNS timeout) and postgresai/netdata-for-dle (IPv6 unreachable). Pinned here:
every image the deploy starts, and the two the engine pulls itself (UI and the
extended Postgres), is pulled first when missing, retried ~20 s apart; an image
already on the box is never re-pulled (a re-run needs no registry, and a rebuilt
tag does not move under a running box). The packages role first waits (bounded)
for cloud-init.
"""

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
failures: list[str] = []


def check(ok: bool, what: str) -> None:
    if not ok:
        failures.append(what)


def flat(tasks):
    """Every task, blocks and rescues included, in file order."""
    for t in tasks or []:
        yield t
        for key in ("block", "rescue", "always"):
            yield from flat(t.get(key))


def pulled_with_retries(path: str, image_var: str) -> None:
    """Pulled first when missing, retried; an image already on the box is never re-pulled (REV !81 B1)."""
    tasks = list(flat(yaml.safe_load((REPO / path).read_text())))
    pulls = [t for t in tasks
             if image_var in str((t.get("community.docker.docker_image") or {}).get("name", ""))]
    check(bool(pulls), f"{path}: no retried pull of {image_var}")
    for t in pulls:
        img = t["community.docker.docker_image"]
        check(img.get("source") == "pull" and not img.get("force_source"),
              f"{path}: {image_var} must be pulled only when it is missing (source: pull, no force_source)")
        check("until" in t and ("succeeded" in str(t["until"]) or "success" in str(t["until"]))
              and isinstance(t.get("retries"), int) and t["retries"] >= 3
              and isinstance(t.get("delay"), int) and t["delay"] >= 15,
              f"{path}: the pull of {image_var} must retry until it succeeds, at least 3 times, at least 15 s apart")
    # Before the container that runs it (for the engine's own pulls: before the engine starts).
    runs = [i for i, t in enumerate(tasks) if "community.docker.docker_container" in t
            and image_var in str(t["community.docker.docker_container"].get("image", ""))]
    engines = [i for i, t in enumerate(tasks) if "community.docker.docker_container" in t]
    users = runs or engines
    if pulls and users:
        check(tasks.index(pulls[0]) < min(users), f"{path}: {image_var} must be pulled before its container starts")


for path, image in [
    ("roles/dblab-agent/tasks/main.yml", "dblab_agent_image"),
    ("roles/joe-agent/tasks/main.yml", "joe_agent_image"),
    ("roles/netdata/tasks/main.yml", "netdata_image"),
    ("roles/joe-bot/tasks/main.yml", "joe_image"),
    ("roles/dblab-engine/tasks/restart_engine.yml", "dblab_engine_image"),
    ("roles/dblab-engine/tasks/restart_engine.yml", "dblab_engine_ui_image"),
    ("roles/dblab-engine/tasks/restart_engine.yml", "dblab_engine_db_image"),
]:
    pulled_with_retries(path, image)

first = yaml.safe_load((REPO / "roles/packages/tasks/main.yml").read_text())[0]
cmd = str(first.get("ansible.builtin.command", first.get("ansible.builtin.shell", "")))
check("cloud-init status --wait" in cmd and "timeout" in cmd, "the packages role must first wait (bounded) for cloud-init")
check(str(first.get("failed_when", "")).lower() == "false", "the cloud-init wait must never fail the deploy")

if failures:
    print("FAIL:\n  " + "\n  ".join(failures))
    sys.exit(1)
print("OK: every image is pulled with retries; cloud-init is waited for")
