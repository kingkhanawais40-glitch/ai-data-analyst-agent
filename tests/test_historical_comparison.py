def calculate_trends(previous_health, current_health, previous_anomaly, current_anomaly):
    health_change = round(current_health - previous_health, 2)
    anomaly_change = round(current_anomaly - previous_anomaly, 2)

    if health_change > 0:
        health_trend = "Improved"
    elif health_change < 0:
        health_trend = "Declined"
    else:
        health_trend = "Stable"

    if anomaly_change < 0:
        anomaly_trend = "Improved"
    elif anomaly_change > 0:
        anomaly_trend = "Worsened"
    else:
        anomaly_trend = "Stable"

    return {
        "health_change": health_change,
        "anomaly_change": anomaly_change,
        "health_trend": health_trend,
        "anomaly_trend": anomaly_trend,
    }


def test_both_improved():
    result = calculate_trends(
        previous_health=94.53,
        current_health=96.20,
        previous_anomaly=14.77,
        current_anomaly=10.50,
    )

    assert result["health_change"] == 1.67
    assert result["anomaly_change"] == -4.27
    assert result["health_trend"] == "Improved"
    assert result["anomaly_trend"] == "Improved"


def test_health_declined_anomaly_worsened():
    result = calculate_trends(
        previous_health=94.53,
        current_health=90.00,
        previous_anomaly=14.77,
        current_anomaly=20.00,
    )

    assert result["health_change"] == -4.53
    assert result["anomaly_change"] == 5.23
    assert result["health_trend"] == "Declined"
    assert result["anomaly_trend"] == "Worsened"


def test_stable():
    result = calculate_trends(
        previous_health=94.53,
        current_health=94.53,
        previous_anomaly=14.77,
        current_anomaly=14.77,
    )

    assert result["health_change"] == 0.0
    assert result["anomaly_change"] == 0.0
    assert result["health_trend"] == "Stable"
    assert result["anomaly_trend"] == "Stable"


def test_health_improved_anomaly_worsened():
    result = calculate_trends(
        previous_health=90.00,
        current_health=95.00,
        previous_anomaly=10.00,
        current_anomaly=15.00,
    )

    assert result["health_trend"] == "Improved"
    assert result["anomaly_trend"] == "Worsened"


def test_health_declined_anomaly_improved():
    result = calculate_trends(
        previous_health=95.00,
        current_health=90.00,
        previous_anomaly=15.00,
        current_anomaly=10.00,
    )

    assert result["health_trend"] == "Declined"
    assert result["anomaly_trend"] == "Improved"