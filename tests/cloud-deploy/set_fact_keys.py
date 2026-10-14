#!/usr/bin/env python3
"""Print, as JSON, every variable a set_fact sets in the given task files (blocks included)."""
import json
import sys

import yaml


def walk(tasks, out):
    for t in tasks or []:
        for key in ("block", "rescue", "always"):
            walk(t.get(key), out)
        facts = t.get("ansible.builtin.set_fact") or t.get("set_fact")
        if isinstance(facts, dict):
            out.update(k for k in facts if k != "cacheable")


keys = set()
for path in sys.argv[1:]:
    with open(path) as f:
        walk(yaml.safe_load(f), keys)
print(json.dumps(sorted(keys)))
