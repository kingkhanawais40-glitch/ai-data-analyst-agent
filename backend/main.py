from pathlib import Path
import shutil
import io
import base64
import hashlib
import hmac
import json
import os
import time



import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from backend.database import get_connection, initialize_database
from backend.profiler import profile_dataframe
from backend.validator import validate_dataframe
from backend.analyzer import analyze_question
from backend.insights import generate_insights
from backend.anomaly_detector import detect_anomalies
from backend.intelligence import generate_dataset_intelligence
from backend.visualization_agent import analyze_and_visualize
from backend.business_questions import answer_business_question
from backend.analysis_planner import plan_analysis
from backend.agent_executor import execute_analysis_plan
from backend.pdf_report import generate_pdf_report
from backend.blob_storage import (
    delete_blob_object,
    download_blob_bytes,
    upload_blob_bytes,
)


# ============================================================
# APPLICATION SETUP
# ============================================================

app = FastAPI(
    title="AI Data Analyst & BI Automation Agent",
    description="AI-powered data analysis and BI automation backend.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ai-data-analyst-agent-sand.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def load_dataset_dataframe(dataset):
    """
    Load a dataset from private Vercel Blob or the legacy local
    uploads directory.
    """
    blob_pathname = None

    try:
        blob_pathname = dataset["blob_pathname"]
    except (KeyError, IndexError, TypeError):
        pass

    if blob_pathname:
        try:
            file_content = download_blob_bytes(blob_pathname)
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to retrieve dataset from Blob storage: {error}",
            ) from error

        source = io.BytesIO(file_content)
    else:
        source = UPLOAD_DIR / dataset["file_name"]

        if not source.is_file():
            raise HTTPException(
                status_code=404,
                detail="Dataset file not found.",
            )

    file_type = dataset["file_type"]

    if file_type == "csv":
        return pd.read_csv(source)

    if file_type in {"xlsx", "xls"}:
        return pd.read_excel(source)

    raise HTTPException(
        status_code=400,
        detail="Unsupported dataset file type.",
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_database()


# ============================================================
# REQUEST MODELS
# ============================================================

class AnalysisRequest(BaseModel):
    question: str


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "AI Data Analyst & BI Automation Agent API",
        "status": "running",
        "version": "1.0.0",
    }


# ============================================================
# HEALTH CHECK
# ============================================================


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


def verify_upload_registration_token(request: "BlobRegistrationRequest") -> bool:
    secret = os.getenv("UPLOAD_REGISTRATION_SECRET")

    if not secret or len(secret) < 32:
        return False

    try:
        encoded_payload, supplied_signature = request.registrationToken.split(".", 1)

        expected_signature = hmac.new(
            secret.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()

        supplied_signature_bytes = base64.urlsafe_b64decode(
            supplied_signature + "=" * (-len(supplied_signature) % 4)
        )

        if not hmac.compare_digest(expected_signature, supplied_signature_bytes):
            return False

        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        payload = json.loads(payload_bytes.decode("utf-8"))

        expires_at = payload.get("expiresAt")

        if not isinstance(expires_at, int) or isinstance(expires_at, bool):
            return False

        if expires_at <= int(time.time() * 1000):
            return False

        return (
            payload.get("pathname") == request.pathname
            and payload.get("fileName") == request.fileName
            and payload.get("fileSize") == request.fileSize
            and payload.get("contentType") == request.contentType
        )

    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return False


class BlobRegistrationRequest(BaseModel):
    pathname: str
    fileName: str
    fileSize: int
    contentType: str
    registrationToken: str




@app.post("/upload/register")
def register_blob_dataset(request: BlobRegistrationRequest):
    if not verify_upload_registration_token(request):
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired upload registration token.",
        )
    original_name = Path(request.fileName).name
    extension = Path(original_name).suffix.lower()

    allowed_extensions = {
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".xls": "xls",
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only CSV, XLSX, and XLS files are supported.",
        )

    if (
        not request.pathname.startswith("datasets/uploads/")
        or ".." in request.pathname
        or "\\" in request.pathname
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid uploaded file reference.",
        )

    if request.fileSize <= 0 or request.fileSize > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be between 1 byte and 25 MB.",
        )

    content_types = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
    }
    file_type = allowed_extensions[extension]

    if request.contentType != content_types[file_type]:
        raise HTTPException(
            status_code=400,
            detail="File type does not match the filename extension.",
        )

    connection = None

    try:
        file_content = download_blob_bytes(request.pathname)

        if not file_content or len(file_content) != request.fileSize:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file size could not be verified.",
            )

        source = io.BytesIO(file_content)
        if file_type == "csv":
            dataframe = pd.read_csv(source)
        else:
            dataframe = pd.read_excel(source)

        row_count = int(dataframe.shape[0])
        column_count = int(dataframe.shape[1])

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO datasets (
                name, file_name, file_type,
                row_count, column_count, blob_pathname
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                Path(original_name).stem,
                original_name,
                file_type,
                row_count,
                column_count,
                request.pathname,
            ),
        )

        dataset_id = cursor.lastrowid
        connection.commit()

        return {
            "message": "Dataset uploaded successfully.",
            "dataset_id": dataset_id,
            "file_name": original_name,
            "file_type": file_type,
            "rows": row_count,
            "columns": column_count,
            "column_names": dataframe.columns.tolist(),
        }

    except HTTPException:
        if connection is not None:
            connection.rollback()
        raise
    except Exception as error:
        if connection is not None:
            connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Dataset registration failed. Check the backend logs.",
        ) from error
    finally:
        if connection is not None:
            connection.close()


# ============================================================
# UPLOAD DATASET
# ============================================================


@app.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided.",
        )

    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower()

    allowed_extensions = {
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".xls": "xls",
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only CSV, XLSX, and XLS files are supported.",
        )

    file_type = allowed_extensions[extension]

    content_types = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
    }

    blob_pathname = None
    connection = None

    try:
        # Read uploaded file into memory.
        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        # Validate and inspect the file before uploading it.
        source = io.BytesIO(file_content)

        if file_type == "csv":
            dataframe = pd.read_csv(source)
        else:
            dataframe = pd.read_excel(source)

        row_count = int(dataframe.shape[0])
        column_count = int(dataframe.shape[1])

        # Store the actual dataset in private Vercel Blob.
        blob_pathname = upload_blob_bytes(
            pathname=f"datasets/{original_name}",
            content=file_content,
            content_type=content_types[file_type],
        )

        # Store metadata and the Blob pathname in the database.
        connection = get_connection()

        cursor = connection.cursor()
        dataset_name = Path(original_name).stem

        cursor.execute(
            """
            INSERT INTO datasets (
                name,
                file_name,
                file_type,
                row_count,
                column_count,
                blob_pathname
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_name,
                original_name,
                file_type,
                row_count,
                column_count,
                blob_pathname,
            ),
        )

        dataset_id = cursor.lastrowid
        connection.commit()

        return {
            "message": "Dataset uploaded successfully.",
            "dataset_id": dataset_id,
            "file_name": original_name,
            "file_type": file_type,
            "rows": row_count,
            "columns": column_count,
            "column_names": dataframe.columns.tolist(),
        }

    except HTTPException:
        if blob_pathname:
            try:
                delete_blob_object(blob_pathname)
            except Exception:
                pass
        raise

    except Exception as error:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass

        if blob_pathname:
            try:
                delete_blob_object(blob_pathname)
            except Exception:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"Dataset upload failed: {str(error)}",
        ) from error

    finally:
        if connection is not None:
            connection.close()

        await file.close()

# ============================================================
# GET DATASET PROFILE
# ============================================================

@app.get("/datasets/{dataset_id}/profile")
def get_dataset_profile(
    dataset_id: int,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        dataframe = load_dataset_dataframe(dataset)

        profile = profile_dataframe(dataframe)

        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "profile": profile,
        }

    finally:
        connection.close()



# ============================================================
# GET DATASET VALIDATION + SAVE HEALTH SNAPSHOT
# ============================================================

@app.get("/datasets/{dataset_id}/validate")
def validate_dataset(dataset_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # Get dataset metadata
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

               # ----------------------------------------------------
        # Load dataset from Blob or legacy local storage
        # ----------------------------------------------------

        dataframe = load_dataset_dataframe(dataset)
        # ----------------------------------------------------
        # Validate dataset
        # ----------------------------------------------------

        validation = validate_dataframe(dataframe)

        if not isinstance(validation, dict):
            raise ValueError(
                "Dataset validation returned an invalid result."
            )

        validation_summary = validation.get("summary", {})

        if not isinstance(validation_summary, dict):
            validation_summary = {}

        # ----------------------------------------------------
        # Extract data-quality metrics
        # ----------------------------------------------------

        quality_score = float(
            validation_summary.get("quality_score", 0)
        )

        total_missing_values = int(
            validation_summary.get("total_missing_values", 0)
        )

        duplicate_rows = int(
            validation_summary.get("duplicate_rows", 0)
        )

        # Preserve unknown counts as NULL, not a false zero.
        raw_flagged_columns = validation_summary.get(
            "flagged_columns"
        )

        flagged_columns = (
            int(raw_flagged_columns)
            if raw_flagged_columns is not None
            else None
        )

        # ----------------------------------------------------
        # Detect anomalies
        # ----------------------------------------------------

        anomaly_result = detect_anomalies(dataframe)

        if not isinstance(anomaly_result, dict):
            anomaly_result = {}

        anomaly_percentage = float(
            anomaly_result.get("anomaly_percentage", 0)
        )

        anomalous_records = int(
            anomaly_result.get("unique_anomalous_records", 0)
        )

        anomaly_columns = int(
            anomaly_result.get("columns_with_anomalies", 0)
        )

        total_outlier_occurrences = int(
            anomaly_result.get("total_outlier_occurrences", 0)
        )

        # ----------------------------------------------------
        # Save health snapshot
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO health_history (
                dataset_id,
                quality_score,
                anomaly_percentage,
                anomalous_records,
                anomaly_columns,
                total_outlier_occurrences,
                total_missing_values,
                duplicate_rows,
                flagged_columns
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                quality_score,
                anomaly_percentage,
                anomalous_records,
                anomaly_columns,
                total_outlier_occurrences,
                total_missing_values,
                duplicate_rows,
                flagged_columns,
            ),
        )

        connection.commit()

        # ----------------------------------------------------
        # Return validation result
        # ----------------------------------------------------

        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "validation": validation,
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(error)}",
        )

    finally:
        connection.close()

# ============================================================
# PLAN DATASET ANALYSIS
# ============================================================

@app.post("/datasets/{dataset_id}/plan")
def plan_dataset_analysis(
    dataset_id: int,
    request: AnalysisRequest,
):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name, file_name, row_count, column_count
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        # Create a plan only; do not execute the analysis.
        plan = plan_analysis(request.question)

        if not plan.get("success"):
            raise HTTPException(
                status_code=400,
                detail=plan.get(
                    "message",
                    "Unable to create analysis plan.",
                ),
            )

        return {
            "success": True,
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "question": request.question,
            "plan": plan,
            "execution_status": "not_started",
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis planning failed: {str(error)}",
        )

    finally:
        connection.close()



# ============================================================
# EXECUTE DATASET ANALYSIS PLAN
# ============================================================

@app.post("/datasets/{dataset_id}/execute")
def execute_dataset_analysis(
    dataset_id: int,
    request: AnalysisRequest,
):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

                # Load the dataset from Blob or legacy local storage.
        dataframe = load_dataset_dataframe(dataset)
        # Build the analysis plan.
        plan = plan_analysis(request.question)

        if not plan.get("success"):
            raise HTTPException(
                status_code=400,
                detail=plan.get(
                    "message",
                    "Unable to create analysis plan.",
                ),
            )

        # Execute the selected analysis steps.
        execution = execute_analysis_plan(
            dataframe=dataframe,
            question=request.question,
            plan=plan,
        )

        return {
            "success": execution["success"],
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "question": request.question,
            "plan": plan,
            "execution": execution,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis execution failed: {str(error)}",
        )

    finally:
        connection.close()



# ============================================================
# ANALYZE DATASET
# ============================================================

@app.post("/datasets/{dataset_id}/analyze")
def analyze_dataset(
    dataset_id: int,
    request: AnalysisRequest,
):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

                # Load the dataset from Blob or legacy local storage.
        dataframe = load_dataset_dataframe(dataset)

        # ----------------------------------------------------
        # Deterministic analysis
        # ----------------------------------------------------

        result = analyze_question(
            dataframe,
            request.question,
        )

        # ----------------------------------------------------
        # Generate business insights
        # ----------------------------------------------------

        analysis_data = result.get(
            "analysis",
            {},
        )

        insights = generate_insights(
            analysis_data,
        )

        # ----------------------------------------------------
        # Save analysis history
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO analysis_history (
                dataset_id,
                question,
                answer
            )
            VALUES (?, ?, ?)
            """,
            (
                dataset_id,
                request.question,
                str(result),
            ),
        )

        history_id = cursor.lastrowid

        # ----------------------------------------------------
        # Save insights
        # ----------------------------------------------------

        for insight in insights:
            cursor.execute(
                """
                INSERT INTO insights (
                    dataset_id,
                    insight,
                    severity
                )
                VALUES (?, ?, ?)
                """,
                (
                    dataset_id,
                    insight.get("insight", ""),
                    insight.get("severity", "info"),
                ),
            )

        connection.commit()

        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "history_id": history_id,
            "question": request.question,
            "analysis": result,
            "insights": insights,
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(error)}",
        )

    finally:
        connection.close()


# ============================================================
# GET DATASET HEALTH HISTORY + HISTORICAL COMPARISON
# ============================================================

@app.get("/datasets/{dataset_id}/history")
def get_analysis_history(
    dataset_id: int,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # Check dataset
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        # ----------------------------------------------------
        # Get health history
        #
        # Oldest snapshot -> newest snapshot
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                dataset_id,
                quality_score,
                quality_score AS data_quality_score,
                anomaly_percentage,
                anomalous_records,
                anomaly_columns,
                total_outlier_occurrences,
                total_missing_values,
                duplicate_rows,
                flagged_columns,
                created_at
            FROM health_history
            WHERE dataset_id = ?
            ORDER BY id ASC
            """,
            (dataset_id,),
        )

        history = [
            dict(row)
            for row in cursor.fetchall()
        ]

        # ----------------------------------------------------
        # Historical comparison
        # ----------------------------------------------------
        #
        # With one snapshot:
        #   current_snapshot = snapshot #1
        #   previous_snapshot = None
        #   comparison unavailable
        #
        # With two or more snapshots:
        #   current_snapshot = latest
        #   previous_snapshot = second latest
        #   calculate health/anomaly changes
        # ----------------------------------------------------

        current_snapshot = None
        previous_snapshot = None

        health_change = None
        anomaly_change = None

        health_trend = "Baseline"
        anomaly_trend = "Baseline"

        has_comparison = False

        if len(history) >= 1:
            current_snapshot = history[-1]

        if len(history) >= 2:
            previous_snapshot = history[-2]

            current_health = float(
                current_snapshot.get(
                    "quality_score",
                    0,
                )
            )

            previous_health = float(
                previous_snapshot.get(
                    "quality_score",
                    0,
                )
            )

            current_anomaly = float(
                current_snapshot.get(
                    "anomaly_percentage",
                    0,
                )
            )

            previous_anomaly = float(
                previous_snapshot.get(
                    "anomaly_percentage",
                    0,
                )
            )

            # ------------------------------------------------
            # Calculate changes
            # ------------------------------------------------

            health_change = round(
                current_health - previous_health,
                2,
            )

            anomaly_change = round(
                current_anomaly - previous_anomaly,
                2,
            )

            # ------------------------------------------------
            # Health trend
            #
            # Higher quality score = better
            # ------------------------------------------------

            if health_change > 0:
                health_trend = "Improved"

            elif health_change < 0:
                health_trend = "Declined"

            else:
                health_trend = "Stable"

            # ------------------------------------------------
            # Anomaly trend
            #
            # Lower anomaly percentage = better
            # ------------------------------------------------

            if anomaly_change < 0:
                anomaly_trend = "Improved"

            elif anomaly_change > 0:
                anomaly_trend = "Worsened"

            else:
                anomaly_trend = "Stable"

            has_comparison = True

        # ----------------------------------------------------
        # Return complete historical intelligence
        # ----------------------------------------------------

        return {
            "dataset_id": dataset_id,

            "history": history,

            "snapshot_count": len(history),

            "has_comparison": has_comparison,

            "current_snapshot": current_snapshot,

            "previous_snapshot": previous_snapshot,

            "health_change": health_change,

            "anomaly_change": anomaly_change,

            "health_trend": health_trend,

            "anomaly_trend": anomaly_trend,
        }

    finally:
        connection.close()


# ============================================================
# GET DATASET INSIGHTS
# ============================================================

@app.get("/datasets/{dataset_id}/insights")
def get_dataset_insights(
    dataset_id: int,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # Check dataset
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        # ----------------------------------------------------
        # Get insights
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                dataset_id,
                insight,
                severity,
                created_at
            FROM insights
            WHERE dataset_id = ?
            ORDER BY id DESC
            """,
            (dataset_id,),
        )

        insights = [
            dict(row)
            for row in cursor.fetchall()
        ]

        return {
            "dataset_id": dataset_id,
            "insights": insights,
        }

    finally:
        connection.close()


# ============================================================
# GET DATASET ANOMALIES
# ============================================================

@app.get("/datasets/{dataset_id}/anomalies")
def get_dataset_anomalies(
    dataset_id: int,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

                # Load the dataset from Blob or legacy local storage.
        dataframe = load_dataset_dataframe(dataset)

        anomalies = detect_anomalies(
            dataframe,
        )

        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "anomalies": anomalies,
        }

    finally:
        connection.close()

        # ============================================================
# GET DATASET INTELLIGENCE
# ============================================================

@app.get("/datasets/{dataset_id}/intelligence")
def get_dataset_intelligence(
    dataset_id: int,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # Get dataset
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

                # Load the dataset from Blob or legacy local storage.
        dataframe = load_dataset_dataframe(dataset)

        # ----------------------------------------------------
        # Validate dataset
        # ----------------------------------------------------

        validation = validate_dataframe(
            dataframe,
        )

        # ----------------------------------------------------
        # Detect anomalies
        # ----------------------------------------------------

        anomaly_result = detect_anomalies(
            dataframe,
        )

        # ----------------------------------------------------
        # Generate automatic intelligence
        # ----------------------------------------------------

        intelligence = generate_dataset_intelligence(
            validation,
            anomaly_result,
        )

        # ----------------------------------------------------
        # Return intelligence
        # ----------------------------------------------------

        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "intelligence": intelligence,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Intelligence generation failed: {str(error)}",
        )

    finally:
        connection.close()


# ============================================================
# DOWNLOAD DATASET PDF REPORT
# ============================================================

@app.get("/datasets/{dataset_id}/report/pdf")
def download_dataset_pdf_report(dataset_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # ----------------------------------------------------
        # Get dataset metadata
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset_row = cursor.fetchone()

        if dataset_row is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        dataset_info = {
            "id": dataset_row["id"],
            "name": dataset_row["name"],
            "file_name": dataset_row["file_name"],
            "rows": dataset_row["row_count"],
            "columns": dataset_row["column_count"],
        }

        # ----------------------------------------------------
        # Load dataset file
        # ----------------------------------------------------

                # ----------------------------------------------------
        # Load dataset from Blob or legacy local storage
        # ----------------------------------------------------

        dataframe = load_dataset_dataframe(dataset_row)

        # ----------------------------------------------------
        # Generate validation metrics
        # ----------------------------------------------------

        validation_result = validate_dataframe(dataframe)

        # ----------------------------------------------------
        # Detect anomalies
        # ----------------------------------------------------

        anomaly_data = detect_anomalies(dataframe)

        if not isinstance(anomaly_data, dict):
            anomaly_data = {}

        # ----------------------------------------------------
        # Generate dataset intelligence
        # ----------------------------------------------------

        intelligence_data = generate_dataset_intelligence(
            validation_result,
            anomaly_data,
        )

        # ----------------------------------------------------
        # Get existing historical snapshots
        # Do not create a new snapshot during PDF download.
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                dataset_id,
                quality_score,
                anomaly_percentage,
                anomalous_records,
                anomaly_columns,
                total_outlier_occurrences,
                total_missing_values,
                duplicate_rows,
                flagged_columns,
                created_at
            FROM health_history
            WHERE dataset_id = ?
            ORDER BY id ASC
            """,
            (dataset_id,),
        )

        history = [
            dict(row)
            for row in cursor.fetchall()
        ]

        historical_data = {
            "dataset_id": dataset_id,
            "history": history,
            "snapshot_count": len(history),
            "has_comparison": len(history) >= 2,
            "current_snapshot": history[-1] if history else None,
            "previous_snapshot": history[-2] if len(history) >= 2 else None,
            "health_change": None,
            "anomaly_change": None,
            "health_trend": "Baseline",
            "anomaly_trend": "Baseline",
        }

        if len(history) >= 2:
            current = history[-1]
            previous = history[-2]

            health_change = round(
                float(current["quality_score"] or 0)
                - float(previous["quality_score"] or 0),
                2,
            )

            anomaly_change = round(
                float(current["anomaly_percentage"] or 0)
                - float(previous["anomaly_percentage"] or 0),
                2,
            )

            historical_data.update(
                {
                    "health_change": health_change,
                    "anomaly_change": anomaly_change,
                    "health_trend": (
                        "Improved" if health_change > 0
                        else "Declined" if health_change < 0
                        else "Stable"
                    ),
                    "anomaly_trend": (
                        "Improved" if anomaly_change < 0
                        else "Worsened" if anomaly_change > 0
                        else "Stable"
                    ),
                }
            )

        # ----------------------------------------------------
        # Get saved insights
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT insight, severity, created_at
            FROM insights
            WHERE dataset_id = ?
            ORDER BY id DESC
            """,
            (dataset_id,),
        )

        saved_insights = [
            dict(row)
            for row in cursor.fetchall()
        ]

        # ----------------------------------------------------
        # Generate PDF
        # ----------------------------------------------------

        pdf_bytes = generate_pdf_report(
            dataset=dataset_info,
            validation={
                "dataset": dataset_info,
                "validation": validation_result,
            },
            anomalies={
                "dataset": dataset_info,
                "anomalies": anomaly_data,
            },
            intelligence={
                "dataset": dataset_info,
                "intelligence": intelligence_data,
            },
            historical=historical_data,
            insights=saved_insights,
        )

        safe_filename = f"dataset_{dataset_id}_report.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{safe_filename}"'
                ),
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "no-store",
            },
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"PDF report generation failed: {str(error)}",
        )

    finally:
        connection.close()


@app.post("/datasets/{dataset_id}/business-question")
def ask_business_question(
    dataset_id: int,
    payload: dict,
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

        question = str(payload.get("question", "")).strip()

        if not question:
            raise HTTPException(
                status_code=400,
                detail="Question is required.",
            )

                # ----------------------------------------------------
        # Load dataset from Blob or legacy local storage
        # ----------------------------------------------------

        dataframe = load_dataset_dataframe(dataset)

        result = answer_business_question(
            dataframe,
            question,
        )

        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "question": result,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Business question analysis failed: {str(error)}",
        )

    finally:
        connection.close()

# ============================================================
# VISUALIZATION PIPELINE
# ============================================================

@app.post("/datasets/{dataset_id}/visualize")
def visualize_dataset(
    dataset_id: int,
    request: AnalysisRequest,
):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM datasets
            WHERE id = ?
            """,
            (dataset_id,),
        )

        dataset = cursor.fetchone()

        if dataset is None:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found.",
            )

               # ----------------------------------------------------
        # Load dataset from Blob or legacy local storage
        # ----------------------------------------------------

        dataframe = load_dataset_dataframe(dataset)
        # ----------------------------------------------------
        # Complete visualization pipeline
        # ----------------------------------------------------

        result = analyze_and_visualize(
            dataframe,
            request.question,
        )

        if not result.get("success"):
            return {
                "dataset": {
                    "id": dataset["id"],
                    "name": dataset["name"],
                    "file_name": dataset["file_name"],
                    "rows": dataset["row_count"],
                    "columns": dataset["column_count"],
                },
                "question": request.question,
                "visualization": result,
            }

        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "file_name": dataset["file_name"],
                "rows": dataset["row_count"],
                "columns": dataset["column_count"],
            },
            "question": request.question,
            "visualization": result,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Visualization failed: {str(error)}",
        )

    finally:
        connection.close()
