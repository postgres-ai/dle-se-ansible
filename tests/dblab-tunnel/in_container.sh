#!/usr/bin/env bash
# Runs inside the test container (see integration.sh): applies the role, then tries everything a
# customer holding a tunnel key could try. Every check prints PASS or FAIL; the exit status is the
# number of failures.
set -uo pipefail

SRC=/src
FAILS=0
pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1${2:+ ($2)}"; FAILS=$((FAILS + 1)); }

state() { echo "{\"status\": $1, \"keys\": $2}" > /tmp/stub/state.json; }

SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR
          -o ConnectTimeout=5)
# tunnel_ssh [ssh options...] [-- command...]
# Always call it in a subshell or with '&': it execs ssh, so '$!' is ssh itself and 'kill' ends it.
tunnel_ssh() { local opts=(); while [ $# -gt 0 ] && [ "$1" != "--" ]; do opts+=("$1"); shift; done; [ "${1:-}" = "--" ] && shift
  exec ssh "${SSH_OPTS[@]}" -i /tmp/keys/customer "${opts[@]}" dblab-tunnel@127.0.0.1 "$@"; }

# Opens a local forward to $1, reads what arrives through it, and closes it.
# Prints what came through (empty when the forward was refused or rejected).
through_forward() {
  local target=$1 key=${2:-/tmp/keys/customer} user=${3:-dblab-tunnel} lport=$((20000 + RANDOM % 10000))
  ssh "${SSH_OPTS[@]}" -i "$key" -N -o ExitOnForwardFailure=yes -L "$lport:$target" "$user@127.0.0.1" &
  local pid=$!
  for _ in $(seq 50); do ss -ltn | grep -q ":$lport " && break; sleep 0.1; done
  timeout 3 nc 127.0.0.1 "$lport" </dev/null 2>/dev/null | head -1
  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
}

# True when sshd itself refuses a forward to $1 (PermitOpen), as opposed to the firewall.
sshd_refuses() {
  local lport=$((40000 + RANDOM % 10000)) err=/tmp/sshd_refuses.err
  # Not tunnel_ssh: the client reports a refused channel at INFO, and the first LogLevel given wins.
  ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=INFO \
    -o ConnectTimeout=5 -i /tmp/keys/customer -N -o ExitOnForwardFailure=yes -L "$lport:$1" \
    dblab-tunnel@127.0.0.1 2>"$err" & local p=$!
  for _ in $(seq 50); do ss -ltn | grep -q ":$lport " && break; sleep 0.1; done
  timeout 3 nc 127.0.0.1 "$lport" </dev/null >/dev/null 2>&1; sleep 0.5
  kill "$p" 2>/dev/null; wait "$p" 2>/dev/null
  grep -q 'administratively prohibited' "$err"
}

# True when the tunnel user can log in (a forward-only session stays up).
can_login() { tunnel_ssh -N -o ExitOnForwardFailure=yes -L "$((30000 + RANDOM % 10000)):127.0.0.1:6000" & local p=$!; sleep 1.5
  if kill -0 "$p" 2>/dev/null; then kill "$p"; wait "$p" 2>/dev/null; return 0; fi; wait "$p" 2>/dev/null; return 1; }

set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq openssh-server openssh-client netcat-openbsd iproute2 >/dev/null
systemctl start ssh
mkdir -p /tmp/stub /tmp/keys /root/.ssh
: > /tmp/stub/calls
state 200 '[]'
ssh-keygen -q -t ed25519 -N '' -f /tmp/keys/customer
ssh-keygen -q -t ed25519 -N '' -f /tmp/keys/ops
cp /tmp/keys/ops.pub /root/.ssh/authorized_keys   # the team key, as authorized-keys installs it
OUTSIDE_IP=$(hostname -I | awk '{print $1}')
nohup python3 -I "$SRC/tests/dblab-tunnel/stub.py" "$OUTSIDE_IP" >/tmp/stub/log 2>&1 &
sleep 1

cd "$SRC/tests/dblab-tunnel"
ansible-playbook -i localhost, -e @test-vars.yml converge.yml >/tmp/converge1.log 2>&1 || { cat /tmp/converge1.log; exit 1; }
ansible-playbook -i localhost, -e @test-vars.yml converge.yml >/tmp/converge2.log 2>&1 || { cat /tmp/converge2.log; exit 1; }
set +e

CUSTOMER=$(cat /tmp/keys/customer.pub)

# --- the role ---------------------------------------------------------------------------------
grep -q 'changed=0' /tmp/converge2.log && pass "a second run changes nothing" \
  || fail "a second run changes nothing" "$(grep -A1 'PLAY RECAP' /tmp/converge2.log | tail -1)"
[ "$(stat -c '%a %U %G' /etc/dblab-tunnel/token)" = "640 root dblab-tunnel-keys" ] \
  && pass "token file is 0640 root:dblab-tunnel-keys" || fail "token file mode" "$(stat -c '%a %U %G' /etc/dblab-tunnel/token)"
getent passwd dblab-tunnel | grep -q ':/usr/sbin/nologin$' && pass "tunnel user has no shell" || fail "tunnel user has no shell"
systemctl is-enabled dblab-tunnel-nft >/dev/null && nft list table inet dblab_tunnel >/dev/null \
  && pass "firewall rules loaded and enabled" || fail "firewall rules loaded and enabled"

# --- keys come from the Platform --------------------------------------------------------------
can_login && fail "no key on the Platform: login denied" || pass "no key on the Platform: login denied"
state 200 "[\"$CUSTOMER\"]"; sleep 2.5
[ "$(through_forward 127.0.0.1:6000)" = "clone-6000" ] && pass "key added: tunnel to a clone (127.0.0.1)" \
  || fail "key added: tunnel to a clone (127.0.0.1)"
[ "$(through_forward localhost:6100)" = "clone-6100" ] && pass "tunnel to a clone by 'localhost' (Console's form)" \
  || fail "tunnel to a clone by 'localhost'"

# --- a re-run puts what is on disk into effect --------------------------------------------------
# A run that wrote the files but stopped before the reload (failed check, lost connection) leaves
# sshd and the firewall running the old config; the next run sees "unchanged" files.
sshd_refuses 127.0.0.1:2345 && pass "(control) sshd refuses a forward outside the pool" \
  || fail "(control) sshd refuses a forward outside the pool"
cp /etc/ssh/sshd_config.d/99-dblab-tunnel.conf /tmp/99.rerun
sed -i '/PermitOpen/d' /etc/ssh/sshd_config.d/99-dblab-tunnel.conf; systemctl reload ssh; sleep 0.5
cp /tmp/99.rerun /etc/ssh/sshd_config.d/99-dblab-tunnel.conf   # right on disk, stale in sshd
nft insert rule inet dblab_tunnel tunnel ip daddr 127.0.0.1 tcp dport 2345 accept   # stale rules
rules=$(nft list table inet dblab_tunnel)   # not a pipe: grep -q + pipefail would read nft's SIGPIPE as "no match"
grep -q 'dport 2345 accept' <<<"$rules" && pass "(control) stale firewall rule in place" \
  || fail "(control) stale firewall rule in place"
ansible-playbook -i localhost, -e @test-vars.yml converge.yml >/tmp/converge3.log 2>&1 \
  || fail "re-run over stale daemons" "$(tail -5 /tmp/converge3.log)"
sshd_refuses 127.0.0.1:2345 && pass "re-run: sshd runs the config on disk" \
  || fail "re-run: sshd runs the config on disk"
rules=$(nft list table inet dblab_tunnel)
grep -q 'dport 2345' <<<"$rules" && fail "re-run: the firewall runs the rules on disk" \
  || pass "re-run: the firewall runs the rules on disk"

# --- nothing but tunnels ----------------------------------------------------------------------
out=$(tunnel_ssh -T -- id 2>&1); echo "$out" | grep -q 'currently not available' && ! echo "$out" | grep -q 'uid=\|chdir' \
  && pass "a command runs nologin, not the command" || fail "a command runs nologin" "$out"
out=$(timeout 5 ssh "${SSH_OPTS[@]}" -i /tmp/keys/customer -tt dblab-tunnel@127.0.0.1 2>&1 </dev/null); rc=$?
echo "$out" | grep -q 'PTY allocation request failed' && [ "$rc" -ne 124 ] && [ "$rc" -ne 0 ] \
  && pass "no terminal, no interactive shell" || fail "no terminal, no interactive shell" "rc=$rc $out"
[ -z "$(through_forward 127.0.0.1:2345)" ] && pass "engine API port is refused" || fail "engine API port is refused"
[ -z "$(through_forward "$OUTSIDE_IP:7777")" ] && pass "another address is refused" || fail "another address is refused"
[ "$(through_forward "$OUTSIDE_IP:7777" /tmp/keys/ops root)" = "outside-pool" ] \
  && pass "(control) that address is reachable for root" || fail "(control) that address is reachable for root"
timeout 10 ssh "${SSH_OPTS[@]}" -i /tmp/keys/customer -N -o ExitOnForwardFailure=yes -R 17000:127.0.0.1:6000 \
  dblab-tunnel@127.0.0.1 2>/dev/null; rc=$?
[ "$rc" -ne 0 ] && [ "$rc" -ne 124 ] && pass "remote forwarding is refused" || fail "remote forwarding is refused" "rc=$rc"
scp "${SSH_OPTS[@]}" -i /tmp/keys/customer /etc/hostname dblab-tunnel@127.0.0.1:/tmp/x >/dev/null 2>&1 \
  && fail "scp is refused" || pass "scp is refused"
echo "ls" | sftp "${SSH_OPTS[@]}" -i /tmp/keys/customer -b - dblab-tunnel@127.0.0.1 >/dev/null 2>&1 \
  && fail "sftp is refused" || pass "sftp is refused"
ssh "${SSH_OPTS[@]}" -i /tmp/keys/customer root@127.0.0.1 true 2>/dev/null \
  && fail "customer key does not open root" || pass "customer key does not open root"
ssh "${SSH_OPTS[@]}" -i /tmp/keys/ops root@127.0.0.1 true 2>/dev/null \
  && pass "team key opens root" || fail "team key opens root"

# --- connection cap ---------------------------------------------------------------------------
lport=19999
tunnel_ssh -N -o ExitOnForwardFailure=yes -L "$lport:127.0.0.1:6000" & cap_ssh=$!
for _ in $(seq 50); do ss -ltn | grep -q ":$lport " && break; sleep 0.1; done
holders=()
for i in 1 2 3; do (sleep 8 | nc 127.0.0.1 $lport >/tmp/cap.$i 2>/dev/null) & holders+=($!); done
sleep 1.5
fourth=$(timeout 3 nc 127.0.0.1 $lport </dev/null 2>/dev/null | head -1)
got=$(cat /tmp/cap.1 /tmp/cap.2 /tmp/cap.3 | grep -c clone-6000)
[ "$got" = 3 ] && [ -z "$fourth" ] && pass "at most 3 concurrent forwarded connections (test cap)" \
  || fail "connection cap" "held=$got fourth='$fourth'"
kill "${holders[@]}" "$cap_ssh" 2>/dev/null; wait "${holders[@]}" "$cap_ssh" 2>/dev/null

# --- the firewall holds even if sshd lets a forward through -----------------------------------
cp /etc/ssh/sshd_config.d/99-dblab-tunnel.conf /tmp/99.bak
sed -i '/PermitOpen/d' /etc/ssh/sshd_config.d/99-dblab-tunnel.conf; systemctl reload ssh; sleep 0.5
[ -z "$(through_forward 127.0.0.1:2345)" ] && pass "backstop: engine API rejected without PermitOpen" \
  || fail "backstop: engine API rejected without PermitOpen"
[ -z "$(through_forward "$OUTSIDE_IP:7777")" ] && pass "backstop: another address rejected without PermitOpen" \
  || fail "backstop: another address rejected without PermitOpen"
[ "$(through_forward 127.0.0.1:6000)" = "clone-6000" ] && pass "backstop: the clone still works" \
  || fail "backstop: the clone still works"
cp /tmp/99.bak /etc/ssh/sshd_config.d/99-dblab-tunnel.conf; systemctl reload ssh; sleep 0.5

# --- revocation and outages --------------------------------------------------------------------
state 200 '[]'; sleep 2.5
can_login && fail "key removed: denied after the cache time" || pass "key removed: denied after the cache time"
state 200 "[\"$CUSTOMER\"]"; sleep 2.5
can_login && pass "key back: allowed" || fail "key back: allowed"
state 503 "[]"; sleep 2.5
can_login && pass "Platform down: the last answer still opens the tunnel" \
  || fail "Platform down: the last answer still opens the tunnel"
state 401 "[]"; sleep 1.5
can_login && fail "token refused: denied at once" || pass "token refused: denied at once"
state 503 "[]"; sleep 1.5
can_login && fail "refused, then down: still denied (cache wiped)" || pass "refused, then down: still denied (cache wiped)"

# --- survives a restart -------------------------------------------------------------------------
systemctl restart dblab-tunnel-nft && nft list table inet dblab_tunnel >/dev/null \
  && pass "firewall unit restarts cleanly" || fail "firewall unit restarts cleanly"
nft list ruleset | grep -q 'table ip filter\|table ip nat\|ufw' ; other=$?
iptables -S >/dev/null 2>&1; pass "(info) other tables untouched: $( [ $other = 0 ] && echo present || echo none-in-container)"

echo "failures: $FAILS"
exit "$FAILS"
