#!/usr/bin/env bash
# Controlled VM only; human signature is requested after the concrete bundle exists.
set -euo pipefail
umask 077
test "$(id -u)" = 0
commit="${1:?Pass a reviewed full Git commit SHA}"
[[ "$commit" =~ ^[0-9a-f]{40}$ ]]
export GIT_TERMINAL_PROMPT=0 GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
work=$(mktemp -d /srv/mibo-private/scoped-ready.XXXXXX)
code=$(mktemp -d /opt/mibo-core-v2.0.2.XXXXXX)
trap 'chown -R root:mibo "$work" "$code"; chmod -R u=rwX,g=rX,o= "$work" "$code"' EXIT
git -c credential.helper= -c core.hooksPath=/dev/null init -q "$work/git"
git -C "$work/git" -c credential.helper= -c core.hooksPath=/dev/null fetch -q --depth=1 https://github.com/mibo-research/mibo-core.git "$commit"
test "$(git -C "$work/git" rev-parse FETCH_HEAD)" = "$commit"
git -C "$work/git" archive FETCH_HEAD | tar -x -C "$code"
printf '固定コード: %s\n私有記録: %s\n' "$commit" "$work"
(
    cd "$code"
    env -i PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
        python3 -B -m unittest discover -s automation/tests -v
) > "$work/synthetic-tests.log" 2>&1
tail -n 4 "$work/synthetic-tests.log"
python3 -B "$code/runtime/seal-installed-snapshot.py" --root "$code" --source-commit "$commit" > "$work/installed-source-provenance.json"
chown -R root:mibo "$code" "$work"
chmod -R u=rwX,g=rX,o= "$code" "$work"
python3 -B "$code/runtime/prepare-core-v2-scoped.py" --out-dir "$work/readiness"
