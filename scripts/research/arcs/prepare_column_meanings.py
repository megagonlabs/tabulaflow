import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

DATABASES = ("retails", "professional_basketball", "github_repos", "financial", "codebase_community", "student_club")
DEFAULT_INPUTS = (
    Path("data/BIRD-SQL_column_meaning/train_column_meaning.json"),
    Path("data/BIRD-SQL_column_meaning/dev_column_meaning.json"),
)


def collect_column_meanings(paths: list[Path]) -> dict[str, Any]:
    meanings: dict[str, Any] = {}
    for path in paths:
        source = json.loads(path.read_text())
        if not isinstance(source, dict):
            raise ValueError(f"Expected an object in {path}")
        for key, value in source.items():
            if any(key.startswith(f"{database}|") for database in DATABASES):
                if len(key.split("|")) != 3:
                    raise ValueError(f"Invalid column-meaning key: {key}")
                meanings[key] = value
    return meanings


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as temporary:
        json.dump(value, temporary, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect ARCS column meanings from the BIRD-SQL metadata.")
    parser.add_argument("--input", type=Path, action="append", dest="inputs")
    parser.add_argument("--output-path", type=Path, default=Path("data/ARCS/databases/column_meanings.json"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.output_path.exists() and not args.overwrite:
        raise FileExistsError(f"Output already exists: {args.output_path}; pass --overwrite to replace it")

    meanings = collect_column_meanings(args.inputs or list(DEFAULT_INPUTS))
    write_json_atomic(args.output_path, meanings)
    print(f"Wrote {len(meanings)} column meanings to {args.output_path}")


if __name__ == "__main__":
    main()
