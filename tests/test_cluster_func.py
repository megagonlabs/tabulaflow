import collections
from mintq.metadata_synthesizer.clusterer import (
    IndexAffixClusterFunc,
    YearAffixClusterFunc,
    YearMonthAffixClusterFunc,
    DateAffixClusterFunc,
)


def test_index_affix_cluster_func() -> None:
    test_cases = [["A1", "A2", "A3", "A5"]]
    for test_case in test_cases:
        fn = IndexAffixClusterFunc(max_missing_ratio=0.2)
        groups = collections.defaultdict(list)
        for name in test_case:
            pattern, variation = fn.extract(name)
            groups[pattern].append(variation)

        assert len(groups) == 1
        desc = fn.summarize([v for v in groups[list(groups.keys())[0]]])
        assert desc == "# from 1 to 5 except 4"


def test_year_affix_cluster_func() -> None:
    test_cases = [
        ["2021", "2022", "2024", "2025"],
    ]
    for test_case in test_cases:
        fn = YearAffixClusterFunc(max_missing_ratio=0.2)
        groups = collections.defaultdict(list)
        for name in test_case:
            pattern, variation = fn.extract(name)
            groups[pattern].append(variation)

        assert len(groups) == 1
        desc = fn.summarize([v for v in groups[list(groups.keys())[0]]])
        assert desc == "YEAR from 2021 to 2025 except 2023"


def test_year_month_affix_cluster_func() -> None:
    test_cases = [
        [
            "202001",
            "202002",
            "202003",
            "202005",
        ],
        [
            "_202001",
            "_202002",
            "_202003",
            "_202005",
        ],
        [
            "_202001A",
            "_202002A",
            "_202003A",
            "_202005A",
        ],
    ]

    for test_case in test_cases:
        fn = YearMonthAffixClusterFunc(max_missing_ratio=0.2)
        groups = collections.defaultdict(list)
        for name in test_case:
            pattern, variation = fn.extract(name)
            groups[pattern].append(variation)

        assert len(groups) == 1
        desc = fn.summarize([v for v in groups[list(groups.keys())[0]]])
        assert desc == "YYYYMM from 202001 to 202005 except 202004"


def test_date_affix_cluster_func() -> None:
    test_cases = [
        [
            "stats_20200105",
            "stats_20200101",
            "stats_20200102",
            "stats_20200103",
        ]
    ]
    for test_case in test_cases:
        fn = DateAffixClusterFunc(max_missing_ratio=0.2)
        groups = collections.defaultdict(list)
        for name in test_case:
            pattern, variation = fn.extract(name)
            groups[pattern].append(variation)

        print(groups)
        assert len(groups) == 1
        desc = fn.summarize([v for v in groups[list(groups.keys())[0]]])
        assert desc == "YYYYMMDD from 20200101 to 20200105 except 20200104"
