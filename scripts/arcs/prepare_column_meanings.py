import argparse
import json
import os

DATABASES = ["retails", "professional_basketball", "github_repos", "financial", "codebase_community", "student_club"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_path", default="data/ARCS/databases/column_meanings.json")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    if os.path.exists(args.output_path):
        if not args.overwrite:
            print(f"{args.output_path} already exists")
            return
        else:
            os.remove(args.output_path)

    column_meaning_paths = [
        "data/BIRD-SQL_column_meaning/train_column_meaning.json",
        "data/BIRD-SQL_column_meaning/dev_column_meaning.json",
    ]

    all_column_meanings = []
    for column_meaning_path in column_meaning_paths:
        with open(column_meaning_path, "r") as f:
            column_meanings = json.load(f)
            all_column_meanings += list(column_meanings.items())

    res = {}
    for db in DATABASES:
        for key, value in all_column_meanings:
            if key.startswith(db + "|"):
                assert len(key.split("|")) == 3, f"Key {key} is not valid"
                res[key] = value

    with open(args.output_path, "w") as f:
        json.dump(res, f, indent=2)
    print(f"{len(res)} column meanings saved to {args.output_path}")


if __name__ == "__main__":
    main()
