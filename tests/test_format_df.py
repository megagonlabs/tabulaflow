import pandas as pd
import numpy as np
from mintq.formatters.utils import format_df


class TestFormatDf:
    def test_basic_formatting(self) -> None:
        """Test basic DataFrame formatting."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        result = format_df(df)
        assert "a" in result
        assert "b" in result
        assert "1" in result
        assert "x" in result

    def test_null_handling_none(self) -> None:
        """Test that None values are displayed as [NULL]."""
        df = pd.DataFrame({"a": [1, None, 3], "b": ["x", None, "z"]})
        result = format_df(df)
        assert "[NULL]" in result

    def test_null_handling_nan(self) -> None:
        """Test that np.nan values are displayed as [NULL]."""
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        result = format_df(df)
        assert "[NULL]" in result
        assert "nan" not in result.lower() or "[null]" in result.lower()

    def test_null_handling_nat(self) -> None:
        """Test that pd.NaT values are displayed as [NULL]."""
        df = pd.DataFrame({"dt": [pd.Timestamp("2020-01-01"), pd.NaT, pd.Timestamp("2020-01-03")]})
        result = format_df(df)
        assert "[NULL]" in result
        assert "NaT" not in result

    def test_row_limiting(self) -> None:
        """Test that rows are limited with ellipsis."""
        df = pd.DataFrame({"a": list(range(10))})
        result = format_df(df, max_visible_rows=5)
        assert "..." in result
        # Should have first rows and last rows
        assert "0" in result
        assert "9" in result

    def test_row_limiting_small_df(self) -> None:
        """Test that small DataFrames are not limited."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = format_df(df, max_visible_rows=5)
        assert "..." not in result

    def test_string_truncation(self) -> None:
        """Test that long strings are truncated."""
        long_string = "a" * 200
        df = pd.DataFrame({"a": [long_string]})
        result = format_df(df, max_cell_width=100)
        assert "..." in result
        assert long_string not in result
        # Should have beginning and end of string
        assert "aaaa" in result

    def test_string_truncation_short_strings(self) -> None:
        """Test that short strings are not truncated."""
        short_string = "hello"
        df = pd.DataFrame({"a": [short_string]})
        result = format_df(df, max_cell_width=100)
        assert short_string in result
        # Only one occurrence (not truncated)
        assert result.count("...") == 0 or "..." not in result.split("hello")[0]

    def test_numeric_not_truncated(self) -> None:
        """Test that numeric values are not truncated (preserved as-is)."""
        df = pd.DataFrame({"a": [12345, 67890]})
        result = format_df(df)
        assert "12345" in result
        assert "67890" in result

    def test_empty_dataframe(self) -> None:
        """Test handling of empty DataFrame."""
        df = pd.DataFrame({"a": [], "b": []})
        result = format_df(df)
        assert "a" in result
        assert "b" in result

    def test_mixed_types_with_nulls(self) -> None:
        """Test DataFrame with mixed types and null values."""
        df = pd.DataFrame(
            {
                "int_col": [1, 2, None],
                "float_col": [1.5, np.nan, 3.5],
                "str_col": ["a", None, "c"],
                "datetime_col": [pd.Timestamp("2020-01-01"), pd.NaT, pd.Timestamp("2020-01-03")],
            }
        )
        result = format_df(df)
        # print(result)
        # All nulls should be [NULL]
        assert result.count("[NULL]") == 4
        # No raw null representations
        assert "nan" not in result or "[NULL]" in result
        assert "NaT" not in result

    def test_tablefmt_parameter(self) -> None:
        """Test different table formats."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result_simple = format_df(df, tablefmt="simple")
        result_grid = format_df(df, tablefmt="grid")
        # Grid format has more structure
        assert result_simple != result_grid
        assert "+" in result_grid or "|" in result_grid
