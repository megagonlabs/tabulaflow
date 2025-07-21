import collections
from mintq.metadata_synthesizer.clusterer import YearMonthAffixClusterFunc


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
        fn = YearMonthAffixClusterFunc()
        groups = collections.defaultdict(list)
        for name in test_case:
            pattern, variation = fn.extract(name)
            groups[pattern].append(variation)

        assert len(groups) == 1
        desc = fn.summarize([v for v in groups[list(groups.keys())[0]]])
        assert desc == "YYYYMM from 202001 to 202005 except 202004"
