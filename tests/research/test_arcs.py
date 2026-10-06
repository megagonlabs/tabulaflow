from tabulaflow.research.benchmarks.arcs import ARCSDatasetLoader


def test_arcs_uses_public_split_names() -> None:
    assert ARCSDatasetLoader.splits == ["test", "base"]
