# Exit if data/ARCS/databases exists and is not empty
if [ -d "data/ARCS/databases" ] && [ -n "$(ls -A data/ARCS/databases)" ]; then
    echo "data/ARCS/databases exists and is not empty"
    exit 1
fi

cp data/BIRD-SQL/dev_20240627/dev_databases/financial/financial.sqlite data/ARCS/databases/financial.sqlite
cp data/BIRD-SQL/train/train_databases/professional_basketball/professional_basketball.sqlite data/ARCS/databases/professional_basketball.sqlite
cp data/BIRD-SQL/train/train_databases/retails/retails.sqlite data/ARCS/databases/retails.sqlite
cp data/BIRD-SQL/dev_20240627/dev_databases/codebase_community/codebase_community.sqlite data/ARCS/databases/codebase_community.sqlite
cp data/BIRD-SQL/dev_20240627/dev_databases/student_club/student_club.sqlite data/ARCS/databases/student_club.sqlite
cp ../ambig-text2sql/data/github_repos_date_sqlite/github_repos_date.sqlite data/ARCS/databases/github_repos.sqlite
