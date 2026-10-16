#!/usr/bin/env bash
# Integration test for the dblab-tunnel role (platform-all#953). Run from the repository root:
#
#   tests/dblab-tunnel/integration.sh
#
# Starts an Ubuntu 24.04 systemd container (privileged: it runs sshd and loads nftables rules in
# its own network namespace), applies the role in it and runs in_container.sh. Needs Docker.
set -euo pipefail
cd "$(dirname "$0")/../.."

IMAGE=${DBLAB_TUNNEL_TEST_IMAGE:-geerlingguy/docker-ubuntu2404-ansible:latest}
NAME="dblab-tunnel-test-$$"

docker run -d --name "$NAME" --privileged --cgroupns=host \
  -v /sys/fs/cgroup:/sys/fs/cgroup:rw -v "$PWD":/src:ro "$IMAGE" >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1' EXIT

for _ in $(seq 60); do
  state=$(docker exec "$NAME" systemctl is-system-running 2>/dev/null || true)
  case "$state" in running|degraded) break ;; esac
  sleep 1
done

docker exec "$NAME" bash /src/tests/dblab-tunnel/in_container.sh
