#!/usr/bin/env bash
# Controlled private VM only. Installs an isolated, pinned source snapshot and
# prepares private readiness evidence. Never signs authorization or starts a service.
set -euo pipefail
umask 077
test "$(id -u)" = 0
commit="${1:?Pass a reviewed full Git commit SHA}"
[[ "$commit" =~ ^[0-9a-f]{40}$ ]]
export GIT_TERMINAL_PROMPT=0 GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
work=$(mktemp -d /srv/mibo-private/agent-ready.XXXXXX)
code=$(mktemp -d /opt/mibo-core-v2.0.1.XXXXXX)
trap 'chown -R root:mibo "$work" "$code"; chmod -R u=rwX,g=rX,o= "$work" "$code"' EXIT
git -c credential.helper= -c core.hooksPath=/dev/null init -q "$work/git"
git -C "$work/git" -c credential.helper= -c core.hooksPath=/dev/null fetch -q --depth=1 https://github.com/mibo-research/mibo-core.git "$commit"
test "$(git -C "$work/git" rev-parse FETCH_HEAD)" = "$commit"
git -C "$work/git" archive FETCH_HEAD | tar -x -C "$code"
printf '固定コード: %s\n私有記録: %s\n' "$commit" "$work"
(
    cd "$code"
    env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
        python3 -m unittest discover -s automation/tests -v
) > "$work/synthetic-tests.log" 2>&1
tail -n 4 "$work/synthetic-tests.log"
python3 -B "$code/runtime/seal-installed-snapshot.py" --root "$code" --source-commit "$commit" > "$work/installed-source-provenance.json"
chown -R root:mibo "$code"
chmod -R u=rwX,g=rX,o= "$code"
python3 -B "$code/runtime/prepare-core-v2-agent.py" --out-dir "$work/readiness"
