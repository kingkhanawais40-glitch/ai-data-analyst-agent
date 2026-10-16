
from datetime import datetime
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_text(value: Any, default: str = "Not available") -> str:
    """Convert a value into readable text."""
    if value is None or value == "":
        return default

    return str(value)


def format_number(value: Any, decimals: int = 2) -> str:
    """Format numeric values safely."""
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "Not available"


def format_integer(value: Any) -> str:
    """Format integer-like values safely."""
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "Not available"


def get_metric(primary: dict, fallback: dict, key: str):
    """Read a metric from the primary dictionary or its fallback."""
    value = primary.get(key)

    if value is None:
        value = fallback.get(key)

    return value


def create_section_heading(text: str, styles: dict) -> Paragraph:
    """Create a consistent section heading."""
    return Paragraph(escape(text), styles["SectionHeading"])


def create_table(rows: list, column_widths: list | None = None) -> Table:
    """Create a professionally styled report table."""
    table = Table(
        rows,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#17365D"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8.5,
                ),
                (
                    "LEADING",
                    (0, 0),
                    (-1, -1),
                    11,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#D5DDE7"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F3F6FA"),
                    ],
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


# ============================================================
# PDF REPORT GENERATOR
# ============================================================

def generate_pdf_report(
    dataset: dict,
    validation: dict | None = None,
    anomalies: dict | None = None,
    intelligence: dict | None = None,
    historical: dict | None = None,
    insights: list | dict | None = None,
) -> bytes:
    """
    Generate a professional PDF report.

    Parameters:
        dataset: Dataset metadata.
        validation: Data-quality validation result.
        anomalies: Anomaly-detection result.
        intelligence: Dataset intelligence and recommendations.
        historical: Historical health comparison result.
        insights: Optional list or dictionary of saved insights.

    Returns:
        PDF document as bytes.
    """

    validation = validation if isinstance(validation, dict) else {}
    anomalies = anomalies if isinstance(anomalies, dict) else {}
    intelligence = intelligence if isinstance(intelligence, dict) else {}
    historical = historical if isinstance(historical, dict) else {}

    # --------------------------------------------------------
    # NORMALIZE INPUT STRUCTURES
    # --------------------------------------------------------

    dataset_data = dataset.get("dataset", dataset)

    if not isinstance(dataset_data, dict):
        dataset_data = {}

    validation_data = validation.get("validation", validation)

    if not isinstance(validation_data, dict):
        validation_data = {}

    validation_summary = validation_data.get("summary", {})

    if not isinstance(validation_summary, dict):
        validation_summary = {}

    anomaly_data = anomalies.get("anomalies", anomalies)

    if not isinstance(anomaly_data, dict):
        anomaly_data = {}

    intelligence_data = intelligence.get("intelligence", intelligence)

    if not isinstance(intelligence_data, dict):
        intelligence_data = {}

    historical_data = historical.get("history", historical)

    if isinstance(historical_data, list):
        historical_data = {"history": historical_data}

    if not isinstance(historical_data, dict):
        historical_data = {}

    # --------------------------------------------------------
    # EXTRACT QUALITY METRICS
    # --------------------------------------------------------

    quality_score = get_metric(
        validation_summary,
        validation_data,
        "quality_score",
    )

    if quality_score is None:
        quality_score = intelligence_data.get("quality_score")

    missing_values = get_metric(
        validation_summary,
        validation_data,
        "total_missing_values",
    )

    if missing_values is None:
        missing_values = intelligence_data.get("total_missing_values")

    duplicate_rows = get_metric(
        validation_summary,
        validation_data,
        "duplicate_rows",
    )

    if duplicate_rows is None:
        duplicate_rows = intelligence_data.get("duplicate_rows")

    # --------------------------------------------------------
    # EXTRACT ANOMALY METRICS
    # --------------------------------------------------------

    anomaly_percentage = anomaly_data.get(
        "anomaly_percentage",
        intelligence_data.get("anomaly_percentage"),
    )

    anomalous_records = anomaly_data.get(
        "unique_anomalous_records",
        anomaly_data.get(
            "anomalous_records",
            intelligence_data.get("unique_anomalous_records"),
        ),
    )

    anomaly_columns = anomaly_data.get(
        "columns_with_anomalies",
        anomaly_data.get(
            "anomaly_columns",
            intelligence_data.get("columns_with_anomalies"),
        ),
    )

    outlier_occurrences = anomaly_data.get(
        "total_outlier_occurrences",
        intelligence_data.get("total_outlier_occurrences"),
    )

    # --------------------------------------------------------
    # CREATE PDF DOCUMENT
    # --------------------------------------------------------

    pdf_buffer = BytesIO()

    dataset_name = safe_text(
        dataset_data.get("name"),
        "Dataset",
    )

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=19 * mm,
        title=f"Data Analysis Report - {dataset_name}",
        author="AI Data Analyst & BI Automation Agent",
        subject="Dataset Quality, Anomalies and Intelligence",
    )

    base_styles = getSampleStyleSheet()

    styles = {
        "Title": ParagraphStyle(
            "ReportTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#17365D"),
            spaceAfter=5,
        ),
        "Subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base_styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#526174"),
            spaceAfter=12,
        ),
        "SectionHeading": ParagraphStyle(
            "ReportSectionHeading",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#17365D"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "ReportBody",
            parent=base_styles["BodyText"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#243247"),
            spaceAfter=5,
        ),
        "Bullet": ParagraphStyle(
            "ReportBullet",
            parent=base_styles["BodyText"],
            fontSize=8.5,
            leading=12,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=5,
        ),
        "Small": ParagraphStyle(
            "ReportSmall",
            parent=base_styles["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748B"),
        ),
    }

    story = []

    # ========================================================
    # REPORT HEADER
    # ========================================================

    story.append(
        Paragraph(
            "AI Data Analyst",
            styles["Title"],
        )
    )

    story.append(
        Paragraph(
            "BI Automation Agent | Dataset Analysis Report",
            styles["Subtitle"],
        )
    )

    generated_at = datetime.now().astimezone().strftime(
        "%Y-%m-%d %H:%M %Z"
    )

    story.append(
        Paragraph(
            f"<b>Generated:</b> {escape(generated_at)}",
            styles["Body"],
        )
    )

    story.append(Spacer(1, 4 * mm))

    # ========================================================
    # SECTION 1: DATASET OVERVIEW
    # ========================================================

    story.append(
        create_section_heading(
            "1. Dataset Overview",
            styles,
        )
    )

    overview_rows = [
        ["Property", "Value"],
        [
            "Dataset ID",
            safe_text(
                dataset_data.get(
                    "id",
                    dataset_data.get("dataset_id"),
                )
            ),
        ],
        [
            "Dataset name",
            safe_text(dataset_data.get("name")),
        ],
        [
            "Source file",
            safe_text(dataset_data.get("file_name")),
        ],
        [
            "Total rows",
            format_integer(
                dataset_data.get(
                    "rows",
                    dataset_data.get("row_count"),
                )
            ),
        ],
        [
            "Total columns",
            format_integer(
                dataset_data.get(
                    "columns",
                    dataset_data.get("column_count"),
                )
            ),
        ],
        [
            "Created at",
            safe_text(dataset_data.get("created_at")),
        ],
    ]

    story.append(
        create_table(
            overview_rows,
            [47 * mm, 117 * mm],
        )
    )

    # ========================================================
    # SECTION 2: DATA QUALITY
    # ========================================================

    story.append(
        create_section_heading(
            "2. Data Quality Assessment",
            styles,
        )
    )

    quality_display = (
        f"{format_number(quality_score)} / 100"
        if quality_score is not None
        else "Not available"
    )

    quality_status = intelligence_data.get(
        "quality_status",
        validation_summary.get(
            "quality_status",
            validation_data.get("quality_status"),
        ),
    )

    quality_rows = [
        ["Metric", "Result"],
        ["Quality score", quality_display],
        ["Quality status", safe_text(quality_status)],
        ["Missing values", format_integer(missing_values)],
        ["Duplicate rows", format_integer(duplicate_rows)],
    ]

    story.append(
        create_table(
            quality_rows,
            [72 * mm, 92 * mm],
        )
    )

    # ========================================================
    # SECTION 3: ANOMALY DETECTION
    # ========================================================

    story.append(
        create_section_heading(
            "3. Anomaly Detection",
            styles,
        )
    )

    anomaly_display = (
        f"{format_number(anomaly_percentage)}%"
        if anomaly_percentage is not None
        else "Not available"
    )

    anomaly_rows = [
        ["Metric", "Result"],
        ["Anomaly percentage", anomaly_display],
        ["Unique anomalous records", format_integer(anomalous_records)],
        ["Columns affected", format_integer(anomaly_columns)],
        ["Outlier occurrences", format_integer(outlier_occurrences)],
        [
            "Most affected column",
            safe_text(
                intelligence_data.get(
                    "most_affected_column",
                    anomaly_data.get("most_affected_column"),
                )
            ),
        ],
        [
            "Overall risk",
            safe_text(intelligence_data.get("overall_risk")),
        ],
    ]

    story.append(
        create_table(
            anomaly_rows,
            [72 * mm, 92 * mm],
        )
    )

    # ========================================================
    # SECTION 4: KEY INSIGHTS
    # ========================================================

    story.append(
        create_section_heading(
            "4. Key Insights",
            styles,
        )
    )

    source_insights = insights

    if source_insights is None:
        source_insights = intelligence_data.get("insights", [])

    if isinstance(source_insights, dict):
        source_insights = source_insights.get("insights", [])

    if not isinstance(source_insights, list):
        source_insights = []

    rendered_insights = 0

    for item in source_insights[:30]:
        if isinstance(item, dict):
            item_text = item.get(
                "insight",
                item.get(
                    "description",
                    item.get(
                        "message",
                        item.get("title", ""),
                    ),
                ),
            )

            severity = item.get("severity")
        else:
            item_text = item
            severity = None

        if not item_text:
            continue

        prefix = ""

        if severity:
            prefix = (
                f"<b>{escape(str(severity))}:</b> "
            )

        story.append(
            Paragraph(
                f"• {prefix}{escape(str(item_text))}",
                styles["Bullet"],
            )
        )

        rendered_insights += 1

    if rendered_insights == 0:
        story.append(
            Paragraph(
                "No saved insights were available for this report.",
                styles["Body"],
            )
        )

    # ========================================================
    # SECTION 5: RECOMMENDATIONS
    # ========================================================

    story.append(
        create_section_heading(
            "5. Recommendations",
            styles,
        )
    )

    recommendations = intelligence_data.get(
        "recommendations",
        [],
    )

    if not isinstance(recommendations, list):
        recommendations = []

    rendered_recommendations = 0

    for item in recommendations[:30]:
        if isinstance(item, dict):
            item_text = item.get(
                "recommendation",
                item.get(
                    "description",
                    item.get(
                        "message",
                        item.get("title", ""),
                    ),
                ),
            )
        else:
            item_text = item

        if not item_text:
            continue

        story.append(
            Paragraph(
                f"• {escape(str(item_text))}",
                styles["Bullet"],
            )
        )

        rendered_recommendations += 1

    if rendered_recommendations == 0:
        story.append(
            Paragraph(
                "No recommendations were available from the current analysis.",
                styles["Body"],
            )
        )

    # ========================================================
    # SECTION 6: HISTORICAL COMPARISON
    # ========================================================

    story.append(
        create_section_heading(
            "6. Historical Health Comparison",
            styles,
        )
    )

    has_comparison = bool(
        historical_data.get("has_comparison")
    )

    current_snapshot = historical_data.get(
        "current_snapshot"
    )

    previous_snapshot = historical_data.get(
        "previous_snapshot"
    )

    if (
        has_comparison
        and isinstance(current_snapshot, dict)
        and isinstance(previous_snapshot, dict)
    ):
        history_rows = [
            [
                "Metric",
                "Previous",
                "Current",
                "Change",
            ],
            [
                "Quality score",
                format_number(
                    previous_snapshot.get("quality_score")
                ),
                format_number(
                    current_snapshot.get("quality_score")
                ),
                format_number(
                    historical_data.get("health_change")
                ),
            ],
            [
                "Anomaly percentage",
                f"{format_number(previous_snapshot.get('anomaly_percentage'))}%",
                f"{format_number(current_snapshot.get('anomaly_percentage'))}%",
                f"{format_number(historical_data.get('anomaly_change'))}%",
            ],
            [
                "Health trend",
                "—",
                safe_text(
                    historical_data.get("health_trend")
                ),
                "—",
            ],
            [
                "Anomaly trend",
                "—",
                safe_text(
                    historical_data.get("anomaly_trend")
                ),
                "—",
            ],
        ]

        story.append(
            create_table(
                history_rows,
                [
                    40 * mm,
                    35 * mm,
                    35 * mm,
                    54 * mm,
                ],
            )
        )

    else:
        story.append(
            Paragraph(
                "Historical comparison is not available yet. "
                "At least two saved health snapshots are required "
                "to compare changes over time.",
                styles["Body"],
            )
        )

    # ========================================================
    # REPORT FOOTNOTE
    # ========================================================

    story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            "This report summarizes the analysis results available "
            "at generation time. Automated anomaly flags and "
            "recommendations should be reviewed in the context "
            "of the dataset.",
            styles["Small"],
        )
    )

    # ========================================================
    # PAGE FOOTER
    # ========================================================

    def add_page_number(canvas, doc):
        canvas.saveState()

        canvas.setStrokeColor(
            colors.HexColor("#D5DDE7")
        )

        canvas.line(
            18 * mm,
            13 * mm,
            A4[0] - 18 * mm,
            13 * mm,
        )

        canvas.setFont("Helvetica", 8)

        canvas.setFillColor(
            colors.HexColor("#64748B")
        )

        canvas.drawString(
            18 * mm,
            8 * mm,
            "AI Data Analyst & BI Automation Agent",
        )

        canvas.drawRightString(
            A4[0] - 18 * mm,
            8 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return pdf_buffer.getvalue()
