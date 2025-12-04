import os
import io
import sys
import logging
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
from botocore.client import Config
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("model_server")

MODEL_NAME = os.environ.get("MODEL_NAME", "openai/clip-vit-base-patch32")
DEVICE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
WASABI_ENDPOINT = os.environ.get("WASABI_ENDPOINT_URL", "https://s3.wasabisys.com")
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
EMB_S3_KEY = os.environ.get("EMB_S3_KEY", "models/reference_embeddings.pt")
EMB_LOCAL = os.environ.get("EMB_PATH", "reference_embeddings.pt")

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION,
    endpoint_url=WASABI_ENDPOINT,
    config=Config(signature_version="s3v4"),
)

app = FastAPI(title="Model Server")

_model = None
_processor = None
_reference_embeddings = None
_reference_keys = None

class MatchRequest(BaseModel):
    s3_keys: List[str]
    bucket: str = None

def download_s3_to_bytes(bucket: str, key: str) -> bytes:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()

def load_model():
    global _model, _processor
    if _model is None:
        use_safetensors = os.environ.get("USE_SAFETENSORS", "true").lower() in ("1","true","yes")
        log.info(f"Loading model {MODEL_NAME} on {DEVICE}")
        try:
            _model = CLIPModel.from_pretrained(MODEL_NAME, use_safetensors=use_safetensors)
        except:
            _model = CLIPModel.from_pretrained(MODEL_NAME)
        _model = _model.to(DEVICE)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    return _model, _processor

def ensure_reference_embeddings():
    global _reference_embeddings, _reference_keys
    if _reference_embeddings is not None:
        return _reference_embeddings, _reference_keys

    if os.path.exists(EMB_LOCAL):
        data = torch.load(EMB_LOCAL, map_location="cpu")
        _reference_embeddings = data["embeddings"]
        _reference_keys = data.get("keys", [])
        return _reference_embeddings, _reference_keys

    try:
        b = download_s3_to_bytes(S3_BUCKET, EMB_S3_KEY)
        with open(EMB_LOCAL, "wb") as f:
            f.write(b)
        data = torch.load(EMB_LOCAL, map_location="cpu")
        _reference_embeddings = data["embeddings"]
        _reference_keys = data.get("keys", [])
        return _reference_embeddings, _reference_keys
    except Exception as e:
        raise RuntimeError("Reference embeddings not found. Upload first.") from e

def image_bytes_to_pil(b: bytes):
    return Image.open(io.BytesIO(b)).convert("RGB")

@app.post("/match")
async def match(req: MatchRequest):
    bucket = req.bucket or S3_BUCKET
    if not bucket:
        raise HTTPException(400, "bucket missing")

    model, processor = load_model()
    ref_embs, ref_keys = ensure_reference_embeddings()

    images = []
    for key in req.s3_keys:
        b = download_s3_to_bytes(bucket, key)
        images.append(image_bytes_to_pil(b))

    inputs = processor(images=images, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        emb = model.get_image_features(**inputs)
    emb = emb / emb.norm(p=2, dim=-1, keepdim=True)
    emb = emb.mean(dim=0, keepdim=True)

    re = ref_embs
    re = re / re.norm(p=2, dim=-1, keepdim=True)
    sims = torch.matmul(emb, re.T).squeeze(0)

    idx = torch.argmax(sims).item()
    return {
        "best_match_key": ref_keys[idx] if ref_keys else None,
        "best_score": float(sims[idx]),
        "all_scores": sims.tolist()
    }

@app.get("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("model_server:app", host="0.0.0.0", port=5001)
