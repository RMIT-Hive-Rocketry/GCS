#!/usr/bin/env bash

set -euo pipefail

REPO="RMIT-Hive-Rocketry/GCS"

for id in $(gh api "repos/$REPO/actions/artifacts" --paginate | jq '.artifacts[].id'); do
  gh api -X DELETE "repos/$REPO/actions/artifacts/$id" >/dev/null
  echo "Deleted artifact $id"
done
