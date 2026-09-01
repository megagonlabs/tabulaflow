#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$repo_root"

destination=data/ARCS/databases
if [[ -d $destination ]] && find "$destination" -mindepth 1 -print -quit | grep -q .; then
    echo "$destination is not empty" >&2
    exit 1
fi
mkdir -p "$destination"

cp data/BIRD-SQL/dev_20240627/dev_databases/financial/financial.sqlite "$destination/financial.sqlite"
cp data/BIRD-SQL/train/train_databases/professional_basketball/professional_basketball.sqlite "$destination/professional_basketball.sqlite"
cp data/BIRD-SQL/train/train_databases/retails/retails.sqlite "$destination/retails.sqlite"
cp data/BIRD-SQL/dev_20240627/dev_databases/codebase_community/codebase_community.sqlite "$destination/codebase_community.sqlite"
cp data/BIRD-SQL/dev_20240627/dev_databases/student_club/student_club.sqlite "$destination/student_club.sqlite"
cp ../ambig-text2sql/data/github_repos_date_sqlite/github_repos_date.sqlite "$destination/github_repos.sqlite"
