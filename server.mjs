import express from "express";
import multer from "multer";
import cors from "cors";
import AWS from "aws-sdk";
import fetch from "node-fetch";
import fs from "fs/promises";
import process from "process";

const app = express();
app.use(express.json());

const FRONTEND_URL = process.env.FRONTEND_URL || "*";
app.use(cors({ origin: FRONTEND_URL, methods: ["GET","POST"] }));

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } });

const s3 = new AWS.S3({
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  region: process.env.AWS_REGION || "us-east-1",
  endpoint: process.env.WASABI_ENDPOINT_URL || "https://s3.wasabisys.com",
  s3ForcePathStyle: true,
});

function s3KeyForUpload(filename) {
  const ts = Date.now();
  const safe = filename.replace(/\s+/g,"_");
  return `uploads/${ts}_${safe}`;
}

function presignedUrlForKey(key, expires=3600) {
  const params = { Bucket: process.env.S3_BUCKET_NAME, Key: key, Expires: expires };
  return s3.getSignedUrlPromise("getObject", params);
}

async function uploadBufferToS3(buffer, key, contentType) {
  const params = {
    Bucket: process.env.S3_BUCKET_NAME,
    Key: key,
    Body: buffer,
    ContentType: contentType,
    ACL: "private"
  };
  await s3.putObject(params).promise();
  return key;
}

app.post("/match", upload.array("images"), async (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ error: "No images provided" });
    }

    const s3Keys = [];
    for (const f of req.files) {
      const key = s3KeyForUpload(f.originalname);
      await uploadBufferToS3(f.buffer, key, f.mimetype);
      s3Keys.push(key);
    }

    const MODEL_SERVER_URL = process.env.MODEL_SERVER_URL || "http://127.0.0.1:5001";
    const resp = await fetch(`${MODEL_SERVER_URL}/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ s3_keys: s3Keys, bucket: process.env.S3_BUCKET_NAME }),
    });

    if (!resp.ok) {
      const t = await resp.text();
      console.error("Model server error:", t);
      return res.status(502).json({ error: "Model server error", detail: t });
    }
    const result = await resp.json();

    if (!result.best_match_key) {
      return res.json({ matched: false, result });
    }

    const presigned = await presignedUrlForKey(result.best_match_key, 3600);
    return res.json({ matched: true, model_url: presigned, raw: result });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: "internal_server_error", message: err.message });
  }
});

app.get("/health", (req, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
});
