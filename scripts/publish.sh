#!/usr/bin/env bash
# Uploads a generated docs tree to gs://<bucket>/<slug>/<ref>/ for each
# immutable ref (a commit sha, a tag), then mirrors it to each alias directory,
# deleting whatever the alias held before. An immutable ref that already exists
# is left as it is.
#
# Usage: publish.sh <docs-dir> <bucket> <slug> <immutable-ref>[,<immutable-ref>...] [alias...]
set -euo pipefail

if [[ $# -lt 4 ]]; then
    echo "usage: $0 <docs-dir> <bucket> <slug> <immutable-ref>[,...] [alias...]" >&2
    exit 2
fi
site_dir=$1
bucket=gs://$2
slug=$3
IFS=, read -r -a immutable_refs <<< "$4"
shift 4
alias_cache_control="public, max-age=300"

if [[ ! -f $site_dir/index.md || ! -f $site_dir/index.html ]]; then
    echo "missing $site_dir/index.{md,html}: run generate.py first" >&2
    exit 1
fi

set_content_types() {
    gcloud storage objects update "$1/**.md" \
        --content-type="text/markdown; charset=utf-8" > /dev/null
    gcloud storage objects update "$1/llms.txt" \
        --content-type="text/plain; charset=utf-8" > /dev/null
}

for ref in "${immutable_refs[@]}"; do
    destination=$bucket/$slug/$ref
    if gcloud storage ls "$destination/index.html" > /dev/null 2>&1; then
        echo "$destination/ already exists; immutable refs are never rewritten"
        continue
    fi
    gcloud storage rsync --recursive "$site_dir" "$destination"
    set_content_types "$destination"
done

source_ref=$bucket/$slug/${immutable_refs[0]}
for alias in "$@"; do
    gcloud storage rsync --recursive --delete-unmatched-destination-objects \
        "$source_ref" "$bucket/$slug/$alias"
    gcloud storage objects update "$bucket/$slug/$alias/**" \
        --cache-control="$alias_cache_control" > /dev/null
done
