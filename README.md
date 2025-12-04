# AI Glasses Try-On — Full Project README

This repository contains a full-stack AI glasses try-on application with:
- Frontend: React + Vite (deployed on Vercel)
- Backend: Node.js Express (deployed on Railway)
- Model server: FastAPI (PyTorch + Transformers CLIP) for image matching (deployed on Railway or side-by-side)
- Storage: Wasabi S3 for 3D models (.glb) and reference images

This README explains how to run locally (docker-compose), compute reference embeddings, upload them to Wasabi, and deploy to Railway & Vercel.

---
## Table of contents
- [Prerequisites](#prerequisites)
- [Local development (docker-compose)](#local-development-docker-compose)
- [Compute and upload reference embeddings](#compute-and-upload-reference_embeddingspt-)
- [Deploy model server & backend to Railway](#deploy-model-server--backend-to-railway)
- [Deploy frontend to Vercel](#deploy-frontend-to-vercel)
- [Environment variables](#environment-variables)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---
## Prerequisites
- Docker & Docker Compose (for local development)
- Python 3.11 (if running model server locally)
- Node 20+ and npm (for frontend/backend local dev)
- Railway account (https://railway.app)
- Vercel account (https://vercel.com)
- Wasabi account and S3 bucket (https://wasabi.com)

---
## Local development (docker-compose)
1. Copy `.env.example` to `.env` and fill your Wasabi credentials and bucket name.
2. Start services:
```bash
docker-compose up --build
```
This brings up:
- Backend at `http://localhost:8080`
- Model server at `http://localhost:5001`

You can test health endpoints:
- `GET http://localhost:8080/health`
- `GET http://localhost:5001/health`

---
## Compute and upload `reference_embeddings.pt` (script)
A helper script `build_and_upload_embeddings.py` will:
1. Load CLIP model
2. Iterate local `reference_images/` folder (one image per reference)
3. Compute normalized image embeddings
4. Save `reference_embeddings.pt` containing `embeddings` and `keys`
5. Upload the file to Wasabi S3 at the configured key (EMB_S3_KEY)

Run it locally (after filling `.env`):
```bash
python build_and_upload_embeddings.py --ref_dir ./reference_images --s3_key models/reference_embeddings.pt
```

---
## Deploy model server & backend to Railway
We recommend two Railway services: **model-server** and **backend**.

1. Create two services in Railway and connect to your GitHub repo.
2. Set environment variables in Railway > Variables (see `Environment variables` section).
3. For model-server, set the start command (or use Dockerfile) to:
```
python model_server.py
```
4. For backend, set the start command:
```
node backend/server.mjs
```
5. Note the model-server Railway URL (e.g. `https://model-server.up.railway.app`) and set `MODEL_SERVER_URL` in backend Railway variables to that value.
6. Ensure both services have access to Wasabi credentials via Railway variables.

---
## Deploy frontend to Vercel
1. Push frontend to GitHub and import project on Vercel.
2. Set environment variable in Vercel:
```
VITE_API_URL=https://your-backend.up.railway.app
```
3. Build command: `npm run build` and Output Directory: `dist`
4. Deploy; Vercel will host the static site and call Railway backend for matching.

---
## Environment variables
Set these in Railway and Vercel appropriately (never commit secrets):

```
# Core
PORT=8080
NODE_ENV=production

# Wasabi S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
WASABI_ENDPOINT_URL=https://s3.wasabisys.com
S3_BUCKET_NAME=your-bucket

# Model server
MODEL_NAME=openai/clip-vit-base-patch32
DEVICE=cpu
EMB_S3_KEY=models/reference_embeddings.pt
EMB_PATH=reference_embeddings.pt

# Backend
MODEL_SERVER_URL=https://model-server.up.railway.app
FRONTEND_URL=https://your-vercel-site.vercel.app
```

---
## Troubleshooting
- `Model server OOM`: reduce batch size, use CPU, or use smaller model. Consider GPU instance for heavy loads.
- `S3 403`: check Wasabi keys and bucket policy; ensure Railway variables are correct.
- `CORS`: allow Vercel domain in backend CORS config.

---
## License
MIT
