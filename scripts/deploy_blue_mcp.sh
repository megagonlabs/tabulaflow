set -e

.venv/bin/python -u mcp/blue_postgres_example_hr_matching_curation_mcp.py &> log/postgres_example_hr_matching_curation_mcp.log &
.venv/bin/python -u mcp/blue_postgres_financial_mcp.py &> log/postgres_financial_mcp.log &
.venv/bin/python -u mcp/blue_postgres_github_repos_mcp.py &> log/postgres_github_repos_mcp.log &
wait
