import pytest

from backend.insights import _format_number, generate_insights


def test_format_number_formats_numeric_values():
    assert _format_number(1234.567) == "1,234.57"
    assert _format_number(10) == "10.00"
    assert _format_number(-25.5) == "-25.50"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "None"),
        ("invalid", "invalid"),
        ("12.5", "12.50"),
    ],
)
def test_format_number_handles_nonstandard_values(value, expected):
    assert _format_number(value) == expected


@pytest.mark.parametrize("analysis", [None, [], "invalid", 123])
def test_generate_insights_returns_empty_for_non_dict(analysis):
    assert generate_insights(analysis) == []


def test_generate_insights_returns_empty_for_failed_analysis():
    assert generate_insights({"success": False, "operation": "average"}) == []


def test_average_insight():
    result = generate_insights({
        "success": True,
        "operation": "average",
        "column": "Energy",
        "result": 125.5,
        "count": 20,
    })

    assert len(result) == 1
    assert result[0]["type"] == "summary"
    assert result[0]["severity"] == "info"
    assert result[0]["insight"] == (
        "The average value of Energy is 125.50 based on 20.00 records."
    )


def test_average_uses_default_column():
    result = generate_insights({
        "success": True,
        "operation": "average",
        "result": 5,
        "count": 2,
    })

    assert "average value of value" in result[0]["insight"]


def test_sum_insight():
    result = generate_insights({
        "success": True,
        "operation": "sum",
        "column": "Energy",
        "result": 2500,
        "count": 100,
    })

    assert result[0]["type"] == "summary"
    assert result[0]["severity"] == "info"
    assert result[0]["insight"] == (
        "The total value of Energy is 2,500.00 across 100.00 records."
    )


def test_highest_insight():
    result = generate_insights({
        "success": True,
        "operation": "highest",
        "column": "Temperature",
        "result": 45.678,
    })

    assert result == [{
        "type": "maximum",
        "severity": "info",
        "insight": "The highest value of Temperature is 45.68.",
    }]


def test_lowest_insight():
    result = generate_insights({
        "success": True,
        "operation": "lowest",
        "column": "Temperature",
        "result": -2.5,
    })

    assert result == [{
        "type": "minimum",
        "severity": "info",
        "insight": "The lowest value of Temperature is -2.50.",
    }]


def test_group_average_insights():
    result = generate_insights({
        "success": True,
        "operation": "group_average",
        "group_by": "City",
        "column": "Energy",
        "result": [
            {"group": "Karachi", "average": 120},
            {"group": "Lahore", "average": 80},
            {"group": "Peshawar", "average": 100},
        ],
    })

    assert len(result) == 2
    assert result[0]["type"] == "comparison"
    assert result[0]["severity"] == "info"
    assert "Karachi has the highest average Energy at 120.00" in result[0]["insight"]
    assert "Lahore has the lowest average at 80.00" in result[0]["insight"]

    assert result[1]["type"] == "group_summary"
    assert "compares Energy across 3 City groups" in result[1]["insight"]


def test_group_average_empty_results():
    result = generate_insights({
        "success": True,
        "operation": "group_average",
        "result": [],
    })

    assert result == []


def test_group_sum_insights():
    result = generate_insights({
        "success": True,
        "operation": "group_sum",
        "group_by": "City",
        "column": "Energy",
        "result": [
            {"group": "Karachi", "total": 900},
            {"group": "Lahore", "total": 400},
        ],
    })

    assert len(result) == 2
    assert result[0]["type"] == "comparison"
    assert "Karachi has the highest total Energy at 900.00" in result[0]["insight"]
    assert "Lahore has the lowest total at 400.00" in result[0]["insight"]
    assert result[1]["type"] == "group_summary"
    assert "compares total Energy across 2 City groups" in result[1]["insight"]


def test_group_sum_empty_results():
    result = generate_insights({
        "success": True,
        "operation": "group_sum",
        "result": [],
    })

    assert result == []


def test_group_highest_insight():
    result = generate_insights({
        "success": True,
        "operation": "group_highest",
        "column": "Energy",
        "group_by": "City",
        "result": {
            "group": "Karachi",
            "average": 150,
            "count": 25,
        },
    })

    assert result == [{
        "type": "maximum",
        "severity": "high",
        "insight": (
            "Karachi has the highest average Energy at 150.00 "
            "based on 25.00 records."
        ),
    }]


def test_group_lowest_insight():
    result = generate_insights({
        "success": True,
        "operation": "group_lowest",
        "column": "Energy",
        "result": {
            "group": "Peshawar",
            "average": 30,
            "count": 10,
        },
    })

    assert result == [{
        "type": "minimum",
        "severity": "low",
        "insight": (
            "Peshawar has the lowest average Energy at 30.00 "
            "based on 10.00 records."
        ),
    }]


@pytest.mark.parametrize(
    ("correlation", "strength", "direction"),
    [
        (0.10, "very weak", "positive"),
        (0.30, "weak", "positive"),
        (0.50, "moderate", "positive"),
        (0.70, "strong", "positive"),
        (0.90, "very strong", "positive"),
        (-0.10, "very weak", "negative"),
        (-0.30, "weak", "negative"),
        (-0.50, "moderate", "negative"),
        (-0.70, "strong", "negative"),
        (-0.90, "very strong", "negative"),
        (0.0, "very weak", "no"),
    ],
)
def test_correlation_strength_and_direction(correlation, strength, direction):
    result = generate_insights({
        "success": True,
        "operation": "correlation",
        "columns": ["Energy", "Temperature"],
        "result": correlation,
    })

    assert len(result) == 2
    assert result[0]["type"] == "correlation"
    assert result[0]["severity"] == "info"
    assert f"{strength} {direction} relationship" in result[0]["insight"]
    assert f"correlation: {correlation:.2f}" in result[0]["insight"]

    assert result[1]["type"] == "warning"
    assert "does not by itself prove causation" in result[1]["insight"]


def test_correlation_boundary_values():
    cases = [
        (0.20, "weak"),
        (0.40, "moderate"),
        (0.60, "strong"),
        (0.80, "very strong"),
    ]

    for correlation, expected_strength in cases:
        result = generate_insights({
            "success": True,
            "operation": "correlation",
            "columns": ["A", "B"],
            "result": correlation,
        })

        assert expected_strength in result[0]["insight"]


@pytest.mark.parametrize(
    ("columns", "correlation"),
    [
        (["Energy"], 0.5),
        (["Energy", "Temperature", "Humidity"], 0.5),
        (["Energy", "Temperature"], None),
        ([], 0.5),
    ],
)
def test_correlation_skips_invalid_input_shapes(columns, correlation):
    result = generate_insights({
        "success": True,
        "operation": "correlation",
        "columns": columns,
        "result": correlation,
    })

    assert result == []


def test_unknown_operation_returns_empty_list():
    assert generate_insights({
        "success": True,
        "operation": "unknown",
    }) == []
