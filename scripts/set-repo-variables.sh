#!/usr/bin/env bash
# Sets the three Actions variables the publish workflow reads on each listed
# repository, with the values setup-gcp.sh printed. Reports, and skips, a
# repository the gh login may not change.
#
# Usage: set-repo-variables.sh <workload-identity-provider> <service-account> <bucket> <owner/repo>...
set -uo pipefail

if [[ $# -lt 4 ]]; then
    echo "usage: $0 <workload-identity-provider> <service-account> <bucket> <owner/repo>..." >&2
    exit 2
fi
provider=$1
service_account=$2
bucket=$3
shift 3

failed=0
for repository in "$@"; do
    if gh variable set AGENT_DOCS_WORKLOAD_IDENTITY_PROVIDER --repo "$repository" --body "$provider" &&
        gh variable set AGENT_DOCS_SERVICE_ACCOUNT --repo "$repository" --body "$service_account" &&
        gh variable set AGENT_DOCS_BUCKET --repo "$repository" --body "$bucket"; then
        echo "$repository: set"
    else
        echo "$repository: could not set the variables" >&2
        failed=1
    fi
done
exit $failed
