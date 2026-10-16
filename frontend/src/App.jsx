import { useEffect, useRef, useState } from "react";
import Plot from "react-plotly.js";
import "./App.css";
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");


function JsonViewer({ value, depth = 0 }) {
  if (value === null) {
    return <span className="json-value-null">null</span>;
  }

  if (typeof value === "string") {
    return (
      <span className="json-value-string">
        {JSON.stringify(value)}
      </span>
    );
  }

  if (typeof value === "number") {
    return (
      <span className="json-value-number">{value}</span>
    );
  }

  if (typeof value === "boolean") {
    return (
      <span className="json-value-boolean">
        {String(value)}
      </span>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="json-value-empty">Empty array</span>;
    }

    return (
      <div className="json-viewer-array">
        {value.map((item, index) => (
          <details
            className="json-viewer-item"
            key={index}
            open={depth === 0 && value.length <= 5}
          >
            <summary>
              Item {index + 1}
            </summary>
            <div className="json-viewer-nested">
              <JsonViewer value={item} depth={depth + 1} />
            </div>
          </details>
        ))}
      </div>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value);

    if (entries.length === 0) {
      return <span className="json-value-empty">Empty object</span>;
    }

    return (
      <div className="json-viewer-object">
        {entries.map(([key, item]) => (
          <div className="json-viewer-row" key={key}>
            <div className="json-viewer-key">
              {key.replaceAll("_", " ")}
            </div>
            <div className="json-viewer-value">
              <JsonViewer value={item} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return <span>{String(value)}</span>;
}



function AgentResultView({ value, stepName = "" }) {
  let result = value;

  // 1. Parse JSON strings when possible.
  if (typeof result === "string") {
    try {
      result = JSON.parse(result);
    } catch {
      return <pre className="agent-step-result-viewer">{result}</pre>;
    }
  }

  // 2. Detect Plotly figures in different backend response structures.
  const figureCandidates = [
    result?.visualization?.visualization?.chart?.figure,
    result?.visualization?.chart?.figure,
    result?.chart?.figure,
    result?.visualization?.figure,
    result?.figure,
    result?.visualization?.visualization?.figure,
    result?.visualization?.chart,
    result?.chart,
    result,
  ];

  const figure = figureCandidates.find(
    (candidate) =>
      candidate &&
      Array.isArray(candidate.data) &&
      candidate.layout &&
      typeof candidate.layout === "object"
  );

  const stepNameLower = String(stepName).toLowerCase();

  const isVisualization =
    stepNameLower.includes("visual") ||
    stepNameLower.includes("chart") ||
    Boolean(figure);

  // 3. Render the actual interactive Plotly chart.
  if (isVisualization && figure) {
    return (
      <div className="agent-plotly-chart">
        <Plot
          data={figure.data}
          layout={{
            autosize: true,
            ...figure.layout,
            width: undefined,
          }}
          config={{
            responsive: true,
            displaylogo: false,
          }}
          useResizeHandler
          style={{
            width: "100%",
            height: "460px",
          }}
        />

        <details className="agent-step-details">
          <summary>View Chart Data</summary>

          <div className="agent-step-result-viewer">
            <JsonViewer value={result} />
          </div>
        </details>
      </div>
    );
  }

  // 4. Keep normal results readable as JSON.
  return <JsonViewer value={result} />;
}

function App() {
  const fileInputRef = useRef(null);

  const [dataset, setDataset] = useState(null);
  const [validation, setValidation] = useState(null);
  const [anomalies, setAnomalies] = useState(null);

  const [uploading, setUploading] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [error, setError] = useState("");

  const [severityFilter, setSeverityFilter] = useState("all");
  const [columnSearch, setColumnSearch] = useState("");
  const [sortBy, setSortBy] = useState("outlier_count");
  const [sortOrder, setSortOrder] = useState("desc");

  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [history, setHistory] = useState(null);
  const [intelligence, setIntelligence] = useState(null);

  const [businessQuestion, setBusinessQuestion] = useState("");
const [businessAnswer, setBusinessAnswer] = useState(null);
const [businessQuestionLoading, setBusinessQuestionLoading] = useState(false);


  // =========================
  // AGENT EXECUTION ENGINE
  // =========================

  const [executionQuestion, setExecutionQuestion] = useState(
    "Find unusual power usage"
  );

  const [executionData, setExecutionData] = useState(null);
  const [executionLoading, setExecutionLoading] = useState(false);
  const [executionError, setExecutionError] = useState("");


  // =========================
  // HELPERS
  // =========================

  const formatNumber = (value) => {
    if (value === null || value === undefined || value === "") {
      return "0";
    }

    return Number(value).toLocaleString();
  };

  const formatPercentage = (value) => {
    return `${Number(value || 0).toFixed(2)}%`;
  };

  const getQualityStatus = (score) => {
    const value = Number(score);

    if (value >= 90) {
      return {
        label: "Excellent",
        className: "status-excellent",
      };
    }

    if (value >= 75) {
      return {
        label: "Good",
        className: "status-good",
      };
    }

    if (value >= 60) {
      return {
        label: "Needs Attention",
        className: "status-warning",
      };
    }

    return {
      label: "Poor",
      className: "status-critical",
    };
  };

  const getAnomalyRateStatus = (rate) => {
    const value = Number(rate);

    if (value >= 20) {
      return {
        label: "High",
        className: "status-critical",
      };
    }

    if (value >= 10) {
      return {
        label: "Moderate",
        className: "status-warning",
      };
    }

    return {
      label: "Low",
      className: "status-good",
    };
  };


const getAffectedColumnsStatus = (count) => {
  // Historical value missing or unavailable
  if (count === null || count === undefined || count === "") {
    return {
      label: "Unavailable",
      className: "status-default",
    };
  }

  const value = Number(count);

  if (!Number.isFinite(value)) {
    return {
      label: "Unavailable",
      className: "status-default",
    };
  }

  if (value >= 10) {
    return {
      label: "High Attention",
      className: "status-critical",
    };
  }

  if (value >= 5) {
    return {
      label: "Monitor",
      className: "status-warning",
    };
  }

  return {
    label: "Low",
    className: "status-good",
  };
};

  const getSeverityClass = (severity) => {
    const normalized = String(severity || "").toLowerCase();

    if (normalized === "high") return "severity-high";
    if (normalized === "medium") return "severity-medium";
    if (normalized === "low") return "severity-low";

    return "severity-default";
  };

  // =========================
  // UPLOAD
  // =========================

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setUploading(true);
    setError("");

    setDataset(null);
setValidation(null);
setAnomalies(null);
setHistory(null);
setIntelligence(null);
setSelectedAnomaly(null);

    setSeverityFilter("all");
    setColumnSearch("");
    setSortBy("outlier_count");
    setSortOrder("desc");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const uploadResponse = await fetch(
        `${API_BASE_URL}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const uploadData = await uploadResponse.json();

      if (!uploadResponse.ok) {
        throw new Error(
          uploadData.detail ||
            uploadData.error ||
            "Dataset upload failed."
        );
      }

      setDataset(uploadData);
      localStorage.setItem(
  "ai_data_analyst_dataset",
  JSON.stringify(uploadData)
);

      const datasetId =
        uploadData.dataset_id ??
        uploadData.id ??
        uploadData.dataset?.dataset_id ??
        uploadData.dataset?.id;

      if (!datasetId) {
        throw new Error(
          "Dataset ID was not returned by the backend."
        );
      }

      // =========================
      // VALIDATION
      // =========================

      const validationResponse = await fetch(
        `${API_BASE_URL}/datasets/${datasetId}/validate`
      );

      const validationData = await validationResponse.json();

      if (!validationResponse.ok) {
        throw new Error(
          validationData.detail ||
            validationData.error ||
            "Dataset validation failed."
        );
      }

      setValidation(validationData);

      // =========================
      // ANOMALIES
      // =========================

      const anomalyResponse = await fetch(
        `${API_BASE_URL}/datasets/${datasetId}/anomalies`
      );

      const anomalyData = await anomalyResponse.json();

      if (!anomalyResponse.ok) {
        throw new Error(
          anomalyData.detail ||
            anomalyData.error ||
            "Anomaly detection failed."
        );
      }

      setAnomalies(anomalyData);

      const historyResponse = await fetch(
        `${API_BASE_URL}/datasets/${datasetId}/history`
      );

      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setHistory(historyData);
      } else {
        setHistory(null);
      }

      // =========================
      // AI INTELLIGENCE
      // =========================

      const intelligenceResponse = await fetch(
        `${API_BASE_URL}/datasets/${datasetId}/intelligence`
      );

      const intelligenceData =
        await intelligenceResponse.json();

      if (!intelligenceResponse.ok) {
        throw new Error(
          intelligenceData.detail ||
            intelligenceData.error ||
            "AI intelligence generation failed."
        );
      }

      setIntelligence(
        intelligenceData.intelligence || null
      );

    } catch (err) {
      console.error("Upload error:", err);

      setError(
        err.message ||
          "Something went wrong while analyzing the dataset."
      );
    } finally {
      setUploading(false);
    }
  };

      // =========================
  // RESTORE DATASET AFTER REFRESH
  // =========================

  useEffect(() => {
    const restoreDataset = async () => {
      try {
        // Dataset #20 is already stored in the backend.
        // We restore it without creating a new snapshot.
        const restoredDatasetId = 20;

        setUploading(true);
        setError("");

        // =========================
        // RESTORE DATASET PROFILE
        // =========================

        const profileResponse = await fetch(
          `${API_BASE_URL}/datasets/${restoredDatasetId}/profile`
        );

        if (!profileResponse.ok) {
          throw new Error(
            "Dataset profile could not be restored."
          );
        }

        const profileData =
          await profileResponse.json();

        setDataset({
          ...profileData,
          dataset_id: restoredDatasetId,
        });

        // =========================
        // RESTORE ANOMALIES
        // =========================

        const anomalyResponse = await fetch(
          `${API_BASE_URL}/datasets/${restoredDatasetId}/anomalies`
        );

        if (!anomalyResponse.ok) {
          throw new Error(
            "Dataset anomalies could not be restored."
          );
        }

        const anomalyData =
          await anomalyResponse.json();

        setAnomalies(anomalyData);

        // =========================
        // RESTORE HISTORY
        // =========================

        const historyResponse = await fetch(
          `${API_BASE_URL}/datasets/${restoredDatasetId}/history`
        );

        if (!historyResponse.ok) {
          throw new Error(
            "Dataset history could not be restored."
          );
        }

        const historyData =
          await historyResponse.json();

        setHistory(historyData);

        // =========================
        // RESTORE VALIDATION DATA
        // =========================
        //
        // IMPORTANT:
        // Do NOT call /validate here because
        // validation creates a new snapshot.
        //
        // Existing validation information is
        // already available from the latest
        // historical snapshot.
        //

        const currentSnapshot =
          historyData?.current_snapshot;

        if (currentSnapshot) {
          setValidation({
            quality_score:
              currentSnapshot.quality_score,

            data_quality_score:
              currentSnapshot.data_quality_score,

            total_missing_values:
              currentSnapshot.total_missing_values,

            duplicate_rows:
              currentSnapshot.duplicate_rows,

              flagged_columns:
  currentSnapshot.flagged_columns,

            anomaly_percentage:
              currentSnapshot.anomaly_percentage,

            anomalous_records:
              currentSnapshot.anomalous_records,

            anomaly_columns:
              currentSnapshot.anomaly_columns,

            total_outlier_occurrences:
              currentSnapshot.total_outlier_occurrences,
          });
        }
      } catch (err) {
        console.error(
          "Dataset restore error:",
          err
        );

        setError(
          err.message ||
            "Saved dataset could not be restored."
        );
      } finally {
        setUploading(false);
      }
    };

    restoreDataset();
  }, []);
  // =========================
  // NEW DATASET
  // =========================

  const handleNewDataset = () => {
    setDataset(null);
    localStorage.removeItem(
  "ai_data_analyst_dataset"
);
    setValidation(null);
    setAnomalies(null);
    setHistory(null);
    setIntelligence(null);
    setError("");
    setSelectedAnomaly(null);

    setSeverityFilter("all");
    setColumnSearch("");
    setSortBy("outlier_count");
    setSortOrder("desc");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleBusinessQuestion = async () => {
  const question = businessQuestion.trim();

  if (!question) {
    return;
  }

  if (!datasetId) {
    setBusinessAnswer({
      success: false,
      message: "Please upload or select a dataset first.",
    });
    return;
  }

  setBusinessQuestionLoading(true);
  setBusinessAnswer(null);

  try {
    const response = await fetch(
      `${API_BASE_URL}/datasets/${datasetId}/business-question`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          question,
        }),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Unable to process the business question."
      );
    }

    setBusinessAnswer(data.question || null);
  } catch (error) {
    setBusinessAnswer({
      success: false,
      question,
      answer:
        error.message ||
        "Unable to process the business question.",
    });
  } finally {
    setBusinessQuestionLoading(false);
  }
};


  // =========================
  // AGENT EXECUTION HANDLER
  // =========================

  const handleExecuteAnalysis = async () => {
    if (!datasetId) {
      setExecutionError("Please upload or restore a dataset first.");
      return;
    }

    if (!executionQuestion.trim()) {
      setExecutionError("Please enter an analysis question.");
      return;
    }

    setExecutionLoading(true);
    setExecutionError("");
    setExecutionData(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/datasets/${datasetId}/execute`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: executionQuestion.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.message ||
            "Agent execution failed."
        );
      }

      setExecutionData(data);
    } catch (err) {
      console.error("Agent execution error:", err);

      setExecutionError(
        err.message ||
          "Unable to execute the analysis. Check that the backend is running."
      );
    } finally {
      setExecutionLoading(false);
    }
  };


  const handleDownloadPdfReport = async () => {
    if (!datasetId) {
      setError("Please upload or restore a dataset first.");
      return;
    }

    setDownloadingReport(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/datasets/${datasetId}/report/pdf`
      );

      if (!response.ok) {
        let message = "Unable to generate the PDF report.";

        try {
          const errorData = await response.json();
          message = errorData.detail || message;
        } catch {
          // Keep the default error message if the response is not JSON.
        }

        throw new Error(message);
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = downloadUrl;
      link.download = `dataset_${datasetId}_report.pdf`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error("PDF report download error:", err);

      setError(
        err.message || "PDF download failed. Please check the backend."
      );
    } finally {
      setDownloadingReport(false);
    }
  };


  // =========================
  // DATASET INFO
  // =========================

  const datasetInfo = dataset?.dataset || dataset || {};

  const fileName =
    datasetInfo.filename ||
    datasetInfo.file_name ||
    datasetInfo.name ||
    "Uploaded dataset";

  const rowCount =
    datasetInfo.rows ??
    datasetInfo.row_count ??
    datasetInfo.total_rows ??
    datasetInfo.shape?.[0] ??
    0;

  const columnCount =
    datasetInfo.columns ??
    datasetInfo.column_count ??
    datasetInfo.total_columns ??
    datasetInfo.shape?.[1] ??
    0;

  const datasetId =
    datasetInfo.dataset_id ??
    datasetInfo.id ??
    dataset?.dataset_id ??
    dataset?.id;


  // =========================
  // VALIDATION DATA
  // =========================

  const validationSummary =
    validation?.validation?.summary ??
    validation?.summary ??
    validation ??
    {};

  const qualityScore =
    validationSummary.quality_score ??
    validationSummary.data_quality_score ??
    validation?.quality_score ??
    validation?.data_quality_score ??
    validation?.qualityScore ??
    validation?.score ??
    null;

  const getDatasetQualityScore = () => {
    const score = Number(qualityScore);

    if (!Number.isFinite(score)) {
      return 0;
    }

    return Math.max(0, Math.min(score, 100));
  };

  const datasetQualityScore = getDatasetQualityScore();

  const qualityLabel =
    validationSummary.quality_label ??
    validation?.quality_label ??
    (qualityScore !== null
      ? getQualityStatus(datasetQualityScore).label
      : "Not available");

  const totalMissingValues =
    validationSummary.total_missing_values ??
    validation?.total_missing_values ??
    0;

  const flaggedColumns =
  validationSummary.flagged_columns ??
  validation?.flagged_columns ??
  validation?.validation?.flagged_columns ??
  null;

  const duplicateRows =
    validationSummary.duplicate_rows ??
    validation?.duplicate_rows ??
    0;

  const validationColumns =
    validation?.validation?.columns ??
    validation?.columns ??
    [];



const columnsWithMissingData =
  validationColumns.filter(
    (column) =>
      Number(column.missing_values || 0) > 0
  ).length;


  const datasetWarnings =
    validation?.validation?.dataset_warnings ??
    validation?.dataset_warnings ??
    [];

  // =========================
  // HISTORICAL DATA HELPERS
  // =========================

  const getHistoryRecords = () => {
    const source =
      history?.history ??
      history?.records ??
      history?.snapshots ??
      history?.data ??
      history;

    if (Array.isArray(source)) {
      return source;
    }

    if (source && typeof source === "object") {
      const nested =
        source.history ??
        source.records ??
        source.snapshots ??
        source.data;

      if (Array.isArray(nested)) {
        return nested;
      }
    }

    return [];
  };

  const historyRecords = getHistoryRecords();

  const getHistoryQuality = (item) => {
    const value =
      item?.quality_score ??
      item?.data_quality_score ??
      item?.qualityScore ??
      item?.summary?.quality_score ??
      item?.validation?.summary?.quality_score;

    const score = Number(value);

    return Number.isFinite(score) ? score : 0;
  };

  const getHistoryAnomalyRate = (item) => {
    const value =
      item?.anomaly_percentage ??
      item?.anomaly_rate ??
      item?.anomalyPercentage ??
      0;

    const rate = Number(value);

    return Number.isFinite(rate) ? rate : 0;
  };

  // =========================
  // PHASE 7.17 — HISTORICAL COMPARISON
  // =========================

  const historyComparison =
    history &&
    typeof history === "object" &&
    !Array.isArray(history)
      ? history
      : {};

  const currentHistorySnapshot =
    historyComparison.current_snapshot ??
    (historyRecords.length > 0
      ? historyRecords[historyRecords.length - 1]
      : null);

  const previousHistorySnapshot =
    historyComparison.previous_snapshot ??
    (historyRecords.length > 1
      ? historyRecords[historyRecords.length - 2]
      : null);

  const hasHistoricalComparison =
    historyComparison.has_comparison === true ||
    Boolean(
      historyComparison.previous_snapshot ||
      historyRecords.length > 1
    );

  const previousHealthScore =
    previousHistorySnapshot !== null
      ? getHistoryQuality(previousHistorySnapshot)
      : null;

  const previousAnomalyRate =
    previousHistorySnapshot !== null
      ? getHistoryAnomalyRate(previousHistorySnapshot)
      : null;

  const healthScoreChange =
    historyComparison.health_change !== undefined &&
    historyComparison.health_change !== null
      ? Number(historyComparison.health_change)
      : previousHealthScore !== null &&
        currentHistorySnapshot !== null
      ? getHistoryQuality(currentHistorySnapshot) -
        previousHealthScore
      : null;

  const anomalyRateChange =
    historyComparison.anomaly_change !== undefined &&
    historyComparison.anomaly_change !== null
      ? Number(historyComparison.anomaly_change)
      : previousAnomalyRate !== null &&
        currentHistorySnapshot !== null
      ? getHistoryAnomalyRate(currentHistorySnapshot) -
        previousAnomalyRate
      : null;

  const healthTrend =
    historyComparison.health_trend ??
    (healthScoreChange === null
      ? "Baseline"
      : healthScoreChange > 0
      ? "Improved"
      : healthScoreChange < 0
      ? "Declined"
      : "Stable");

  const anomalyTrend =
    historyComparison.anomaly_trend ??
    (anomalyRateChange === null
      ? "Baseline"
      : anomalyRateChange < 0
      ? "Improved"
      : anomalyRateChange > 0
      ? "Worsened"
      : "Stable");

  const getComparisonTrendClass = (trend) => {
    const normalized = String(trend || "")
      .toLowerCase()
      .trim();

    if (
      normalized === "improved" ||
      normalized === "improving"
    ) {
      return "trend-positive";
    }

    if (
      normalized === "declined" ||
      normalized === "worsened"
    ) {
      return "trend-negative";
    }

    return "trend-neutral";
  };

  const getComparisonTrendIcon = (trend) => {
    const normalized = String(trend || "")
      .toLowerCase()
      .trim();

    if (
      normalized === "improved" ||
      normalized === "improving"
    ) {
      return "↑";
    }

    if (
      normalized === "declined" ||
      normalized === "worsened"
    ) {
      return "↓";
    }

    return "→";
  };

  const getHistoryDate = (item) => {
    return (
      item?.created_at ??
      item?.timestamp ??
      item?.analyzed_at ??
      item?.date ??
      item?.datetime ??
      null
    );
  };

  const formatHistoryDate = (value) => {
    if (!value) {
      return "Unknown date";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return String(value);
    }

    return date.toLocaleString("en-PK", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };


const getHistoryStatus = (score) => {
  const quality = Number(score);

  if (!Number.isFinite(quality)) {
    return {
      label: "Unavailable",
      className: "timeline-status-warning",
    };
  }

  if (quality >= 90) {
    return {
      label: "Excellent",
      className: "timeline-status-excellent",
    };
  }

  if (quality >= 75) {
    return {
      label: "Good",
      className: "timeline-status-good",
    };
  }

  if (quality >= 60) {
    return {
      label: "Needs Attention",
      className: "timeline-status-warning",
    };
  }

  return {
    label: "Critical",
    className: "timeline-status-critical",
  };
};


  const getTimelineRecords = () => {
    return historyRecords.map((item, index) => {
      const score = getHistoryQuality(item);
      const rate = getHistoryAnomalyRate(item);

      return {
        ...item,
        timelineIndex: index + 1,
        qualityScore: score,
        anomalyRate: rate,
        date: getHistoryDate(item),
        status: getHistoryStatus(score, rate),
      };
    });
  };

  const timelineRecords = getTimelineRecords();

  const getTimelineTrend = (currentRecord, previousRecord) => {
    if (!previousRecord) {
      return {
        label: "Baseline",
        className: "timeline-trend-baseline",
        icon: "●",
      };
    }

    const healthChange =
      Number(currentRecord.qualityScore) -
      Number(previousRecord.qualityScore);

    const anomalyChange =
      Number(currentRecord.anomalyRate) -
      Number(previousRecord.anomalyRate);

    if (healthChange > 0.5 && anomalyChange <= 0.5) {
      return {
        label: "Improved",
        className: "timeline-trend-improved",
        icon: "↑",
      };
    }

    if (healthChange < -0.5 || anomalyChange > 0.5) {
      return {
        label: "Declined",
        className: "timeline-trend-declined",
        icon: "↓",
      };
    }

    return {
      label: "Stable",
      className: "timeline-trend-stable",
      icon: "→",
    };
  };

  const intelligentTimelineRecords = timelineRecords.map(
    (record, index, records) => {
      const previousRecord =
        index > 0 ? records[index - 1] : null;

      return {
        ...record,
        trend: getTimelineTrend(record, previousRecord),
      };
    }
  );

  const timelineHealthScores =
    intelligentTimelineRecords.map(
      (record) => Number(record.qualityScore)
    );

  const timelineAverageHealth =
    timelineHealthScores.length > 0
      ? timelineHealthScores.reduce(
          (sum, score) => sum + score,
          0
        ) / timelineHealthScores.length
      : 0;

  const timelineBestHealth =
    timelineHealthScores.length > 0
      ? Math.max(...timelineHealthScores)
      : 0;

  const timelineLowestHealth =
    timelineHealthScores.length > 0
      ? Math.min(...timelineHealthScores)
      : 0;

  // =========================
  // END HISTORICAL DATA
  // =========================

  // =========================
  // ANOMALY SOURCE
  // =========================

  const anomalySource =
    anomalies?.anomalies &&
    typeof anomalies.anomalies === "object" &&
    !Array.isArray(anomalies.anomalies)
      ? anomalies.anomalies
      : anomalies || {};

  const rawAnomalyDetails =
    anomalySource?.anomalies ??
    anomalySource?.details ??
    anomalySource?.columns ??
    anomalies?.details ??
    anomalies?.columns ??
    anomalySource;

  const anomalyDetails =
    Array.isArray(rawAnomalyDetails)
      ? rawAnomalyDetails
      : rawAnomalyDetails &&
        typeof rawAnomalyDetails === "object"
      ? Object.entries(rawAnomalyDetails)
          .filter(
            ([, values]) =>
              values &&
              typeof values === "object" &&
              !Array.isArray(values)
          )
          .map(([column, values]) => ({
            column,
            ...(values || {}),
          }))
      : [];

  // =========================
  // ANOMALY METRICS
  // =========================

  const anomalyCount =
    anomalySource?.unique_anomalous_records ??
    anomalySource?.unique_anomalies ??
    anomalySource?.anomaly_count ??
    anomalySource?.total_anomalies ??
    anomalies?.unique_anomalous_records ??
    0;

  const anomalyPercentage =
    anomalySource?.anomaly_percentage ??
    anomalySource?.percentage ??
    anomalies?.anomaly_percentage ??
    0;

  const anomalyColumns =
    anomalySource?.columns_with_anomalies ??
    anomalies?.columns_with_anomalies ??
    anomalyDetails.length;

  const totalOutlierOccurrences =
    anomalySource?.total_outlier_occurrences ??
    anomalySource?.total_outliers ??
    anomalies?.total_outlier_occurrences ??
    0;

  // =========================
  // SEVERITY COUNTS
  // =========================

  const highSeverityCount = anomalyDetails.filter(
    (item) =>
      String(item.severity || "").toLowerCase() === "high"
  ).length;

  const mediumSeverityCount = anomalyDetails.filter(
    (item) =>
      String(item.severity || "").toLowerCase() === "medium"
  ).length;

  const lowSeverityCount = anomalyDetails.filter(
    (item) =>
      String(item.severity || "").toLowerCase() === "low"
  ).length;

  // =========================
  // MOST AFFECTED COLUMN
  // =========================

  const mostAffectedColumn =
    anomalyDetails.length > 0
      ? [...anomalyDetails].sort(
          (a, b) =>
            Number(b.outlier_count || 0) -
            Number(a.outlier_count || 0)
        )[0]?.column
      : null;

  // =========================
  // EXPLANATION
  // =========================

  const getAnomalyExplanation = (item) => {
    const severity = String(
      item.severity || ""
    ).toLowerCase();

    const high = Number(item.high_outliers || 0);
    const low = Number(item.low_outliers || 0);

    if (high > 0 && low > 0) {
      return "This column contains both unusually high and unusually low values compared with its normal IQR range.";
    }

    if (high > 0) {
      if (severity === "high") {
        return "This column has a high number of unusually large values. These observations are significantly above the normal IQR range.";
      }

      return "This column contains values that are higher than the expected IQR range.";
    }

    if (low > 0) {
      return "This column contains values that are lower than the expected IQR range.";
    }

    return "This column contains observations outside the normal statistical IQR range.";
  };

  // =========================
  // FILTER + SORT
  // =========================

  const filteredAndSortedAnomalies = [...anomalyDetails]
    .filter((item) => {
      const matchesSeverity =
        severityFilter === "all" ||
        String(item.severity || "").toLowerCase() ===
          severityFilter;

      const matchesColumn = String(item.column || "")
        .toLowerCase()
        .includes(columnSearch.toLowerCase().trim());

      return matchesSeverity && matchesColumn;
    })
    .sort((a, b) => {
      let valueA;
      let valueB;

      if (sortBy === "column") {
        valueA = String(a.column || "");
        valueB = String(b.column || "");

        return sortOrder === "asc"
          ? valueA.localeCompare(valueB)
          : valueB.localeCompare(valueA);
      }

      if (sortBy === "outlier_percentage") {
        valueA = Number(a.outlier_percentage || 0);
        valueB = Number(b.outlier_percentage || 0);
      } else if (sortBy === "high_outliers") {
        valueA = Number(a.high_outliers || 0);
        valueB = Number(b.high_outliers || 0);
      } else if (sortBy === "low_outliers") {
        valueA = Number(a.low_outliers || 0);
        valueB = Number(b.low_outliers || 0);
      } else {
        valueA = Number(a.outlier_count || 0);
        valueB = Number(b.outlier_count || 0);
      }

      return sortOrder === "asc"
        ? valueA - valueB
        : valueB - valueA;
    });

  // =========================
  // RESET FILTERS
  // =========================

  const resetFilters = () => {
    setSeverityFilter("all");
    setColumnSearch("");
    setSortBy("outlier_count");
    setSortOrder("desc");
  };

  // =========================
  // MODAL
  // =========================

  const openAnomalyDetails = (item) => {
    setSelectedAnomaly(item);
  };

  const closeAnomalyDetails = () => {
    setSelectedAnomaly(null);
  };

  const selectedDirection =
    Number(selectedAnomaly?.high_outliers || 0) > 0 &&
    Number(selectedAnomaly?.low_outliers || 0) > 0
      ? "Both High & Low"
      : Number(selectedAnomaly?.high_outliers || 0) > 0
      ? "High"
      : Number(selectedAnomaly?.low_outliers || 0) > 0
      ? "Low"
      : "N/A";

  // =========================
  // RENDER
  // =========================

  return (
    <div className="app">

      {/* =========================
          TOP BAR
      ========================= */}

      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark">AI</div>

          <div>
            <h1>AI Data Analyst</h1>
            <p>Data Quality &amp; BI Automation Agent</p>
          </div>
        </div>

        <div className="topbar-actions">
          {dataset && (
            <div className="system-status">
              <span className="status-dot"></span>
              Analysis Ready
            </div>
          )}


{dataset && (
  <button
    type="button"
    className="download-report-button"
    onClick={handleDownloadPdfReport}
    disabled={downloadingReport || uploading}
  >
    {downloadingReport
      ? "Generating PDF..."
      : "↓ Download PDF Report"}
  </button>
)}

<button
  type="button"
  className="new-dataset-button"
  onClick={handleNewDataset}
  disabled={uploading || downloadingReport}
>
  + New Dataset
</button>

        </div>
      </header>

      <div className="dashboard">

        {/* =========================
            WELCOME
        ========================= */}

        {!dataset && !uploading && (
          <section className="welcome-section">

            <div className="welcome-content">
              <span className="section-eyebrow">
                AI-POWERED ANALYTICS
              </span>

              <h2>Turn your data into decisions.</h2>

              <p>
                Upload an Excel or CSV dataset to automatically
                evaluate data quality, identify anomalies and
                generate actionable analytical insights.
              </p>

              <div className="welcome-points">
                <span>✓ Data Quality Validation</span>
                <span>✓ Statistical Anomaly Detection</span>
                <span>✓ Business Intelligence Ready</span>
              </div>
            </div>

            <div
              className="upload-card"
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="upload-icon">↑</div>

              <h3>Upload Dataset</h3>

              <p>
                Drop your data here or select a file
              </p>

              <span className="file-types">
                CSV · XLSX · XLS
              </span>

              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                Choose File
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleUpload}
                hidden
              />
            </div>

          </section>
        )}

        {/* =========================
            LOADING
        ========================= */}

        {uploading && (
          <section className="loading-card">
            <div className="loading-spinner"></div>

            <div>
              <span className="section-eyebrow">
                PROCESSING DATA
              </span>

              <h3>Analyzing Dataset...</h3>

              <p>
                Uploading, validating and detecting
                anomalies. Please wait.
              </p>
            </div>
          </section>
        )}

        {/* =========================
            ERROR
        ========================= */}

        {error && !uploading && (
          <section className="error-card">
            <div className="error-icon">!</div>

            <div>
              <span className="section-eyebrow">
                ANALYSIS ERROR
              </span>

              <h3>Something went wrong</h3>

              <p>{error}</p>
            </div>
          </section>
        )}

        {/* =========================
            DATASET DASHBOARD
        ========================= */}

        {dataset && !uploading && (
          <div>

            {/* =========================
                DATASET HEADER
            ========================= */}

            <section className="dataset-card">
              <div className="dataset-header-main">
                <div className="dataset-title-area">
                  <div className="dataset-file-icon">
                    XLS
                  </div>

                  <div className="dataset-title-content">
                    <span className="section-eyebrow">
                      ACTIVE DATASET
                    </span>

                    <h2>{fileName}</h2>

                    <p>
                      Dataset ID #{datasetId} · Currently loaded
                      for analysis
                    </p>
                  </div>
                </div>

                <div className="dataset-status">
                  <span className="dataset-status-dot"></span>
                  Ready for Analysis
                </div>
              </div>

              <div className="dataset-metadata">
                <div className="dataset-metadata-item">
                  <span className="metadata-icon">↕</span>

                  <div>
                    <span>Rows</span>
                    <strong>{formatNumber(rowCount)}</strong>
                  </div>
                </div>

                <div className="dataset-metadata-item">
                  <span className="metadata-icon">▦</span>

                  <div>
                    <span>Columns</span>
                    <strong>{formatNumber(columnCount)}</strong>
                  </div>
                </div>

                <div className="dataset-metadata-item">
                  <span className="metadata-icon">#</span>

                  <div>
                    <span>Dataset ID</span>
                    <strong>{datasetId}</strong>
                  </div>
                </div>

                <div className="dataset-metadata-item">
                  <span className="metadata-icon">✓</span>

                  <div>
                    <span>Analysis Status</span>
                    <strong>Ready</strong>
                  </div>
                </div>
              </div>
            </section>

            {/* =========================
                OVERVIEW STATS
            ========================= */}

            <section className="stats-grid">

              {/* Rows */}
              <div className="stat-card stat-card-primary">
                <div className="stat-card-top">
                  <span className="stat-label">Rows</span>
                  <span className="stat-icon">↕</span>
                </div>

                <strong className="stat-value">
                  {formatNumber(rowCount)}
                </strong>

                <small className="stat-description">
                  Total records
                </small>
              </div>

              {/* Columns */}
              <div className="stat-card">
                <div className="stat-card-top">
                  <span className="stat-label">Columns</span>
                  <span className="stat-icon">▦</span>
                </div>

                <strong className="stat-value">
                  {formatNumber(columnCount)}
                </strong>

                <small className="stat-description">
                  Dataset fields
                </small>
              </div>

              {/* Data Quality */}
              <div className="stat-card">
                <div className="stat-card-top">
                  <span className="stat-label">Data Quality</span>
                  <span className="stat-icon">✓</span>
                </div>

                <strong className="stat-value">
                  {qualityScore !== null
                    ? `${datasetQualityScore}%`
                    : "N/A"}
                </strong>

                <div className="stat-progress">
                  <div className="stat-progress-track">
                    <div
                      className="stat-progress-fill quality-progress"
                      style={{
                        width: `${datasetQualityScore}%`,
                      }}
                    ></div>
                  </div>
                </div>

                <div className="stat-status-row">
                  {qualityScore !== null && (
                    <span
                      className={`stat-status ${
                        getQualityStatus(
                          datasetQualityScore
                        ).className
                      }`}
                    >
                      <span className="status-dot"></span>

                      {
                        getQualityStatus(
                          datasetQualityScore
                        ).label
                      }
                    </span>
                  )}
                </div>
              </div>

              {/* Anomalous Records */}
              <div className="stat-card">
                <div className="stat-card-top">
                  <span className="stat-label">
                    Anomalous Records
                  </span>

                  <span className="stat-icon">!</span>
                </div>

                <strong className="stat-value">
                  {formatNumber(anomalyCount)}
                </strong>

                <div className="stat-mini-metric">
                  <span>of dataset</span>

                  <strong>
                    {formatPercentage(anomalyPercentage)}
                  </strong>
                </div>

                <div className="stat-status-row">
                  <span
                    className={`stat-status ${
                      Number(anomalyCount) > 0
                        ? "status-warning"
                        : "status-good"
                    }`}
                  >
                    <span className="status-dot"></span>

                    {Number(anomalyCount) > 0
                      ? "Requires Review"
                      : "No Anomalies"}
                  </span>
                </div>
              </div>

              {/* Anomaly Rate */}
              <div className="stat-card">
                <div className="stat-card-top">
                  <span className="stat-label">
                    Anomaly Rate
                  </span>

                  <span className="stat-icon">%</span>
                </div>

                <strong className="stat-value">
                  {formatPercentage(anomalyPercentage)}
                </strong>

                <div className="anomaly-meter">
                  <div className="anomaly-meter-track">
                    <div
                      className={`anomaly-meter-fill ${
                        Number(anomalyPercentage) >= 20
                          ? "meter-critical"
                          : Number(anomalyPercentage) >= 10
                          ? "meter-warning"
                          : "meter-good"
                      }`}
                      style={{
                        width: `${Math.min(
                          Number(anomalyPercentage || 0) * 2,
                          100
                        )}%`,
                      }}
                    ></div>
                  </div>

                  <div className="anomaly-meter-labels">
                    <span>0%</span>
                    <span>10%</span>
                    <span>20%+</span>
                  </div>
                </div>

                <div className="stat-status-row">
                  <span
                    className={`stat-status ${
                      getAnomalyRateStatus(
                        anomalyPercentage
                      ).className
                    }`}
                  >
                    <span className="status-dot"></span>

                    {
                      getAnomalyRateStatus(
                        anomalyPercentage
                      ).label
                    }
                  </span>
                </div>
              </div>

              {/* Affected Columns */}
              <div className="stat-card">
                <div className="stat-card-top">
                  <span className="stat-label">
                    Affected Columns
                  </span>

                  <span className="stat-icon">⚠</span>
                </div>

                <strong className="stat-value">
                  {formatNumber(anomalyColumns)}
                </strong>

                <div className="affected-column-visual">
                  <div className="affected-column-bars">
                    {Array.from({ length: 10 }).map(
                      (_, index) => (
                        <span
                          key={index}
                          className={
                            index <
                            Math.min(
                              Number(anomalyColumns || 0),
                              10
                            )
                              ? "affected-bar active"
                              : "affected-bar"
                          }
                        ></span>
                      )
                    )}
                  </div>
                </div>

                <div className="stat-status-row">
                  <span
                    className={`stat-status ${
                      getAffectedColumnsStatus(
                        anomalyColumns
                      ).className
                    }`}
                  >
                    <span className="status-dot"></span>

                    {
                      getAffectedColumnsStatus(
                        anomalyColumns
                      ).label
                    }
                  </span>
                </div>
              </div>

            </section>

            {/* =========================
                DATA QUALITY
            ========================= */}

            {validation?.validation?.summary && (
              <section className="quality-breakdown-section">

                <div className="section-heading">
                  <div>
                    <span className="section-eyebrow">
                      DATA QUALITY
                    </span>

                    <h2>Quality Breakdown</h2>

                    <p>
                      Overview of dataset validation and quality
                      indicators.
                    </p>
                  </div>
                </div>

                <div className="quality-overview-grid">

                  {/* Quality Score */}
                  <div className="quality-score-card">
                    <div className="quality-card-header">
                      <div>
                        <span className="quality-card-label">
                          Overall Quality
                        </span>

                        <strong className="quality-score-value">
                          {qualityScore !== null
                            ? `${datasetQualityScore}%`
                            : "N/A"}
                        </strong>
                      </div>

                      {qualityScore !== null && (
                        <span
                          className={`quality-status-badge ${
                            getQualityStatus(
                              datasetQualityScore
                            ).className
                          }`}
                        >
                          {
                            getQualityStatus(
                              datasetQualityScore
                            ).label
                          }
                        </span>
                      )}
                    </div>

                    <div className="quality-progress-large">
                      <div className="quality-progress-track">
                        <div
                          className="quality-progress-fill"
                          style={{
                            width: `${datasetQualityScore}%`,
                          }}
                        ></div>
                      </div>

                      <div className="quality-progress-labels">
                        <span>0%</span>
                        <span>50%</span>
                        <span>100%</span>
                      </div>
                    </div>

                    <p className="quality-score-description">
                      {qualityLabel} dataset quality based on the
                      current validation checks.
                    </p>
                  </div>

                  {/* Missing Values */}
                  <div className="quality-metric-card">
                    <div className="quality-metric-icon">
                      ∅
                    </div>

                    <div className="quality-metric-content">
                      <span>Missing Values</span>

                      <strong>
                        {Number(
                          totalMissingValues
                        ).toLocaleString()}
                      </strong>

                      <small>
                        Missing cells across dataset
                      </small>
                    </div>
                  </div>

                  {/* Flagged Columns */}
                  <div className="quality-metric-card">
                    <div className="quality-metric-icon">
                      !
                    </div>

                    <div className="quality-metric-content">
                      <span>Flagged Columns</span>

                      <strong>
  {flaggedColumns == null
    ? "—"
    : Number(flaggedColumns).toLocaleString()}
</strong>

                      <small>
                        Columns requiring attention
                      </small>
                    </div>
                  </div>

                  {/* Duplicate Rows */}
                  <div className="quality-metric-card">
                    <div className="quality-metric-icon">
                      ⧉
                    </div>

                    <div className="quality-metric-content">
                      <span>Duplicate Rows</span>

                      <strong>
                        {Number(
                          duplicateRows
                        ).toLocaleString()}
                      </strong>

                      <small>
                        Duplicate records detected
                      </small>
                    </div>
                  </div>

                </div>

                {datasetWarnings.length > 0 && (
                  <div className="quality-warning-box">
                    <div className="quality-warning-header">
                      <div>
                        <span className="quality-warning-label">
                          VALIDATION WARNINGS
                        </span>

                        <strong>
                          Dataset requires attention
                        </strong>
                      </div>

                      <span className="quality-warning-count">
                        {datasetWarnings.length}
                      </span>
                    </div>

                    <div className="quality-warning-list">
                      {datasetWarnings.map(
                        (warning, index) => (
                          <div
                            className="quality-warning-item"
                            key={`${warning.type}-${index}`}
                          >
                            <div className="warning-main">
                              <span
                                className={`warning-severity ${
                                  String(
                                    warning.severity || "info"
                                  ).toLowerCase() === "high"
                                    ? "warning-high"
                                    : String(
                                        warning.severity || "info"
                                      ).toLowerCase() === "medium"
                                    ? "warning-medium"
                                    : "warning-low"
                                }`}
                              >
                                {warning.severity || "info"}
                              </span>

                              <div>
                                <strong>
                                  {warning.message}
                                </strong>

                                <small>
                                  Validation rule:{" "}
                                  {warning.type || "General"}
                                </small>
                              </div>
                            </div>

                            {warning.count !== undefined && (
                              <span className="warning-count">
                                {Number(
                                  warning.count
                                ).toLocaleString()}
                              </span>
                            )}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}

              </section>
            )}

            {/* =========================
                COLUMN QUALITY
            ========================= */}

            {validationColumns.length > 0 && (
              <section className="column-quality-section">

                <div className="section-heading">
                  <div>
                    <span className="section-eyebrow">
                      COLUMN VALIDATION
                    </span>

                    <h2>Column Quality Intelligence</h2>

                    <p>
                      Columns requiring attention based on
                      missing values, uniqueness and validation
                      rules.
                    </p>
                  </div>
                </div>

                <div className="column-quality-summary">

                  <div className="column-summary-item">
                    <span>Total Columns</span>

                    <strong>
                      {formatNumber(
                        validationColumns.length
                      )}
                    </strong>
                  </div>

                  <div className="column-summary-item">
                    <span>Flagged Columns</span>

                    <strong>
                      {formatNumber(
                        validationColumns.filter(
                          (column) =>
                            column.flags?.length > 0 ||
                            Number(
                              column.missing_values || 0
                            ) > 0
                        ).length
                      )}
                    </strong>
                  </div>

                  <div className="column-summary-item">
                    <span>
                      Columns with Missing Data
                    </span>

                    <strong>
                      {formatNumber(
                        validationColumns.filter(
                          (column) =>
                            Number(
                              column.missing_values || 0
                            ) > 0
                        ).length
                      )}
                    </strong>
                  </div>

                </div>

                <div className="column-quality-table-wrapper">
                  <table className="column-quality-table">
                    <thead>
                      <tr>
                        <th>Column</th>
                        <th>Data Type</th>
                        <th>Missing Values</th>
                        <th>Unique Values</th>
                        <th>Quality Flags</th>
                      </tr>
                    </thead>

                    <tbody>
                      {validationColumns
                        .filter(
                          (column) =>
                            column.flags?.length > 0 ||
                            Number(
                              column.missing_values || 0
                            ) > 0
                        )
                        .map((column) => {
                          const missingPercentage =
                            Number(
                              column.missing_percentage || 0
                            );

                          const riskLevel =
                            missingPercentage >= 50
                              ? "critical"
                              : missingPercentage >= 20
                              ? "high"
                              : missingPercentage > 0
                              ? "medium"
                              : "low";

                          return (
                            <tr key={column.column}>

                              <td className="quality-column-name">
                                <div>
                                  <strong>
                                    {column.column}
                                  </strong>

                                  <small>
                                    {riskLevel === "critical"
                                      ? "Critical attention"
                                      : riskLevel === "high"
                                      ? "High attention"
                                      : riskLevel === "medium"
                                      ? "Needs review"
                                      : "Healthy"}
                                  </small>
                                </div>
                              </td>

                              <td>
                                <span className="column-type-badge">
                                  {column.data_type}
                                </span>
                              </td>

                              <td>
                                <div className="missing-quality-cell">
                                  <div className="missing-quality-header">
                                    <strong>
                                      {Number(
                                        column.missing_values || 0
                                      ).toLocaleString()}
                                    </strong>

                                    <span>
                                      {missingPercentage.toFixed(
                                        2
                                      )}
                                      %
                                    </span>
                                  </div>

                                  <div className="missing-progress-track">
                                    <div
                                      className={`missing-progress-fill missing-${riskLevel}`}
                                      style={{
                                        width: `${Math.min(
                                          missingPercentage,
                                          100
                                        )}%`,
                                      }}
                                    ></div>
                                  </div>
                                </div>
                              </td>

                              <td>
                                <span className="unique-value-count">
                                  {Number(
                                    column.unique_values || 0
                                  ).toLocaleString()}
                                </span>
                              </td>

                              <td>
                                <div className="column-flag-list">

                                  {column.flags?.map(
                                    (flag, index) => (
                                      <div
                                        className={`column-flag-item severity-${String(
                                          flag.severity || "info"
                                        ).toLowerCase()}`}
                                        key={`${flag.type}-${index}`}
                                      >
                                        <span>
                                          {flag.severity ||
                                            "info"}
                                        </span>

                                        <p>
                                          {flag.message}
                                        </p>
                                      </div>
                                    )
                                  )}

                                  {Number(
                                    column.missing_values || 0
                                  ) > 0 &&
                                    !column.flags?.some(
                                      (flag) =>
                                        flag.type ===
                                        "missing_values"
                                    ) && (
                                      <div
                                        className={`column-flag-item severity-${riskLevel}`}
                                      >
                                        <span>
                                          {riskLevel}
                                        </span>

                                        <p>
                                          {Number(
                                            column.missing_values
                                          ).toLocaleString()}{" "}
                                          missing values (
                                          {missingPercentage.toFixed(
                                            2
                                          )}
                                          %).
                                        </p>
                                      </div>
                                    )}

                                </div>
                              </td>

                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>

              </section>
            )}

            {/* =========================
                ANOMALY ANALYSIS TABLE
            ========================= */}

            {anomalies && (
              <section className="anomaly-analysis-section">

                <div className="section-heading">
                  <div>
                    <span className="section-eyebrow">
                      COLUMN LEVEL ANALYSIS
                    </span>

                    <h2>Anomaly Analysis</h2>

                    <p>
                      Detailed breakdown of detected outliers by
                      column and severity.
                    </p>
                  </div>

                  <div className="anomaly-table-count">
                    {anomalyDetails.length} columns
                  </div>
                </div>

                {anomalyDetails.length > 0 ? (
                  <div className="anomaly-table-wrapper">
                    <table className="anomaly-analysis-table">

                      <thead>
                        <tr>
                          <th>Column</th>
                          <th>Outlier Count</th>
                          <th>Anomaly Rate</th>
                          <th>Severity</th>
                          <th>Impact</th>
                        </tr>
                      </thead>

                      <tbody>
                        {[...anomalyDetails]
                          .sort(
                            (a, b) =>
                              Number(
                                b.outlier_count ??
                                  b.count ??
                                  0
                              ) -
                              Number(
                                a.outlier_count ??
                                  a.count ??
                                  0
                              )
                          )
                          .map((item, index) => {
                            const column =
                              item.column ??
                              item.name ??
                              `Column ${index + 1}`;

                            const outlierCount =
                              Number(
                                item.outlier_count ??
                                  item.count ??
                                  item.anomalies ??
                                  0
                              );

                            const percentage =
                              Number(
                                item.anomaly_percentage ??
                                  item.percentage ??
                                  item.anomaly_rate ??
                                  item.outlier_percentage ??
                                  0
                              );

                            const severity = String(
                              item.severity ?? "low"
                            ).toLowerCase();

                            const severityLabel =
                              severity
                                .charAt(0)
                                .toUpperCase() +
                              severity.slice(1);

                            const maxOutlierCount =
                              Math.max(
                                ...anomalyDetails.map(
                                  (entry) =>
                                    Number(
                                      entry.outlier_count ??
                                        entry.count ??
                                        entry.anomalies ??
                                        0
                                    )
                                ),
                                1
                              );

                            const impactWidth =
                              Math.min(
                                (outlierCount /
                                  maxOutlierCount) *
                                  100,
                                100
                              );

                            return (
                              <tr key={column}>
                                <td>
                                  <div className="anomaly-column-cell">
                                    <span className="anomaly-row-number">
                                      {String(
                                        index + 1
                                      ).padStart(2, "0")}
                                    </span>

                                    <div>
                                      <strong>
                                        {column}
                                      </strong>

                                      <small>
                                        Statistical outlier
                                        detection
                                      </small>
                                    </div>
                                  </div>
                                </td>

                                <td>
                                  <span className="anomaly-count-value">
                                    {formatNumber(
                                      outlierCount
                                    )}
                                  </span>
                                </td>

                                <td>
                                  <div className="anomaly-rate-cell">
                                    <strong>
                                      {formatPercentage(
                                        percentage
                                      )}
                                    </strong>

                                    <div className="anomaly-rate-track">
                                      <div
                                        className={`anomaly-rate-fill ${
                                          severity === "high"
                                            ? "rate-high"
                                            : severity ===
                                              "medium"
                                            ? "rate-medium"
                                            : "rate-low"
                                        }`}
                                        style={{
                                          width: `${Math.min(
                                            percentage,
                                            100
                                          )}%`,
                                        }}
                                      ></div>
                                    </div>
                                  </div>
                                </td>

                                <td>
                                  <span
                                    className={`anomaly-severity-badge severity-${severity}`}
                                  >
                                    <span className="severity-indicator"></span>
                                    {severityLabel}
                                  </span>
                                </td>

                                <td>
                                  <div className="anomaly-impact-cell">
                                    <div className="anomaly-impact-track">
                                      <div
                                        className={`anomaly-impact-fill impact-${severity}`}
                                        style={{
                                          width: `${impactWidth}%`,
                                        }}
                                      ></div>
                                    </div>

                                    <span>
                                      {index === 0
                                        ? "Highest"
                                        : index < 3
                                        ? "High"
                                        : severity ===
                                          "medium"
                                        ? "Moderate"
                                        : "Low"}
                                    </span>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                      </tbody>

                    </table>
                  </div>
                ) : (
                  <div className="empty-anomaly-state">
                    <div className="empty-anomaly-icon">
                      ✓
                    </div>

                    <strong>No anomalies detected</strong>

                    <p>
                      The current dataset does not contain any
                      detected statistical outliers.
                    </p>
                  </div>
                )}

              </section>
            )}

            {/* =========================
                SEVERITY SUMMARY
            ========================= */}

            {anomalies && (
              <section className="dashboard-section">

                <div className="section-heading">
                  <div>
                    <span className="section-eyebrow">
                      SEVERITY DISTRIBUTION
                    </span>

                    <h2>Smart Anomaly Summary</h2>

                    <p>
                      Automated classification of detected
                      anomaly severity.
                    </p>
                  </div>
                </div>

                <div className="severity-summary-grid">

                  <div className="severity-summary-card high">
                    <span>High Severity</span>
                    <strong>{highSeverityCount}</strong>
                    <small>Priority review</small>
                  </div>

                  <div className="severity-summary-card medium">
                    <span>Medium Severity</span>
                    <strong>{mediumSeverityCount}</strong>
                    <small>Requires attention</small>
                  </div>

                  <div className="severity-summary-card low">
                    <span>Low Severity</span>
                    <strong>{lowSeverityCount}</strong>
                    <small>Monitor variation</small>
                  </div>

                </div>

              </section>
            )}

            {/* =========================
                ANOMALY FILTER + TABLE
            ========================= */}

            {anomalies && (
              <section className="dashboard-section anomaly-analysis-section">

                <div className="section-heading">
                  <div>
                    <span className="section-eyebrow">
                      ANOMALY ANALYSIS
                    </span>

                    <h2>Detected Statistical Outliers</h2>

                    <p>
                      Filter, sort and inspect anomaly columns in
                      detail.
                    </p>
                  </div>

                  <span className="section-count">
                    {filteredAndSortedAnomalies.length} /{" "}
                    {anomalyDetails.length}
                  </span>
                </div>

                {/* FILTER BAR */}

                <div className="anomaly-controls">

                  <div className="anomaly-control">
                    <label>Severity</label>

                    <select
                      value={severityFilter}
                      onChange={(event) =>
                        setSeverityFilter(
                          event.target.value
                        )
                      }
                    >
                      <option value="all">
                        All Severities
                      </option>

                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>

                  <div className="anomaly-control anomaly-search">
                    <label>Search Column</label>

                    <input
                      type="text"
                      placeholder="Search column name..."
                      value={columnSearch}
                      onChange={(event) =>
                        setColumnSearch(
                          event.target.value
                        )
                      }
                    />
                  </div>

                  <div className="anomaly-control">
                    <label>Sort By</label>

                    <select
                      value={sortBy}
                      onChange={(event) =>
                        setSortBy(event.target.value)
                      }
                    >
                      <option value="outlier_count">
                        Outlier Count
                      </option>

                      <option value="outlier_percentage">
                        Outlier Percentage
                      </option>

                      <option value="high_outliers">
                        High Outliers
                      </option>

                      <option value="low_outliers">
                        Low Outliers
                      </option>

                      <option value="column">
                        Column Name
                      </option>
                    </select>
                  </div>

                  <button
                    type="button"
                    className="sort-order-button"
                    onClick={() =>
                      setSortOrder(
                        sortOrder === "desc"
                          ? "asc"
                          : "desc"
                      )
                    }
                  >
                    {sortOrder === "desc"
                      ? "↓ Desc"
                      : "↑ Asc"}
                  </button>

                  <button
                    type="button"
                    className="reset-filter-button"
                    onClick={resetFilters}
                  >
                    Reset
                  </button>

                </div>

                {/* TABLE */}

                {filteredAndSortedAnomalies.length > 0 ? (
                  <div className="anomaly-table-wrapper">

                    <table className="anomaly-table">

                      <thead>
                        <tr>
                          <th>Column</th>
                          <th>Outliers</th>
                          <th>Percentage</th>
                          <th>High</th>
                          <th>Low</th>
                          <th>Severity</th>
                          <th>Action</th>
                        </tr>
                      </thead>

                      <tbody>
                        {filteredAndSortedAnomalies.map(
                          (item, index) => (
                            <tr
                              key={`${item.column}-${index}`}
                            >
                              <td>
                                <strong>
                                  {item.column}
                                </strong>
                              </td>

                              <td>
                                {formatNumber(
                                  item.outlier_count
                                )}
                              </td>

                              <td>
                                {formatPercentage(
                                  item.outlier_percentage
                                )}
                              </td>

                              <td>
                                {formatNumber(
                                  item.high_outliers
                                )}
                              </td>

                              <td>
                                {formatNumber(
                                  item.low_outliers
                                )}
                              </td>

                              <td>
                                <span
                                  className={`severity-badge ${getSeverityClass(
                                    item.severity
                                  )}`}
                                >
                                  {item.severity ||
                                    "Unknown"}
                                </span>
                              </td>

                              <td>
                                <button
                                  type="button"
                                  className="view-details-button"
                                  onClick={() =>
                                    openAnomalyDetails(
                                      item
                                    )
                                  }
                                >
                                  View Details
                                </button>
                              </td>
                            </tr>
                          )
                        )}
                      </tbody>

                    </table>

                  </div>
                ) : (
                  <div className="filter-empty-state">
                    <div className="empty-icon">⌕</div>

                    <h4>
                      No matching anomaly columns
                    </h4>

                    <p>
                      Try changing the severity filter or
                      column search.
                    </p>

                    <button
                      type="button"
                      className="reset-filter-button"
                      onClick={resetFilters}
                    >
                      Reset Filters
                    </button>
                  </div>
                )}

              </section>
            )}

            {/* =========================
                RECOMMENDATIONS
            ========================= */}

            {anomalies && (
              <section className="recommendations-section">

                <div className="section-heading">
                  <div>
                    <span className="section-eyebrow">
                      DECISION SUPPORT
                    </span>

                    <h2>Actionable Recommendations</h2>

                    <p>
                      Suggested next steps based on the detected
                      anomaly patterns.
                    </p>
                  </div>

                  <div className="recommendation-count">
                    4 Actions
                  </div>
                </div>

                <div className="recommendations-grid">

                  {/* High Priority */}
                  <div className="recommendation-card recommendation-high">
                    <div className="recommendation-card-header">
                      <div className="recommendation-icon">
                        !
                      </div>

                      <div>
                        <span className="recommendation-priority">
                          HIGH PRIORITY
                        </span>

                        <h3>
                          Review high-severity columns
                        </h3>
                      </div>
                    </div>

                    <p>
                      Multiple columns contain strong
                      statistical deviations and should be
                      investigated before using the dataset
                      for important analysis.
                    </p>

                    <div className="recommendation-action">
                      <span>Recommended action</span>

                      <strong>
                        Validate unusual records and source
                        values
                      </strong>
                    </div>
                  </div>

                  {/* Most affected */}
                  <div className="recommendation-card recommendation-high">
                    <div className="recommendation-card-header">
                      <div className="recommendation-icon">
                        ↑
                      </div>

                      <div>
                        <span className="recommendation-priority">
                          HIGH PRIORITY
                        </span>

                        <h3>
                          Investigate the most affected column
                        </h3>
                      </div>
                    </div>

                    <p>
                      <strong>
                        {mostAffectedColumn ||
                          "No column identified"}
                      </strong>{" "}
                      has the highest number of detected
                      outlier values in the current analysis.
                    </p>

                    <div className="recommendation-action">
                      <span>Recommended action</span>

                      <strong>
                        Check source data, thresholds, and
                        business rules
                      </strong>
                    </div>
                  </div>

                  {/* Medium */}
                  <div className="recommendation-card recommendation-medium">
                    <div className="recommendation-card-header">
                      <div className="recommendation-icon">
                        M
                      </div>

                      <div>
                        <span className="recommendation-priority">
                          MEDIUM PRIORITY
                        </span>

                        <h3>
                          Review medium-severity patterns
                        </h3>
                      </div>
                    </div>

                    <p>
                      Medium-severity anomalies may represent
                      unusual operating conditions, legitimate
                      variation, or possible data-entry issues.
                    </p>

                    <div className="recommendation-action">
                      <span>Recommended action</span>

                      <strong>
                        Compare affected values with normal
                        ranges
                      </strong>
                    </div>
                  </div>

                  {/* Monitoring */}
                  <div className="recommendation-card recommendation-low">
                    <div className="recommendation-card-header">
                      <div className="recommendation-icon">
                        ✓
                      </div>

                      <div>
                        <span className="recommendation-priority">
                          MONITOR
                        </span>

                        <h3>
                          Continue monitoring low-severity
                          anomalies
                        </h3>
                      </div>
                    </div>

                    <p>
                      Low-severity anomalies are less urgent
                      but should remain visible during future
                      analysis to determine whether the pattern
                      persists.
                    </p>

                    <div className="recommendation-action">
                      <span>Recommended action</span>

                      <strong>
                        Monitor trends and confirm legitimate
                        variation
                      </strong>
                    </div>
                  </div>

                </div>
              </section>
            )}

            {/* =========================
                EXECUTIVE SUMMARY
            ========================= */}

            <section className="executive-summary-section">

              <div className="section-heading">

                <div>
                  <span className="section-eyebrow">
                    EXECUTIVE ANALYTICS
                  </span>

                  <h2>Dashboard Analytics Summary</h2>

                  <p>
                    High-level interpretation of the current
                    dataset health and analytical readiness.
                  </p>
                </div>

                <div
                  className={`readiness-badge ${
                    datasetQualityScore >= 90 &&
                    Number(anomalyPercentage) < 20
                      ? "readiness-ready"
                      : "readiness-review"
                  }`}
                >
                  {datasetQualityScore >= 90 &&
                  Number(anomalyPercentage) < 20
                    ? "Ready for Analysis"
                    : "Review Required"}
                </div>

              </div>

              <div className="executive-summary-grid">

                {/* Overall Health */}
                <div className="executive-summary-card executive-health-card">

                  <div className="executive-card-header">
                    <div>
                      <span>DATASET HEALTH</span>
                      <h3>Overall Condition</h3>
                    </div>

                    <div className="executive-card-icon">
                      ✓
                    </div>
                  </div>

                  <div className="executive-health-score">
                    <strong>
                      {formatNumber(
                        datasetQualityScore
                      )}
                    </strong>

                    <span>/ 100</span>
                  </div>

                  <div className="executive-health-track">
                    <div
                      className="executive-health-fill"
                      style={{
                        width: `${datasetQualityScore}%`,
                      }}
                    ></div>
                  </div>

                  <p>
                    The dataset has a{" "}
                    <strong>
                      {
                        getQualityStatus(
                          datasetQualityScore
                        ).label.toLowerCase()
                      }
                    </strong>{" "}
                    overall quality score.
                  </p>

                </div>

                {/* Key Finding */}
                <div className="executive-summary-card">

                  <div className="executive-card-header">
                    <div>
                      <span>KEY FINDING</span>
                      <h3>Anomaly Concentration</h3>
                    </div>

                    <div className="executive-card-icon executive-warning-icon">
                      !
                    </div>
                  </div>

                  <div className="executive-large-value">
                    {formatPercentage(
                      anomalyPercentage
                    )}
                  </div>

                  <p>
                    {formatNumber(anomalyCount)} unique
                    records contain detected anomalies
                    across{" "}
                    <strong>{anomalyColumns}</strong>{" "}
                    columns.
                  </p>

                  <div className="executive-mini-status">
                    <span
                      className={
                        Number(anomalyPercentage) >= 20
                          ? "mini-status-critical"
                          : Number(anomalyPercentage) >= 10
                          ? "mini-status-warning"
                          : "mini-status-good"
                      }
                    >
                      {
                        getAnomalyRateStatus(
                          anomalyPercentage
                        ).label
                      }
                    </span>

                    <span>Anomaly rate</span>
                  </div>

                </div>

                {/* Data Risk */}
                <div className="executive-summary-card">

                  <div className="executive-card-header">
                    <div>
                      <span>DATA RISK</span>
                      <h3>Missing Values</h3>
                    </div>

                    <div className="executive-card-icon executive-risk-icon">
                      !
                    </div>
                  </div>

                  <div className="executive-large-value">
                    {formatNumber(
                      totalMissingValues
                    )}
                  </div>

                  <p>
                    Missing values were detected across{" "}
                    <strong>
                      {columnsWithMissingData}
                    </strong>{" "}
                    columns.
                  </p>

                  <div className="executive-mini-status">
                    <span className="mini-status-warning">
                      Review
                    </span>

                    <span>Data completeness</span>
                  </div>

                </div>

                {/* Readiness */}
                <div className="executive-summary-card executive-readiness-card">

                  <div className="executive-card-header">
                    <div>
                      <span>
                        ANALYTICAL READINESS
                      </span>

                      <h3>
                        Recommended Next Step
                      </h3>
                    </div>

                    <div className="executive-card-icon executive-ready-icon">
                      →
                    </div>
                  </div>

                  <div className="executive-readiness-title">
                    {Number(anomalyPercentage) >= 20
                      ? "Investigate anomalies first"
                      : Number(totalMissingValues) > 0
                      ? "Review data completeness"
                      : "Proceed with analysis"}
                  </div>

                  <p>
                    Prioritize data-quality issues before
                    making high-impact business decisions from
                    this dataset.
                  </p>

                  <div className="executive-next-step">
                    <span>Suggested focus</span>

                    <strong>
                      {mostAffectedColumn ||
                        "Dataset quality"}
                    </strong>
                  </div>

                </div>

              </div>

              {/* Key Findings */}
              <div className="executive-findings-panel">

                <div className="executive-findings-header">
                  <div>
                    <span>ANALYTICS SNAPSHOT</span>
                    <h3>Key Findings</h3>
                  </div>
                </div>

                <div className="executive-findings-list">

                  <div className="executive-finding-item">
                    <span className="finding-number">
                      01
                    </span>

                    <div>
                      <strong>Dataset size</strong>

                      <p>
                        {formatNumber(rowCount)} records
                        across{" "}
                        {formatNumber(columnCount)}
                        columns are currently loaded for
                        analysis.
                      </p>
                    </div>
                  </div>

                  <div className="executive-finding-item">
                    <span className="finding-number">
                      02
                    </span>

                    <div>
                      <strong>
                        Quality assessment
                      </strong>

                      <p>
                        The current dataset quality score is{" "}
                        {formatNumber(
                          datasetQualityScore
                        )}
                        /100 with{" "}
                        {formatNumber(
                          totalMissingValues
                        )}{" "}
                        missing values detected.
                      </p>
                    </div>
                  </div>

                  <div className="executive-finding-item">
                    <span className="finding-number">
                      03
                    </span>

                    <div>
                      <strong>
                        Anomaly assessment
                      </strong>

                      <p>
                        {formatNumber(anomalyCount)}
                        unique records are anomalous,
                        with{" "}
                        {formatNumber(
                          totalOutlierOccurrences
                        )}{" "}
                        total outlier occurrences.
                      </p>
                    </div>
                  </div>

                  <div className="executive-finding-item">
                    <span className="finding-number">
                      04
                    </span>

                    <div>
                      <strong>Priority area</strong>

                      <p>
                        <strong>
                          {mostAffectedColumn ||
                            "No major column identified"}
                        </strong>{" "}
                        currently has the highest detected
                        anomaly concentration.
                      </p>
                    </div>
                  </div>

                </div>
              </div>

            </section>

            {/* =========================
                DATASET HEALTH SCORE
            ========================= */}

            <section className="health-visualization-section">

              <div className="section-heading">

                <div>
                  <span className="section-eyebrow">
                    DATA HEALTH
                  </span>

                  <h2>Dataset Health Score</h2>

                  <p>
                    Visual assessment of the dataset's overall
                    analytical quality.
                  </p>
                </div>

                <div
                  className={`health-status-pill ${
                    getQualityStatus(
                      datasetQualityScore
                    ).className
                  }`}
                >
                  {
                    getQualityStatus(
                      datasetQualityScore
                    ).label
                  }
                </div>

              </div>

              <div className="health-visualization-grid">

                {/* Main Score */}
                <div className="health-score-visual-card">

                  <div
                    className="health-score-ring"
                    style={{
                      "--health-score": datasetQualityScore,
                    }}
                  >
                    <div className="health-score-ring-inner">

                      <strong>
                        {formatNumber(
                          datasetQualityScore
                        )}
                      </strong>

                      <span>/ 100</span>

                    </div>
                  </div>

                  <div className="health-score-description">

                    <span>
                      OVERALL DATA QUALITY
                    </span>

                    <h3>
                      {
                        getQualityStatus(
                          datasetQualityScore
                        ).label
                      }{" "}
                      Dataset
                    </h3>

                    <p>
                      The dataset is currently suitable for
                      analysis, with some data-quality items
                      requiring attention.
                    </p>

                  </div>

                </div>

                {/* Health Components */}
                <div className="health-components-card">

                  <div className="health-components-header">
                    <span>
                      QUALITY COMPONENTS
                    </span>

                    <strong>
                      Current assessment
                    </strong>
                  </div>

                  <div className="health-component-list">

                    {/* Completeness */}
                    <div className="health-component">

                      <div className="health-component-info">

                        <div>
                          <strong>
                            Data Completeness
                          </strong>

                          <span>
                            {formatNumber(
                              totalMissingValues
                            )}{" "}
                            missing values
                          </span>
                        </div>

                        <strong
                          className={
                            Number(
                              totalMissingValues
                            ) > 0
                              ? "health-value-warning"
                              : "health-value-good"
                          }
                        >
                          {Number(
                            totalMissingValues
                          ) > 0
                            ? "Review"
                            : "Good"}
                        </strong>

                      </div>

                      <div className="health-component-track">
                        <div
                          className={`health-component-fill ${
                            Number(
                              totalMissingValues
                            ) > 0
                              ? "health-fill-warning"
                              : "health-fill-good"
                          }`}
                          style={{
                            width:
                              Number(
                                totalMissingValues
                              ) > 0
                                ? "75%"
                                : "100%",
                          }}
                        ></div>
                      </div>

                    </div>

                    {/* Duplicates */}
                    <div className="health-component">

                      <div className="health-component-info">

                        <div>
                          <strong>
                            Duplicate Records
                          </strong>

                          <span>
                            {formatNumber(
                              duplicateRows
                            )}{" "}
                            duplicates
                          </span>
                        </div>

                        <strong
                          className={
                            Number(
                              duplicateRows
                            ) > 0
                              ? "health-value-warning"
                              : "health-value-good"
                          }
                        >
                          {Number(
                            duplicateRows
                          ) > 0
                            ? "Review"
                            : "Clean"}
                        </strong>

                      </div>

                      <div className="health-component-track">
                        <div
                          className={`health-component-fill ${
                            Number(
                              duplicateRows
                            ) > 0
                              ? "health-fill-warning"
                              : "health-fill-good"
                          }`}
                          style={{
                            width:
                              Number(
                                duplicateRows
                              ) > 0
                                ? "70%"
                                : "100%",
                          }}
                        ></div>
                      </div>

                    </div>

                    {/* Flagged Columns */}
                    <div className="health-component">

                      <div className="health-component-info">

                        <div>
                          <strong>
                            Flagged Columns
                          </strong>


<span>
  {flaggedColumns == null
    ? "—"
    : formatNumber(flaggedColumns)}{" "}
  columns flagged
</span>

                        </div>


<strong
  className={
    flaggedColumns == null
      ? ""
      : Number(flaggedColumns) > 0
      ? "health-value-warning"
      : "health-value-good"
  }
>
  {flaggedColumns == null
    ? "Unavailable"
    : Number(flaggedColumns) > 0
    ? "Monitor"
    : "Clean"}
</strong>

                      </div>


<div className="health-component-track">
  {flaggedColumns != null && (
    <div
      className={`health-component-fill ${
        Number(flaggedColumns) > 0
          ? "health-fill-warning"
          : "health-fill-good"
      }`}
      style={{
        width:
          Number(flaggedColumns) > 0
            ? "80%"
            : "100%",
      }}
    ></div>
  )}
</div>


                    </div>

                    {/* Anomalies */}
                    <div className="health-component">

                      <div className="health-component-info">

                        <div>
                          <strong>
                            Anomaly Exposure
                          </strong>

                          <span>
                            {formatPercentage(
                              anomalyPercentage
                            )}{" "}
                            anomaly rate
                          </span>
                        </div>

                        <strong
                          className={
                            Number(
                              anomalyPercentage
                            ) >= 20
                              ? "health-value-critical"
                              : Number(
                                  anomalyPercentage
                                ) >= 10
                              ? "health-value-warning"
                              : "health-value-good"
                          }
                        >
                          {
                            getAnomalyRateStatus(
                              anomalyPercentage
                            ).label
                          }
                        </strong>

                      </div>

                      <div className="health-component-track">
                        <div
                          className={`health-component-fill ${
                            Number(
                              anomalyPercentage
                            ) >= 20
                              ? "health-fill-critical"
                              : Number(
                                  anomalyPercentage
                                ) >= 10
                              ? "health-fill-warning"
                              : "health-fill-good"
                          }`}
                          style={{
                            width: `${Math.min(
                              Number(
                                anomalyPercentage
                              ) * 3,
                              100
                            )}%`,
                          }}
                        ></div>
                      </div>

                    </div>

                  </div>
                </div>

              </div>

              {/* Health Interpretation */}
              <div className="health-interpretation">

                <div className="health-interpretation-icon">
                  i
                </div>

                <div>
                  <span>
                    HEALTH INTERPRETATION
                  </span>

                  <p>
                    The dataset has an overall quality score of{" "}
                    <strong>
                      {formatNumber(
                        datasetQualityScore
                      )}
                      /100
                    </strong>
                    . The strongest areas are reflected in the
                    overall quality score, while missing values,
                    flagged columns, and anomalies should be
                    reviewed before high-impact decisions.
                  </p>
                </div>

              </div>

            </section>

            {/* =========================================================
    PHASE 7.15.1 — HEALTH INSIGHTS CARDS
========================================================= */}
<section className="health-insights-section">
  <div className="section-heading">
    <div>
      <span className="section-eyebrow">HEALTH INTELLIGENCE</span>
      <h2>Health Insights</h2>
      <p>
        Smart interpretation of dataset quality, completeness,
        structural integrity, and anomaly exposure.
      </p>
    </div>

    <div className="health-insights-badge">
      AI Health Analysis
    </div>
  </div>

  <div className="health-insights-grid">

    {/* Overall Health */}
    <div className="health-insight-card">
      <div className="health-insight-top">
        <div className="health-insight-icon health-icon-blue">
          ✓
        </div>

        <span className="health-insight-label">
          OVERALL HEALTH
        </span>
      </div>

      <div className="health-insight-value">
        {getDatasetQualityScore().toFixed(2)}
        <span>/100</span>
      </div>

      <div className="health-insight-status status-excellent">
        {getQualityStatus(getDatasetQualityScore()).label}
      </div>

      <p>
        The dataset has a strong overall quality score and is
        suitable for further analytical processing.
      </p>
    </div>

    {/* Data Completeness */}
    <div className="health-insight-card">
      <div className="health-insight-top">
        <div className="health-insight-icon health-icon-warning">
          !
        </div>

        <span className="health-insight-label">
          DATA COMPLETENESS
        </span>
      </div>

      <div className="health-insight-value">
        {formatNumber(totalMissingValues)}
      </div>

      <div className="health-insight-status status-warning">
        Review
      </div>

      <p>
        Missing values were detected. Review affected columns
        before using the dataset for sensitive analysis.
      </p>
    </div>

    {/* Structural Integrity */}
    <div className="health-insight-card">
      <div className="health-insight-top">
        <div className="health-insight-icon health-icon-success">
          ✓
        </div>

        <span className="health-insight-label">
          STRUCTURAL INTEGRITY
        </span>
      </div>

      <div className="health-insight-value">
        {formatNumber(duplicateRows)}
      </div>

      <div className="health-insight-status status-good">
        Clean
      </div>

      <p>
        No duplicate records were detected, indicating strong
        structural consistency in the dataset.
      </p>
    </div>

    {/* Anomaly Exposure */}
    <div className="health-insight-card">
      <div className="health-insight-top">
        <div className="health-insight-icon health-icon-orange">
          ~
        </div>

        <span className="health-insight-label">
          ANOMALY EXPOSURE
        </span>
      </div>

      <div className="health-insight-value">
        {formatPercentage(anomalyPercentage)}
      </div>

      <div
        className={`health-insight-status ${
          getAnomalyRateStatus(anomalyPercentage).className
        }`}
      >
        {getAnomalyRateStatus(anomalyPercentage).label}
      </div>

      <p>
        Some records contain statistical anomalies and should
        be investigated before final decision-making.
      </p>
    </div>

    {/* Analysis Readiness */}
    <div className="health-insight-card">
      <div className="health-insight-top">
        <div className="health-insight-icon health-icon-purple">
          →
        </div>

        <span className="health-insight-label">
          ANALYSIS READINESS
        </span>
      </div>

      <div className="health-insight-value health-readiness-value">
        {getDatasetQualityScore() >= 90 &&
        Number(anomalyPercentage) < 20
          ? "Ready"
          : "Review"}
      </div>

      <div
        className={`health-insight-status ${
          getDatasetQualityScore() >= 90 &&
          Number(anomalyPercentage) < 20
            ? "status-good"
            : "status-warning"
        }`}
      >
        {getDatasetQualityScore() >= 90 &&
        Number(anomalyPercentage) < 20
          ? "Recommended"
          : "Attention Needed"}
      </div>

      <p>
        The current dataset can proceed to analytical workflows
        while identified quality issues remain visible.
      </p>
    </div>

    {/* Priority Action */}
    <div className="health-insight-card health-priority-card">
      <div className="health-insight-top">
        <div className="health-insight-icon health-icon-critical">
          !
        </div>

        <span className="health-insight-label">
          PRIORITY ACTION
        </span>
      </div>

      <div className="health-insight-priority-title">
        Review Data Quality
      </div>

      <div className="health-insight-status status-warning">
        Recommended
      </div>

      <p>
        Review missing values and high-severity anomaly columns
        before relying on the dataset for important decisions.
      </p>
    </div>

  </div>
</section>

{/* =========================================================
    PHASE 7.15.2 — SMART HEALTH INTERPRETATION
========================================================= */}
<section className="smart-health-section">
  <div className="section-heading">
    <div>
      <span className="section-eyebrow">
        SMART INTERPRETATION
      </span>
      <h2>Dataset Health Interpretation</h2>
      <p>
        Automated interpretation of the dataset's quality,
        risks, strengths, and analytical readiness.
      </p>
    </div>
  </div>

  <div className="smart-health-panel">

    {/* Main Interpretation */}
    <div className="smart-health-main">
      <div className="smart-health-main-icon">
        ✦
      </div>

      <div>
        <span className="smart-health-label">
          OVERALL ASSESSMENT
        </span>

        <h3>
          {getDatasetQualityScore() >= 90
            ? "Dataset is in excellent overall health"
            : getDatasetQualityScore() >= 75
            ? "Dataset is in good overall health"
            : getDatasetQualityScore() >= 60
            ? "Dataset requires quality improvements"
            : "Dataset requires significant quality improvements"}
        </h3>

        <p>
          The dataset currently has a{" "}
          <strong>
            {getDatasetQualityScore().toFixed(2)}%
          </strong>{" "}
          quality score with{" "}
          <strong>
            {formatPercentage(anomalyPercentage)}
          </strong>{" "}
          anomalous records. It is suitable for analytical
          workflows, but identified quality issues should be
          reviewed before high-impact decision-making.
        </p>
      </div>
    </div>

    {/* Interpretation Grid */}
    <div className="smart-health-grid">

      {/* Strengths */}
      <div className="smart-health-item">
        <div className="smart-health-item-header">
          <div className="smart-health-item-icon health-icon-success">
            ✓
          </div>

          <div>
            <span className="smart-health-item-label">
              STRENGTHS
            </span>
            <h4>What is working well</h4>
          </div>
        </div>

        <ul>
          {Number(
            duplicateRows
          ) === 0 && (
            <li>
              No duplicate records detected.
            </li>
          )}

          {getDatasetQualityScore() >= 90 && (
            <li>
              Overall data quality is excellent.
            </li>
          )}

          {Number(anomalyColumns) <= 10 && (
            <li>
              Anomalies are concentrated in a limited number
              of columns.
            </li>
          )}

          <li>
            Dataset structure is ready for analytical processing.
          </li>
        </ul>
      </div>

      {/* Weaknesses */}
      <div className="smart-health-item">
        <div className="smart-health-item-header">
          <div className="smart-health-item-icon health-icon-warning">
            !
          </div>

          <div>
            <span className="smart-health-item-label">
              AREAS TO REVIEW
            </span>
            <h4>What needs attention</h4>
          </div>
        </div>

        <ul>
          {Number(
            totalMissingValues
          ) > 0 && (
            <li>
              {formatNumber(
                totalMissingValues
              )}{" "}
              missing values require review.
            </li>
          )}

          {Number(anomalyPercentage) > 10 && (
            <li>
              Anomaly exposure is above the low-risk range.
            </li>
          )}

          {Number(anomalyColumns) > 0 && (
            <li>
              Detected anomalies should be investigated before
              final conclusions.
            </li>
          )}
        </ul>
      </div>

      {/* Risk */}
      <div className="smart-health-item">
        <div className="smart-health-item-header">
          <div className="smart-health-item-icon health-icon-orange">
            !
          </div>

          <div>
            <span className="smart-health-item-label">
              RISK ASSESSMENT
            </span>
            <h4>
              {Number(anomalyPercentage) >= 20
                ? "High analytical risk"
                : Number(anomalyPercentage) >= 10
                ? "Moderate analytical risk"
                : "Low analytical risk"}
            </h4>
          </div>
        </div>

        <p className="smart-health-risk-text">
          {Number(anomalyPercentage) >= 20
            ? "A high concentration of anomalous records may affect analytical reliability. Detailed investigation is recommended."
            : Number(anomalyPercentage) >= 10
            ? "A moderate level of anomalies is present. Results should be interpreted with appropriate caution."
            : "The anomaly level is relatively low and should have limited impact on most analytical workflows."}
        </p>
      </div>

      {/* Readiness */}
      <div className="smart-health-item">
        <div className="smart-health-item-header">
          <div className="smart-health-item-icon health-icon-blue">
            →
          </div>

          <div>
            <span className="smart-health-item-label">
              ANALYSIS READINESS
            </span>

            <h4>
              {getDatasetQualityScore() >= 90 &&
              Number(anomalyPercentage) < 20
                ? "Ready for analysis"
                : "Review before analysis"}
            </h4>
          </div>
        </div>

        <p className="smart-health-risk-text">
          {getDatasetQualityScore() >= 90 &&
          Number(anomalyPercentage) < 20
            ? "The dataset meets the current quality threshold and can proceed to analytical workflows."
            : "Resolve or review important quality issues before relying on analytical results."}
        </p>
      </div>

    </div>

    {/* Recommended Action */}
    <div className="smart-health-action">
      <div className="smart-health-action-icon">
        →
      </div>

      <div>
        <span className="smart-health-action-label">
          RECOMMENDED NEXT ACTION
        </span>

        <h4>
          Review missing values and high-severity anomalies
        </h4>

        <p>
          Start with columns containing the highest anomaly
          counts and investigate missing-value patterns before
          proceeding to deeper analysis.
        </p>
      </div>
    </div>

  </div>
</section>

{/* =========================================================
    PHASE 7.15.3 — HEALTH PRIORITY & RISK INDICATOR
========================================================= */}
<section className="health-risk-section">
  <div className="section-heading">
    <div>
      <span className="section-eyebrow">
        RISK INTELLIGENCE
      </span>
      <h2>Health Priority & Risk</h2>
      <p>
        Automated prioritization of the most important dataset
        quality and analytical risks.
      </p>
    </div>
  </div>

  <div className="health-risk-grid">

    {/* Overall Risk */}
    <div className="health-risk-card health-risk-main-card">
      <div className="health-risk-card-header">
        <div>
          <span className="health-risk-label">
            OVERALL RISK LEVEL
          </span>

          <h3>
            {Number(anomalyPercentage) >= 20 ||
            getDatasetQualityScore() < 60
              ? "High"
              : Number(anomalyPercentage) >= 10 ||
                getDatasetQualityScore() < 75
              ? "Moderate"
              : "Low"}
          </h3>
        </div>

        <div
          className={`health-risk-level-icon ${
            Number(anomalyPercentage) >= 20 ||
            getDatasetQualityScore() < 60
              ? "risk-icon-high"
              : Number(anomalyPercentage) >= 10 ||
                getDatasetQualityScore() < 75
              ? "risk-icon-moderate"
              : "risk-icon-low"
          }`}
        >
          !
        </div>
      </div>

      <div className="health-risk-meter">
        <div
          className={`health-risk-meter-fill ${
            Number(anomalyPercentage) >= 20 ||
            getDatasetQualityScore() < 60
              ? "risk-fill-high"
              : Number(anomalyPercentage) >= 10 ||
                getDatasetQualityScore() < 75
              ? "risk-fill-moderate"
              : "risk-fill-low"
          }`}
          style={{
            width: `${Math.min(
              Math.max(
                Number(anomalyPercentage) * 2,
                100 - getDatasetQualityScore()
              ),
              5
            )}%`,
          }}
        ></div>
      </div>

      <p>
        {Number(anomalyPercentage) >= 20 ||
        getDatasetQualityScore() < 60
          ? "Significant quality or anomaly risks require attention before analytical use."
          : Number(anomalyPercentage) >= 10 ||
            getDatasetQualityScore() < 75
          ? "The dataset has noticeable analytical risks that should be reviewed."
          : "The dataset currently presents a relatively low overall analytical risk."}
      </p>
    </div>

    {/* Priority Score */}
    <div className="health-risk-card">
      <span className="health-risk-label">
        PRIORITY SCORE
      </span>

      <div className="health-priority-score">
        {Math.round(
          Math.min(
            100,
            Math.max(
              Number(anomalyPercentage) * 2,
              100 - getDatasetQualityScore()
            )
          )
        )}
        <span>/100</span>
      </div>

      <div className="health-risk-status status-warning">
        Attention Required
      </div>

      <p>
        Higher scores indicate greater need for immediate
        data-quality investigation.
      </p>
    </div>

    {/* Primary Issue */}
    <div className="health-risk-card">
      <span className="health-risk-label">
        PRIMARY ISSUE
      </span>

      <div className="health-primary-issue">
        {Number(
          totalMissingValues
        ) > 0
          ? "Missing Values"
          : Number(anomalyPercentage) > 0
          ? "Statistical Anomalies"
          : "No Major Issues"}
      </div>

      <div
        className={`health-risk-status ${
          Number(
            totalMissingValues
          ) > 0
            ? "status-warning"
            : "status-good"
        }`}
      >
        {Number(
          totalMissingValues
        ) > 0
          ? "Review"
          : "Stable"}
      </div>

      <p>
        {Number(
          totalMissingValues
        ) > 0
          ? "Missing data is the first quality issue to investigate."
          : "No significant completeness issue is currently detected."}
      </p>
    </div>

    {/* Most Affected Area */}
    <div className="health-risk-card">
      <span className="health-risk-label">
        MOST AFFECTED AREA
      </span>

      <div className="health-primary-issue">
        {mostAffectedColumn || "No major anomaly"}
      </div>

      <div className="health-risk-status status-warning">
        Monitor
      </div>

      <p>
        This area has the highest detected anomaly concentration
        and should receive additional investigation.
      </p>
    </div>

  </div>

  {/* Priority Action */}
  <div className="health-priority-action">
    <div className="health-priority-action-number">
      01
    </div>

    <div className="health-priority-action-content">
      <span className="health-risk-label">
        HIGHEST PRIORITY
      </span>

      <h3>
        {Number(
          totalMissingValues
        ) > 0
          ? "Review missing-value patterns"
          : Number(anomalyPercentage) > 0
          ? "Investigate detected anomalies"
          : "Proceed with analytical workflow"}
      </h3>

      <p>
        {Number(
          totalMissingValues
        ) > 0
          ? "Start by identifying affected columns, understanding why values are missing, and determining whether imputation or exclusion is appropriate."
          : Number(anomalyPercentage) > 0
          ? "Investigate the columns with the highest anomaly counts and verify whether the detected values represent legitimate variation or data-quality problems."
          : "The dataset currently shows no major quality blocker. Continue with the next analytical workflow."}
      </p>
    </div>
  </div>
</section>
{/* =========================================================
    PHASE 7.15.4 — HEALTH SCORE BREAKDOWN
========================================================= */}
<section className="health-breakdown-section">
  <div className="section-heading">
    <div>
      <span className="section-eyebrow">
        SCORE ANALYTICS
      </span>
      <h2>Health Score Breakdown</h2>
      <p>
        Component-level view of the factors contributing to
        the overall dataset health score.
      </p>
    </div>

    <div className="health-breakdown-total">
      <span>OVERALL SCORE</span>
      <strong>
        {getDatasetQualityScore().toFixed(2)}
        <small>/100</small>
      </strong>
    </div>
  </div>

  <div className="health-breakdown-grid">

    {/* Data Completeness */}
    <div className="health-breakdown-card">
      <div className="health-breakdown-header">
        <div>
          <span className="health-breakdown-label">
            DATA COMPLETENESS
          </span>
          <h3>
            {Math.max(
              0,
              100 -
                (
                  Number(
                    validation?.validation?.summary
                      ?.total_missing_values ?? 0
                  ) /
                  Math.max(Number(rowCount) * Number(columnCount), 1)
                ) *
                  100
            ).toFixed(2)}
            <small>/100</small>
          </h3>
        </div>

        <div className="health-breakdown-icon breakdown-blue">
          ✓
        </div>
      </div>

      <div className="health-breakdown-progress">
        <div
          className="health-breakdown-progress-fill"
          style={{
            width: `${Math.min(
              Math.max(
                100 -
                  (
                    Number(
                      validation?.validation?.summary
                        ?.total_missing_values ?? 0
                    ) /
                    Math.max(
                      Number(rowCount) * Number(columnCount),
                      1
                    )
                  ) *
                    100,
                0
              ),
              100
            )}%`,
          }}
        ></div>
      </div>

      <p>
        Based on the proportion of populated cells across the
        dataset.
      </p>
    </div>

    {/* Structural Integrity */}
    <div className="health-breakdown-card">
      <div className="health-breakdown-header">
        <div>
          <span className="health-breakdown-label">
            STRUCTURAL INTEGRITY
          </span>

          <h3>
            {Number(
              duplicateRows
            ) === 0
              ? "100"
              : Math.max(
                  0,
                  100 -
                    (
                      Number(
                        validation?.validation?.summary
                          ?.duplicate_rows ?? 0
                      ) /
                      Math.max(Number(rowCount), 1)
                    ) *
                      100
                ).toFixed(2)}
            <small>/100</small>
          </h3>
        </div>

        <div className="health-breakdown-icon breakdown-green">
          ✓
        </div>
      </div>

      <div className="health-breakdown-progress">
        <div
          className="health-breakdown-progress-fill breakdown-fill-green"
          style={{
            width: `${
              Number(
                duplicateRows
              ) === 0
                ? 100
                : Math.min(
                    Math.max(
                      100 -
                        (
                          Number(
                            validation?.validation?.summary
                              ?.duplicate_rows ?? 0
                          ) /
                          Math.max(Number(rowCount), 1)
                        ) *
                          100,
                      0
                    ),
                    100
                  )
            }%`,
          }}
        ></div>
      </div>

      <p>
        Measures structural cleanliness based on duplicate
        records.
      </p>
    </div>

    {/* Anomaly Stability */}
    <div className="health-breakdown-card">
      <div className="health-breakdown-header">
        <div>
          <span className="health-breakdown-label">
            ANOMALY STABILITY
          </span>

          <h3>
            {Math.max(
              0,
              100 - Number(anomalyPercentage)
            ).toFixed(2)}
            <small>/100</small>
          </h3>
        </div>

        <div className="health-breakdown-icon breakdown-orange">
          ~
        </div>
      </div>

      <div className="health-breakdown-progress">
        <div
          className="health-breakdown-progress-fill breakdown-fill-orange"
          style={{
            width: `${Math.min(
              Math.max(
                100 - Number(anomalyPercentage),
                0
              ),
              100
            )}%`,
          }}
        ></div>
      </div>

      <p>
        Reflects how much of the dataset remains outside the
        detected anomaly population.
      </p>
    </div>

    {/* Quality Readiness */}
    <div className="health-breakdown-card">
      <div className="health-breakdown-header">
        <div>
          <span className="health-breakdown-label">
            ANALYTICAL READINESS
          </span>

          <h3>
            {Math.min(
              Math.max(getDatasetQualityScore(), 0),
              100
            ).toFixed(2)}
            <small>/100</small>
          </h3>
        </div>

        <div className="health-breakdown-icon breakdown-purple">
          →
        </div>
      </div>

      <div className="health-breakdown-progress">
        <div
          className="health-breakdown-progress-fill breakdown-fill-purple"
          style={{
            width: `${Math.min(
              Math.max(getDatasetQualityScore(), 0),
              100
            )}%`,
          }}
        ></div>
      </div>

      <p>
        Indicates the current readiness of the dataset for
        downstream analytical workflows.
      </p>
    </div>

  </div>

  {/* Score Interpretation */}
  <div className="health-score-interpretation">
    <div className="health-score-interpretation-icon">
      ✦
    </div>

    <div>
      <span className="health-breakdown-label">
        SCORE INTERPRETATION
      </span>

      <h3>
        {getDatasetQualityScore() >= 90
          ? "Excellent dataset health"
          : getDatasetQualityScore() >= 75
          ? "Good dataset health"
          : getDatasetQualityScore() >= 60
          ? "Dataset needs attention"
          : "Poor dataset health"}
      </h3>

      <p>
        The overall health score combines the available data
        quality signals into a single high-level indicator.
        Individual component scores should still be reviewed
        before making important analytical decisions.
      </p>
    </div>
  </div>
</section>

 {/* =========================================================
    PHASE 7.17.4 — HISTORICAL HEALTH COMPARISON
========================================================= */}

<section className="health-trend-section">

  <div className="section-heading">

    <div>
      <span className="section-eyebrow">
        HISTORICAL INTELLIGENCE
      </span>

      <h2>Health Trend & Comparison</h2>

      <p>
        Compare the current dataset health with the
        previous recorded analysis snapshot.
      </p>
    </div>

    <div className="health-trend-badge">
      {hasHistoricalComparison
        ? "Comparison Available"
        : "Current Snapshot"}
    </div>

  </div>


  {hasHistoricalComparison ? (

    <>

      {/* ===============================================
          COMPARISON METRICS
      =============================================== */}

      <div className="health-trend-grid">

        {/* CURRENT HEALTH */}

        <div className="health-trend-card">

          <span className="health-trend-label">
            CURRENT HEALTH
          </span>

          <div className="health-trend-value">

            {getDatasetQualityScore().toFixed(2)}

            <small>/100</small>

          </div>

          <div
            className={`health-trend-change ${
              getComparisonTrendClass(
                healthTrend
              )
            }`}
          >

            <span>
              {getComparisonTrendIcon(
                healthTrend
              )}
            </span>

            {healthScoreChange >= 0 ? "+" : ""}
            {Number(
              healthScoreChange ?? 0
            ).toFixed(2)}{" "}
            points

          </div>

        </div>


        {/* PREVIOUS HEALTH */}

        <div className="health-trend-card">

          <span className="health-trend-label">
            PREVIOUS HEALTH
          </span>

          <div className="health-trend-value">

            {Number(
              previousHealthScore ?? 0
            ).toFixed(2)}

            <small>/100</small>

          </div>

          <p>
            Previous recorded dataset health score.
          </p>

        </div>


        {/* CURRENT ANOMALY */}

        <div className="health-trend-card">

          <span className="health-trend-label">
            CURRENT ANOMALY RATE
          </span>

          <div className="health-trend-value">

            {formatPercentage(
              anomalyPercentage
            )}

          </div>

          <div
            className={`health-trend-change ${
              getComparisonTrendClass(
                anomalyTrend
              )
            }`}
          >

            <span>
              {getComparisonTrendIcon(
                anomalyTrend
              )}
            </span>

            {anomalyRateChange >= 0 ? "+" : ""}
            {Number(
              anomalyRateChange ?? 0
            ).toFixed(2)}%

          </div>

        </div>


        {/* PREVIOUS ANOMALY */}

        <div className="health-trend-card">

          <span className="health-trend-label">
            PREVIOUS ANOMALY RATE
          </span>

          <div className="health-trend-value">

            {formatPercentage(
              previousAnomalyRate ?? 0
            )}

          </div>

          <p>
            Previous recorded anomaly exposure.
          </p>

        </div>

      </div>


      {/* ===============================================
          HEALTH TREND STATUS
      =============================================== */}

      <div
        className={`health-trend-summary ${
          getComparisonTrendClass(
            healthTrend
          ) === "trend-positive"
            ? "trend-summary-positive"
            : getComparisonTrendClass(
                healthTrend
              ) === "trend-negative"
            ? "trend-summary-negative"
            : "trend-summary-neutral"
        }`}
      >

        <div className="health-trend-summary-icon">

          {getComparisonTrendIcon(
            healthTrend
          )}

        </div>


        <div>

          <span className="health-trend-label">
            HEALTH TREND
          </span>

          <h3>

            {healthTrend === "Improved"
              ? "Dataset health is improving"
              : healthTrend === "Declined"
              ? "Dataset health has declined"
              : "Dataset health is stable"}

          </h3>


          <p>

            {healthTrend === "Improved"
              ? "The current health score is higher than the previous recorded snapshot, indicating an improvement in overall dataset quality."
              : healthTrend === "Declined"
              ? "The current health score is lower than the previous recorded snapshot. Recent data-quality changes should be reviewed."
              : "The current health score is unchanged compared with the previous recorded snapshot."}

          </p>

        </div>

      </div>


      {/* ===============================================
          ANOMALY TREND STATUS
      =============================================== */}

      <div
        className={`health-trend-summary ${
          getComparisonTrendClass(
            anomalyTrend
          ) === "trend-positive"
            ? "trend-summary-positive"
            : getComparisonTrendClass(
                anomalyTrend
              ) === "trend-negative"
            ? "trend-summary-negative"
            : "trend-summary-neutral"
        }`}
      >

        <div className="health-trend-summary-icon">

          {getComparisonTrendIcon(
            anomalyTrend
          )}

        </div>


        <div>

          <span className="health-trend-label">
            ANOMALY TREND
          </span>

          <h3>

            {anomalyTrend === "Improved"
              ? "Anomaly exposure is improving"
              : anomalyTrend === "Worsened"
              ? "Anomaly exposure has increased"
              : "Anomaly exposure is stable"}

          </h3>


          <p>

            {anomalyTrend === "Improved"
              ? "The anomaly rate is lower than the previous recorded snapshot, indicating reduced anomaly exposure."
              : anomalyTrend === "Worsened"
              ? "The anomaly rate is higher than the previous recorded snapshot. Investigate the affected data patterns."
              : "The anomaly rate is unchanged compared with the previous recorded snapshot."}

          </p>

        </div>

      </div>


      {/* ===============================================
          SNAPSHOT COMPARISON
      =============================================== */}

      <div className="health-trend-comparison-meta">

        <div>

          <span>
            PREVIOUS SNAPSHOT
          </span>

          <strong>
            {previousHistorySnapshot
              ? formatHistoryDate(
                  getHistoryDate(
                    previousHistorySnapshot
                  )
                )
              : "N/A"}
          </strong>

        </div>


        <div>

          <span>
            CURRENT SNAPSHOT
          </span>

          <strong>
            {currentHistorySnapshot
              ? formatHistoryDate(
                  getHistoryDate(
                    currentHistorySnapshot
                  )
                )
              : "Current analysis"}
          </strong>

        </div>


        <div>

          <span>
            SNAPSHOTS RECORDED
          </span>

          <strong>
            {historyRecords.length}
          </strong>

        </div>

      </div>

    </>

  ) : (

    /* ===============================================
       BASELINE STATE
    =============================================== */

    <div className="health-trend-empty">

      <div className="health-trend-empty-icon">
        —
      </div>

      <div>

        <h3>
          No historical comparison available yet
        </h3>

        <p>
          A previous analysis snapshot is required
          to calculate a health trend. The current
          health score will be used as the baseline
          for future comparisons.
        </p>

      </div>

    </div>

  )}

</section>

{/* =========================================================
    PHASE 7.16 — DATASET HEALTH TIMELINE
========================================================= */}
<section className="health-timeline-section">

  <div className="section-heading">
    <div>
      <span className="section-eyebrow">
        ANALYSIS HISTORY
      </span>

      <h2>Dataset Health Timeline</h2>

      <p>
        Historical view of dataset health and anomaly
        exposure across recorded analysis snapshots.
      </p>
    </div>

    <div className="health-timeline-count">
      {timelineRecords.length} Snapshots
    </div>
  </div>

  {/* =======================================================
      PHASE 7.16.10 — TIMELINE OVERALL STATISTICS
  ======================================================= */}

  {timelineRecords.length > 0 && (
    <div className="timeline-statistics-grid">

      <div className="timeline-stat-card">
        <span>SNAPSHOTS</span>

        <strong>
          {timelineRecords.length}
        </strong>

        <p>
          Total recorded analyses
        </p>
      </div>

      <div className="timeline-stat-card">
        <span>BEST HEALTH</span>

        <strong>
          {timelineBestHealth.toFixed(2)}
          <small>/100</small>
        </strong>

        <p>
          Highest recorded health score
        </p>
      </div>

      <div className="timeline-stat-card">
        <span>LOWEST HEALTH</span>

        <strong>
          {timelineLowestHealth.toFixed(2)}
          <small>/100</small>
        </strong>

        <p>
          Lowest recorded health score
        </p>
      </div>

      <div className="timeline-stat-card">
        <span>AVERAGE HEALTH</span>

        <strong>
          {timelineAverageHealth.toFixed(2)}
          <small>/100</small>
        </strong>

        <p>
          Average historical health score
        </p>
      </div>

    </div>
  )}


  {/* =======================================================
      TIMELINE RECORDS
  ======================================================= */}

  {timelineRecords.length > 0 ? (

    <div className="health-timeline">

      {intelligentTimelineRecords
        .slice()
        .reverse()
        .map((record, index) => (

          <div
            className="health-timeline-item"
            key={`${record.timelineIndex}-${index}`}
          >

            <div className="health-timeline-marker">
              <span></span>
            </div>

            <div className="health-timeline-content">

              <div className="health-timeline-header">

                <div>
                  <span className="health-timeline-step">
                    ANALYSIS #{record.timelineIndex}
                  </span>

                  <h3>
                    {formatHistoryDate(record.date)}
                  </h3>
                </div>

                <div className="health-timeline-status-group">

                  <span
                    className={`health-timeline-status ${record.status.className}`}
                  >
                    {record.status.label}
                  </span>

                  <span
                    className={`health-timeline-trend ${record.trend.className}`}
                  >
                    <span className="health-timeline-trend-icon">
                      {record.trend.icon}
                    </span>

                    {record.trend.label}
                  </span>

                </div>

              </div>


              {/* Timeline Metrics */}

              <div className="health-timeline-metrics">

                <div className="health-timeline-metric">
                  <span>
                    HEALTH SCORE
                  </span>

                  <strong>
                    {record.qualityScore.toFixed(2)}
                    <small>/100</small>
                  </strong>
                </div>


                <div className="health-timeline-metric">
                  <span>
                    ANOMALY RATE
                  </span>

                  <strong>
                    {formatPercentage(
                      record.anomalyRate
                    )}
                  </strong>
                </div>


                <div className="health-timeline-metric">
                  <span>
                    SNAPSHOT
                  </span>

                  <strong>
                    #{record.timelineIndex}
                  </strong>
                </div>

              </div>


              {/* Health Progress */}

              <div className="health-timeline-progress">

                <div className="health-timeline-progress-label">

                  <span>
                    Health Quality
                  </span>

                  <strong>
                    {record.qualityScore.toFixed(1)}%
                  </strong>

                </div>


                <div className="health-timeline-progress-track">

                  <div
                    className="health-timeline-progress-fill"
                    style={{
                      width: `${Math.min(
                        Math.max(
                          record.qualityScore,
                          0
                        ),
                        100
                      )}%`,
                    }}
                  ></div>

                </div>

              </div>

            </div>

          </div>

        ))}

    </div>

  ) : (

    <div className="health-timeline-empty">

      <div className="health-timeline-empty-icon">
        —
      </div>

      <div>

        <h3>
          No analysis history available
        </h3>

        <p>
          Dataset analysis snapshots will appear here
          after historical records are created.
        </p>

      </div>

    </div>

  )}


  {/* =======================================================
      PHASE 7.16.7 — SMART TREND ANALYSIS
  ======================================================= */}

  {intelligentTimelineRecords.length > 1 && (
    <div className="timeline-intelligence-summary">

      <div className="timeline-intelligence-icon">
        ✦
      </div>

      <div className="timeline-intelligence-content">

        <span className="health-timeline-label">
          SMART TREND ANALYSIS
        </span>

        <h3>
          {intelligentTimelineRecords[
            intelligentTimelineRecords.length - 1
          ].trend.label === "Improved"
            ? "Dataset health is improving"
            : intelligentTimelineRecords[
                intelligentTimelineRecords.length - 1
              ].trend.label === "Declined"
            ? "Dataset health requires attention"
            : intelligentTimelineRecords[
                intelligentTimelineRecords.length - 1
              ].trend.label === "Stable"
            ? "Dataset health is stable"
            : "Historical baseline established"}
        </h3>

        <p>
          The latest analysis is compared with the previous
          recorded snapshot to identify changes in overall
          health and anomaly exposure.
        </p>

      </div>

    </div>
  )}


</section>

{/* =========================================================
    PHASE 8.9 — AI DATASET INTELLIGENCE
========================================================= */}

{intelligence && (
  <section className="ai-intelligence-section">

    {/* Header */}
    <div className="section-heading">

      <div>
        <span className="section-eyebrow">
          AI INTELLIGENCE
        </span>

        <h2>
          Intelligent Dataset Analysis
        </h2>

        <p>
          Automated interpretation of dataset quality,
          anomaly exposure, risk level, and recommended
          business actions.
        </p>
      </div>

      <div
        className={`ai-risk-badge ${
          String(
            intelligence.overall_risk || ""
          ).toLowerCase() === "high"
            ? "ai-risk-high"
            : String(
                intelligence.overall_risk || ""
              ).toLowerCase() === "medium"
            ? "ai-risk-medium"
            : "ai-risk-low"
        }`}
      >
        {intelligence.overall_risk || "Unknown"} Risk
      </div>

    </div>


    {/* =====================================================
        AI OVERVIEW METRICS
    ===================================================== */}

    <div className="ai-intelligence-overview-grid">

      {/* Quality */}
      <div className="ai-intelligence-card">

        <div className="ai-intelligence-card-top">

          <span className="ai-intelligence-label">
            QUALITY SCORE
          </span>

          <div className="ai-intelligence-icon ai-icon-success">
            ✓
          </div>

        </div>

        <div className="ai-intelligence-value">
          {Number(
            intelligence.quality_score ?? 0
          ).toFixed(2)}

          <small>/100</small>
        </div>

        <span className="ai-intelligence-status">
          {intelligence.quality_status ||
            "Unknown"}
        </span>

      </div>


      {/* Anomaly Rate */}
      <div className="ai-intelligence-card">

        <div className="ai-intelligence-card-top">

          <span className="ai-intelligence-label">
            ANOMALY RATE
          </span>

          <div className="ai-intelligence-icon ai-icon-warning">
            !
          </div>

        </div>

        <div className="ai-intelligence-value">
          {formatPercentage(
            intelligence.anomaly_percentage
          )}
        </div>

        <span className="ai-intelligence-status">
          {formatNumber(
            intelligence.unique_anomalous_records
          )}{" "}
          anomalous records
        </span>

      </div>


      {/* Affected Columns */}
      <div className="ai-intelligence-card">

        <div className="ai-intelligence-card-top">

          <span className="ai-intelligence-label">
            AFFECTED COLUMNS
          </span>

          <div className="ai-intelligence-icon ai-icon-orange">
            ~
          </div>

        </div>

        <div className="ai-intelligence-value">
          {formatNumber(
            intelligence.columns_with_anomalies
          )}
        </div>

        <span className="ai-intelligence-status">
          Columns with detected anomalies
        </span>

      </div>


      {/* Outlier Occurrences */}
      <div className="ai-intelligence-card">

        <div className="ai-intelligence-card-top">

          <span className="ai-intelligence-label">
            OUTLIER OCCURRENCES
          </span>

          <div className="ai-intelligence-icon ai-icon-purple">
            #
          </div>

        </div>

        <div className="ai-intelligence-value">
          {formatNumber(
            intelligence.total_outlier_occurrences
          )}
        </div>

        <span className="ai-intelligence-status">
          Total detected outliers
        </span>

      </div>

    </div>


    {/* =====================================================
        MOST AFFECTED AREA + SEVERITY
    ===================================================== */}

    <div className="ai-intelligence-analysis-grid">

      {/* Most Affected Column */}
      <div className="ai-intelligence-panel">

        <div className="ai-intelligence-panel-header">

          <div>
            <span className="ai-intelligence-label">
              PRIORITY AREA
            </span>

            <h3>
              Most Affected Column
            </h3>
          </div>

          <div className="ai-panel-icon">
            !
          </div>

        </div>

        <div className="ai-priority-column">
          {intelligence.most_affected_column ||
            "No major anomaly identified"}
        </div>

        <p>
          This column has the highest detected anomaly
          concentration and should receive priority
          investigation.
        </p>

      </div>


      {/* Severity Distribution */}
      <div className="ai-intelligence-panel">

        <div className="ai-intelligence-panel-header">

          <div>
            <span className="ai-intelligence-label">
              ANOMALY SEVERITY
            </span>

            <h3>
              Severity Distribution
            </h3>
          </div>

          <div className="ai-panel-icon">
            ~
          </div>

        </div>

        <div className="ai-severity-grid">

          <div className="ai-severity-item ai-severity-high">
            <span>HIGH</span>

            <strong>
              {formatNumber(
                intelligence.severity_distribution
                  ?.high ?? 0
              )}
            </strong>

            <small>
              Immediate review
            </small>
          </div>

          <div className="ai-severity-item ai-severity-medium">
            <span>MEDIUM</span>

            <strong>
              {formatNumber(
                intelligence.severity_distribution
                  ?.medium ?? 0
              )}
            </strong>

            <small>
              Monitor
            </small>
          </div>

          <div className="ai-severity-item ai-severity-low">
            <span>LOW</span>

            <strong>
              {formatNumber(
                intelligence.severity_distribution
                  ?.low ?? 0
              )}
            </strong>

            <small>
              Observation
            </small>
          </div>

        </div>

      </div>

    </div>


    {/* =====================================================
        AI GENERATED INSIGHTS
    ===================================================== */}

    <div className="ai-insights-panel">

      <div className="ai-insights-header">

        <div>
          <span className="ai-intelligence-label">
            AUTOMATED FINDINGS
          </span>

          <h3>
            AI Insights
          </h3>

          <p>
            Key findings generated from the current
            dataset quality and anomaly analysis.
          </p>
        </div>

        <div className="ai-insights-count">
          {formatNumber(
            intelligence.insights?.length ?? 0
          )}{" "}
          Insights
        </div>

      </div>


      <div className="ai-insights-list">

        {(intelligence.insights || []).length > 0 ? (

          intelligence.insights.map(
            (item, index) => (

              <div
                className="ai-insight-item"
                key={`${item.type}-${index}`}
              >

                <div
                  className={`ai-insight-severity ${
                    getSeverityClass(
                      item.severity
                    )
                  }`}
                >
                  {String(
                    item.severity || "info"
                  ).toUpperCase()}
                </div>

                <div className="ai-insight-content">

                  <span>
                    {String(
                      item.type || "insight"
                    )
                      .replaceAll("_", " ")
                      .toUpperCase()}
                  </span>

                  <p>
                    {item.insight}
                  </p>

                </div>

              </div>

            )
          )

        ) : (

          <div className="ai-empty-state">
            No automated insights are currently
            available.
          </div>

        )}

      </div>

    </div>


    {/* =====================================================
        AI RECOMMENDATIONS
    ===================================================== */}

    <div className="ai-recommendations-panel">

      <div className="ai-recommendations-header">

        <div>
          <span className="ai-intelligence-label">
            DECISION SUPPORT
          </span>

          <h3>
            Recommended Actions
          </h3>

          <p>
            Suggested actions based on the automated
            dataset intelligence assessment.
          </p>
        </div>

        <div className="ai-recommendations-icon">
          →
        </div>

      </div>


      <div className="ai-recommendations-list">

        {(intelligence.recommendations || [])
          .length > 0 ? (

          intelligence.recommendations.map(
            (recommendation, index) => (

              <div
                className="ai-recommendation-item"
                key={index}
              >

                <div className="ai-recommendation-number">
                  {String(index + 1).padStart(
                    2,
                    "0"
                  )}
                </div>

                <div>
                  <p>
                    {recommendation}
                  </p>
                </div>

              </div>

            )
          )

        ) : (

          <div className="ai-empty-state">
            No recommendations are currently
            available.
          </div>

        )}

      </div>

    </div>


    {/* =====================================================
        AI FINAL ASSESSMENT
    ===================================================== */}

    <div className="ai-final-assessment">

      <div className="ai-final-icon">
        ✦
      </div>

      <div>

        <span className="ai-intelligence-label">
          AI FINAL ASSESSMENT
        </span>

        <h3>
          {intelligence.overall_risk === "High"
            ? "Immediate data-quality review recommended"
            : intelligence.overall_risk === "Medium"
            ? "Dataset is usable with targeted review"
            : "Dataset presents a low analytical risk"}
        </h3>

        <p>
          The automated assessment combines data quality,
          missing-value exposure, anomaly concentration,
          and severity distribution to identify the most
          important areas requiring attention.
        </p>

      </div>

    </div>

  </section>
)}




{/* =========================================
    AGENT EXECUTION ENGINE
========================================= */}

<section className="agent-execution-section">
  <div className="section-heading">
    <div>
      <span className="section-eyebrow">
        AUTONOMOUS DATA ANALYSIS
      </span>

      <h2>Agent Execution Engine</h2>

      <p>
        Describe your analysis goal and let the agent
        execute the appropriate analytical workflow.
      </p>
    </div>

    <div className="business-question-badge">
      AI AGENT
    </div>
  </div>

  {/* ANALYSIS QUESTION FORM */}

  <div className="agent-execution-form">
    <label htmlFor="execution-question">
      Analysis Question
    </label>

    <textarea
      id="execution-question"
      value={executionQuestion}
      onChange={(event) =>
        setExecutionQuestion(event.target.value)
      }
      placeholder="Example: Find unusual power usage"
      rows={3}
      disabled={executionLoading}
    />

    <div className="agent-execution-footer">
      <span>
        {datasetId
          ? `Dataset ID: ${datasetId}`
          : "Upload or restore a dataset first"}
      </span>

      <button
        type="button"
        className="business-question-button"
        onClick={handleExecuteAnalysis}
        disabled={
          executionLoading ||
          !datasetId ||
          !executionQuestion.trim()
        }
      >
        {executionLoading
          ? "Executing Analysis..."
          : "Run AI Analysis →"}
      </button>
    </div>
  </div>

  {/* EXECUTION ERROR */}

  {executionError && (
    <div
      className="agent-execution-error"
      role="alert"
    >
      <strong>Execution Failed</strong>
      <p>{executionError}</p>
    </div>
  )}

  {/* LOADING STATE */}

  {executionLoading && (
    <div
      className="agent-execution-loading"
      role="status"
    >
      <span className="agent-loading-indicator" />

      <div>
        <strong>Agent is working...</strong>
        <p>
          The backend is processing your analysis request.
        </p>
      </div>
    </div>
  )}

  {/* EXECUTION RESULTS */}

  {executionData && (
    <div className="agent-execution-results">

      {/* REPORT HEADER */}

      <div className="agent-execution-result-header">
        <div>
          <span className="section-eyebrow">
            EXECUTION REPORT
          </span>

          <h3>Analysis Results</h3>
        </div>

        <span
          className={`agent-execution-status ${
            executionData.execution?.execution_status ===
            "completed"
              ? "agent-status-completed"
              : "agent-status-other"
          }`}
        >
          {executionData.execution?.execution_status ||
            (executionData.success
              ? "Success"
              : "Unknown")}
        </span>
      </div>

      {/* SUMMARY METRICS */}

      <div className="agent-execution-metrics">
        <div className="agent-execution-metric">
          <span>Total Steps</span>

          <strong>
            {executionData.execution?.step_count ?? 0}
          </strong>
        </div>

        <div className="agent-execution-metric">
          <span>Completed</span>

          <strong>
            {executionData.execution?.completed_count ?? 0}
          </strong>
        </div>

        <div className="agent-execution-metric">
          <span>Failed</span>

          <strong>
            {executionData.execution?.failed_count ?? 0}
          </strong>
        </div>
      </div>

      {/* EXECUTION PLAN */}

      {executionData.plan != null && (
        <div className="agent-execution-block">

          <div className="agent-plan-header">
            <div>
              <h4>Execution Plan</h4>

              <p className="agent-plan-description">
                The workflow selected for your analysis.
              </p>
            </div>



<span className="agent-plan-mode">
  {executionData.execution?.execution_status === "completed" &&
  Number(executionData.execution?.completed_count ?? 0) > 0
    ? "Execution Complete"
    : Number(executionData.execution?.failed_count ?? 0) > 0
      ? "Execution Issues"
      : executionData.plan.execution_mode === "plan_only"
        ? "Plan Only"
        : "Workflow Ready"}
</span>


          </div>

          {Array.isArray(executionData.plan.steps) &&
          executionData.plan.steps.length > 0 ? (
            <div className="agent-plan-workflow">

              {executionData.plan.steps.map(
                (step, index) => {
                  const labels = {
                    profiling: "Dataset Profiling",
                    data_quality:
                      "Data Quality Assessment",
                    anomaly_detection:
                      "Anomaly Detection",
                    business_analysis:
                      "Business Analysis",
                    visualization:
                      "Data Visualization",
                  };

                  const descriptions = {
                    profiling:
                      "Explore dataset structure, columns, types, and statistics.",

                    data_quality:
                      "Evaluate missing values, duplicates, and data quality.",

                    anomaly_detection:
                      "Identify unusual records and potential outliers.",

                    business_analysis:
                      "Extract useful findings and business insights.",

                    visualization:
                      "Prepare visual representations of relevant findings.",
                  };

                  const stepName = String(
                    step.step || `step_${index + 1}`
                  );

                  const title =
                    labels[stepName] ||
                    stepName
                      .replaceAll("_", " ")
                      .replace(/\b\w/g, (char) =>
                        char.toUpperCase()
                      );

                  const executionSteps = Array.isArray(
                    executionData.execution?.steps
                  )
                    ? executionData.execution.steps
                    : [];

                  const matchingStep =
                    executionSteps.find(
                      (item) =>
                        String(
                          item.step ||
                          item.name ||
                          item.step_name ||
                          item.action ||
                          ""
                        ) === stepName
                    );

                  const rawStatus = String(
                    matchingStep?.status ||
                    matchingStep?.execution_status ||
                    "pending"
                  ).toLowerCase();

                  const allowedStatuses = [
                    "completed",
                    "failed",
                    "running",
                    "pending",
                  ];

                  const statusClass =
                    allowedStatuses.includes(rawStatus)
                      ? rawStatus
                      : "pending";

                  const statusLabels = {
                    completed: "Completed",
                    failed: "Failed",
                    running: "Running",
                    pending: "Pending",
                  };

                  return (
                    <div
                      className={`agent-plan-card agent-plan-card-${statusClass}`}
                      key={`${stepName}-${index}`}
                    >
                      <div className="agent-plan-number">
                        {statusClass === "completed"
                          ? "✓"
                          : statusClass === "failed"
                          ? "!"
                          : step.order ?? index + 1}
                      </div>

                      <div className="agent-plan-card-content">
                        <strong>{title}</strong>

                        <p>
                          {step.reason ||
                            descriptions[stepName] ||
                            "This step is included in the analysis workflow."}
                        </p>

                        {matchingStep?.error && (
                          <p className="agent-step-error">
                            {String(matchingStep.error)}
                          </p>
                        )}
                      </div>

                      <span
                        className={`agent-plan-status agent-plan-status-${statusClass}`}
                      >
                        {statusLabels[statusClass]}
                      </span>
                    </div>
                  );
                }
              )}

            </div>
          ) : (
            <p>No workflow steps are available.</p>
          )}

          <div className="agent-plan-footer">
            <span>
              Intent:{" "}
              <strong>
                {executionData.plan.intent ||
                  "General analysis"}
              </strong>
            </span>

            <span>
              Total steps:{" "}
              <strong>
                {executionData.plan.step_count ??
                  executionData.plan.steps?.length ??
                  0}
              </strong>
            </span>
          </div>
        </div>
      )}

      {/* ACTUAL EXECUTION STEPS */}

      <div className="agent-execution-block">
        <h4>Execution Steps</h4>

        {Array.isArray(
          executionData.execution?.steps
        ) &&
        executionData.execution.steps.length > 0 ? (
          <div className="agent-execution-step-list">

            {executionData.execution.steps.map(
              (step, index) => {
                const stepName =
                  step.step ||
                  step.name ||
                  step.step_name ||
                  step.action ||
                  `Step ${index + 1}`;

                const stepStatus = String(
                  step.status ||
                  step.execution_status ||
                  "unknown"
                ).toLowerCase();

                const isCompleted =
                  stepStatus === "completed";

                const isFailed =
                  stepStatus === "failed";

                return (
                  <div
                    className="agent-execution-step"
                    key={`${stepName}-${index}`}
                  >
                    <div className="agent-step-number">
                      {isCompleted
                        ? "✓"
                        : isFailed
                        ? "!"
                        : index + 1}
                    </div>

                    <div className="agent-step-content">
                      <strong>
                        {String(stepName).replaceAll(
                          "_",
                          " "
                        )}
                      </strong>

                      {step.reason && (
                        <p>{step.reason}</p>
                      )}

                      {step.description && (
                        <p>{step.description}</p>
                      )}

                      {step.error && (
                        <p className="agent-step-error">
                          {String(step.error)}
                        </p>
                      )}

                      {step.result != null && (
                        <details className="agent-step-details">
                          <summary>
                            View Step Result
                          </summary>

                          <div className="agent-step-result-viewer">
                            <AgentResultView
                              value={step.result}
                              stepName={String(stepName)}
                            />
                          </div>
                        </details>
                      )}
                    </div>

                    <span
                      className={`agent-step-status ${
                        isCompleted
                          ? "agent-status-completed"
                          : isFailed
                          ? "agent-status-failed"
                          : "agent-status-pending"
                      }`}
                    >
                      {stepStatus.replaceAll("_", " ")}
                    </span>
                  </div>
                );
              }
            )}

          </div>
        ) : (
          <p>No execution steps were returned.</p>
        )}
      </div>

      {/* FINAL RESULTS */}

      {executionData.execution?.results != null && (
        <div className="agent-execution-block">
          <h4>Results</h4>

          <div className="agent-final-results-list">
            {Object.entries(
              executionData.execution.results
            ).map(([resultName, result]) => (
              <div
                className="agent-final-result-item"
                key={resultName}
              >
                <h5>
                  {resultName
                    .replaceAll("_", " ")
                    .replace(/\b\w/g, (char) =>
                      char.toUpperCase()
                    )}
                </h5>

                <AgentResultView
                  value={result}
                  stepName={resultName}
                />
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )}
</section>

{/* =========================================================
    PHASE 8.10 — ASK YOUR DATA
========================================================= */}

<section className="business-question-section">

  <div className="business-question-header">

    <div>
      <span className="section-eyebrow">
        AI BUSINESS ANALYST
      </span>

      <h2>
        Ask Your Data
      </h2>

      <p>
        Ask a natural-language business question about
        the current dataset and get an intelligent analysis.
      </p>
    </div>

    <div className="business-question-badge">
      AI QUERY
    </div>

  </div>

  <div className="business-question-box">

    <textarea
      value={businessQuestion}
      onChange={(event) =>
        setBusinessQuestion(event.target.value)
      }
      placeholder="Ask a question about your dataset..."
      rows={4}
      disabled={businessQuestionLoading}
    />

    <div className="business-question-footer">

      <div className="business-question-hint">
        Example: Which city has the highest power consumption?
      </div>

      <button
        type="button"
        className="business-question-button"
        onClick={handleBusinessQuestion}
        disabled={
          businessQuestionLoading ||
          !businessQuestion.trim()
        }
      >
        {businessQuestionLoading
          ? "Analyzing..."
          : "Ask AI →"}
      </button>

    </div>

  </div>

  {businessAnswer && (
  <div className="business-question-result">
    <div className="business-question-result-header">
      <span className="ai-intelligence-label">
        AI RESPONSE
      </span>

      <span
        className={`business-answer-status ${
          businessAnswer.success
            ? "success"
            : "error"
        }`}
      >
        {businessAnswer.success ? "Analysis Complete" : "Analysis Failed"}
      </span>
    </div>

    <div className="business-question-result-question">
      <strong>Question:</strong>
      <span>{businessAnswer.question}</span>
    </div>

    {businessAnswer.success ? (
      <>
        <div className="business-question-answer">
          <span className="business-answer-label">
            ANSWER
          </span>

          <p>{businessAnswer.answer}</p>
        </div>

        {businessAnswer.analysis && (
          <div className="business-question-analysis">
            <div className="business-analysis-item">
              <span>Analysis Type</span>
              <strong>
                {businessAnswer.analysis.analysis_type || "—"}
              </strong>
            </div>

            <div className="business-analysis-item">
              <span>Group By</span>
              <strong>
                {businessAnswer.analysis.group_column || "—"}
              </strong>
            </div>

            <div className="business-analysis-item">
              <span>Result</span>
              <strong>
                {businessAnswer.analysis.result || "—"}
              </strong>
            </div>

            <div className="business-analysis-item">
              <span>Value</span>
              <strong>
                {typeof businessAnswer.analysis.value === "number"
                  ? businessAnswer.analysis.value.toLocaleString()
                  : "—"}
              </strong>
            </div>
          </div>
        )}
      </>
    ) : (
      <div className="business-question-result-message">
        {businessAnswer.answer ||
          businessAnswer.message ||
          "Unable to process the question."}
      </div>
    )}
  </div>
)}
</section>


{/* =========================
    ANOMALY MODAL
========================= */}

{selectedAnomaly && (
  <div
    className="anomaly-modal-overlay"
    onClick={closeAnomalyDetails}
  >

    <div
      className="anomaly-modal"
      onClick={(event) =>
        event.stopPropagation()
      }
    >

      <div className="anomaly-modal-header">

        <div>

          <span className="section-eyebrow">
            ANOMALY DRILL-DOWN
          </span>

          <h2>
            {selectedAnomaly.column}
          </h2>

        </div>

        <button
          type="button"
          className="anomaly-modal-close"
          onClick={closeAnomalyDetails}
          aria-label="Close"
        >
          ×
        </button>

      </div>


      <div className="anomaly-modal-body">

        <div className="anomaly-detail-grid">

          <div className="anomaly-detail-card">
            <span>Severity</span>

            <strong>
              <span
                className={`severity-badge ${getSeverityClass(
                  selectedAnomaly.severity
                )}`}
              >
                {selectedAnomaly.severity ||
                  "Unknown"}
              </span>
            </strong>
          </div>


          <div className="anomaly-detail-card">
            <span>Outlier Count</span>

            <strong>
              {formatNumber(
                selectedAnomaly.outlier_count
              )}
            </strong>
          </div>


          <div className="anomaly-detail-card">
            <span>Outlier Percentage</span>

            <strong>
              {formatPercentage(
                selectedAnomaly.outlier_percentage
              )}
            </strong>
          </div>


          <div className="anomaly-detail-card">
            <span>Likely Direction</span>

            <strong>
              {selectedDirection}
            </strong>
          </div>


          <div className="anomaly-detail-card">
            <span>High Outliers</span>

            <strong>
              {formatNumber(
                selectedAnomaly.high_outliers
              )}
            </strong>
          </div>


          <div className="anomaly-detail-card">
            <span>Low Outliers</span>

            <strong>
              {formatNumber(
                selectedAnomaly.low_outliers
              )}
            </strong>
          </div>

        </div>


        <div className="anomaly-detail-section">

          <h3>
            Normal IQR Range
          </h3>

          <div className="iqr-range">

            <div>
              <span>
                Lower Bound
              </span>

              <strong>
                {selectedAnomaly.lower !==
                undefined
                  ? Number(
                      selectedAnomaly.lower
                    ).toLocaleString()
                  : "N/A"}
              </strong>
            </div>


            <div>
              <span>
                Upper Bound
              </span>

              <strong>
                {selectedAnomaly.upper !==
                undefined
                  ? Number(
                      selectedAnomaly.upper
                    ).toLocaleString()
                  : "N/A"}
              </strong>
            </div>

          </div>

        </div>


        <div className="anomaly-detail-section">

          <h3>
            Explanation
          </h3>

          <p>
            {getAnomalyExplanation(
              selectedAnomaly
            )}
          </p>

        </div>


        <div className="anomaly-detail-section">

          <h3>
            What to Check
          </h3>

          <ul className="anomaly-check-list">

            <li>
              Verify whether the unusual values are
              legitimate business observations.
            </li>

            <li>
              Check for data-entry or measurement
              errors.
            </li>

            <li>
              Compare the affected values with the
              source records.
            </li>

            {String(
              selectedAnomaly.severity || ""
            ).toLowerCase() === "high" && (
              <li>
                Prioritize this column because its
                anomaly severity is high.
              </li>
            )}

          </ul>

        </div>

      </div>


      <div className="anomaly-modal-footer">

        <button
          type="button"
          className="reset-filter-button"
          onClick={closeAnomalyDetails}
        >
          Close
        </button>

      </div>

    </div>

  </div>

)}


      </div>
    )}
  </div>
</div>
);
}

export default App;
