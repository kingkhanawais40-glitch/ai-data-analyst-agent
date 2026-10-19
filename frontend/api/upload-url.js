
import { createHmac, randomUUID } from "node:crypto";
import { issueSignedToken, presignUrl } from "@vercel/blob";

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const URL_LIFETIME_MS = 10 * 60 * 1000;

const ALLOWED_ORIGINS = new Set([
  "https://ai-data-analyst-agent-sand.vercel.app",
  "http://localhost:5173",
]);

const FILE_TYPES = {
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".xls": "application/vnd.ms-excel",
  ".csv": "text/csv",
};

function createRegistrationToken(payload, secret) {
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = createHmac("sha256", secret)
    .update(encodedPayload)
    .digest("base64url");

  return `${encodedPayload}.${signature}`;
}

function setCorsHeaders(req, res) {
  const origin = req.headers.origin;

  if (!origin || !ALLOWED_ORIGINS.has(origin)) return false;

  res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Vary", "Origin");

  return true;
}

export default async function handler(req, res) {
  if (!setCorsHeaders(req, res)) {
    return res.status(403).json({ error: "Origin not allowed." });
  }

  if (req.method === "OPTIONS") return res.status(204).end();

  if (req.method !== "POST") {
    res.setHeader("Allow", "POST, OPTIONS");
    return res.status(405).json({ error: "Method not allowed." });
  }

  try {
    const secret = process.env.UPLOAD_REGISTRATION_SECRET;

    if (!secret || secret.length < 32) {
      console.error("Upload registration secret is missing or invalid.");
      return res.status(500).json({
        error: "Upload service is not configured correctly.",
      });
    }

    const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body;
    const originalName =
      typeof body?.fileName === "string" ? body.fileName : "";
    const fileName = originalName
      .split(/[\\/]/)
      .pop()
      .replace(/[^a-zA-Z0-9._-]/g, "_")
      .slice(-100);

    const extension = fileName.includes(".")
      ? fileName.slice(fileName.lastIndexOf(".")).toLowerCase()
      : "";

    const contentType = FILE_TYPES[extension];
    const fileSize = body?.fileSize;

    if (!fileName || !contentType) {
      return res.status(400).json({
        error: "Only XLSX, XLS, and CSV files are supported.",
      });
    }

    if (
      !Number.isSafeInteger(fileSize) ||
      fileSize < 1 ||
      fileSize > MAX_UPLOAD_BYTES
    ) {
      return res.status(400).json({
        error: "File size must be between 1 byte and 25 MB.",
      });
    }

    const pathname = `datasets/uploads/${randomUUID()}-${fileName}`;
    const validUntil = Date.now() + URL_LIFETIME_MS;

    const signedToken = await issueSignedToken({
      pathname,
      operations: ["put"],
      validUntil,
      allowedContentTypes: [contentType],
      maximumSizeInBytes: fileSize,
    });

    const { presignedUrl } = await presignUrl(signedToken, {
      operation: "put",
      pathname,
      access: "private",
      validUntil,
      allowedContentTypes: [contentType],
      maximumSizeInBytes: fileSize,
      allowOverwrite: false,
      addRandomSuffix: false,
    });

    const registrationToken = createRegistrationToken(
      {
        pathname,
        fileName: originalName.split(/[\\/]/).pop(),
        fileSize,
        contentType,
        expiresAt: validUntil,
      },
      secret
    );

    return res.status(200).json({
      presignedUrl,
      pathname,
      contentType,
      expiresAt: validUntil,
      maxSizeBytes: fileSize,
      registrationToken,
    });
  } catch (error) {
    console.error("Presigned upload URL generation failed:", error);
    return res.status(500).json({
      error: "Could not prepare the dataset upload.",
    });
  }
}
