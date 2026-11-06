#!/usr/bin/env bash
# Prints the bucket refs for a push, as two lines: the comma-separated immutable
# refs (the short sha, and the tag on a tag push), then the space-separated
# aliases. The default branch gets "latest" and its name, main gets "main" and
# "stable", and any other branch gets its name with "/" turned into "-".
#
# Usage: refs-for-push.sh <sha> <ref-type> <ref-name> <default-branch>
set -euo pipefail

if [[ $# -ne 4 ]]; then
    echo "usage: $0 <sha> <ref-type> <ref-name> <default-branch>" >&2
    exit 2
fi
sha=${1::7}
ref_type=$2
ref_name=$3
default_branch=$4

immutable=$sha
aliases=()
if [[ $ref_type == tag ]]; then
    immutable=$sha,$ref_name
elif [[ $ref_name == main ]]; then
    aliases=(main stable)
    if [[ $default_branch == main ]]; then
        aliases+=(latest)
    fi
elif [[ $ref_name == "$default_branch" ]]; then
    aliases=(latest "$ref_name")
else
    aliases=("${ref_name//\//-}")
fi
echo "$immutable"
echo "${aliases[*]}"
