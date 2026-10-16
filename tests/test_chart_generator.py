
import base64

import numpy as np
import pytest

from backend.chart_generator import generate_chart


@pytest.fixture
def chart_data():
    columns = ["City", "Consumption"]

    results = [
        {"City": "Karachi", "Consumption": 120},
        {"City": "Lahore", "Consumption": 95},
        {"City": "Peshawar", "Consumption": 80},
    ]

    return columns, results


def decode_plotly_array(values):
    """Decode numeric arrays serialized by PlotlyJSONEncoder."""
    if isinstance(values, dict) and "bdata" in values:
        dtype = values.get("dtype", "f8")
        raw = base64.b64decode(values["bdata"])

        dtype_map = {
            "i1": "int8",
            "u1": "uint8",
            "i2": "int16",
            "u2": "uint16",
            "i4": "int32",
            "u4": "uint32",
            "i8": "int64",
            "u8": "uint64",
            "f4": "float32",
            "f8": "float64",
        }

        numpy_dtype = dtype_map.get(dtype, dtype)
        return np.frombuffer(raw, dtype=numpy_dtype).tolist()

    return list(values)


@pytest.mark.parametrize(
    "chart_type",
    ["bar", "line", "pie", "scatter"],
)
def test_generate_supported_chart_types(chart_type, chart_data):
    columns, results = chart_data

    result = generate_chart(
        chart_type=chart_type,
        columns=columns,
        results=results,
        title="Power Consumption",
    )

    assert result["success"] is True
    assert result["chart_type"] == chart_type
    assert result["title"] == "Power Consumption"
    assert result["columns"] == columns
    assert isinstance(result["figure"], dict)
    assert "data" in result["figure"]
    assert "layout" in result["figure"]
    assert len(result["figure"]["data"]) > 0


def test_bar_chart_uses_correct_columns(chart_data):
    columns, results = chart_data

    result = generate_chart("bar", columns, results)

    assert result["success"] is True

    trace = result["figure"]["data"][0]

    assert list(trace["x"]) == [
        "Karachi",
        "Lahore",
        "Peshawar",
    ]
    assert decode_plotly_array(trace["y"]) == [120, 95, 80]


def test_line_chart_enables_markers(chart_data):
    columns, results = chart_data

    result = generate_chart("line", columns, results)

    assert result["success"] is True

    trace = result["figure"]["data"][0]

    assert trace["type"] == "scatter"
    assert trace["mode"] == "lines+markers"


def test_pie_chart_uses_names_and_values(chart_data):
    columns, results = chart_data

    result = generate_chart("pie", columns, results)

    assert result["success"] is True

    trace = result["figure"]["data"][0]

    assert list(trace["labels"]) == [
        "Karachi",
        "Lahore",
        "Peshawar",
    ]
    assert decode_plotly_array(trace["values"]) == [120, 95, 80]


def test_scatter_chart_uses_correct_columns(chart_data):
    columns, results = chart_data

    result = generate_chart("scatter", columns, results)

    assert result["success"] is True

    trace = result["figure"]["data"][0]

    assert list(trace["x"]) == [
        "Karachi",
        "Lahore",
        "Peshawar",
    ]
    assert decode_plotly_array(trace["y"]) == [120, 95, 80]


def test_chart_uses_plotly_white_template(chart_data):
    columns, results = chart_data

    result = generate_chart("bar", columns, results)

    assert result["success"] is True
    assert result["figure"]["layout"]["template"] is not None


def test_chart_with_custom_title(chart_data):
    columns, results = chart_data

    result = generate_chart(
        "bar",
        columns,
        results,
        title="Monthly Energy Report",
    )

    assert result["success"] is True
    assert result["title"] == "Monthly Energy Report"
    assert (
        result["figure"]["layout"]["title"]["text"]
        == "Monthly Energy Report"
    )


def test_empty_columns_returns_error():
    result = generate_chart(
        chart_type="bar",
        columns=[],
        results=[{"City": "Karachi", "Consumption": 100}],
    )

    assert result == {
        "success": False,
        "message": "No columns available for chart generation.",
    }


def test_empty_results_returns_error():
    result = generate_chart(
        chart_type="bar",
        columns=["City", "Consumption"],
        results=[],
    )

    assert result == {
        "success": False,
        "message": "No result data available for chart generation.",
    }


@pytest.mark.parametrize(
    "chart_type",
    ["bar", "line", "pie", "scatter"],
)
def test_chart_requires_two_columns(chart_type):
    result = generate_chart(
        chart_type=chart_type,
        columns=["City"],
        results=[{"City": "Karachi"}],
    )

    assert result["success"] is False
    assert result["message"] == (
        f"A {chart_type} chart requires at least two columns."
    )


def test_unsupported_chart_type_returns_error(chart_data):
    columns, results = chart_data

    result = generate_chart(
        chart_type="heatmap",
        columns=columns,
        results=results,
    )

    assert result == {
        "success": False,
        "message": "Unsupported chart type: heatmap",
    }


def test_chart_figure_is_json_serializable(chart_data):
    import json

    columns, results = chart_data

    result = generate_chart("bar", columns, results)

    assert result["success"] is True

    serialized = json.dumps(result["figure"])
    restored = json.loads(serialized)

    assert isinstance(restored, dict)
    assert "data" in restored
    assert "layout" in restored


def test_missing_requested_dataframe_column_returns_error():
    result = generate_chart(
        chart_type="bar",
        columns=["City", "MissingColumn"],
        results=[
            {"City": "Karachi", "Consumption": 100},
            {"City": "Lahore", "Consumption": 90},
        ],
    )

    assert result["success"] is False
    assert result["chart_type"] == "bar"
    assert result["message"].startswith(
        "Chart generation failed:"
    )


def test_invalid_results_structure_returns_error():
    result = generate_chart(
        chart_type="bar",
        columns=["City", "Consumption"],
        results=["invalid row"],
    )

    assert result["success"] is False
    assert result["chart_type"] == "bar"
    assert result["message"].startswith(
        "Chart generation failed:"
    )