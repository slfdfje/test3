#!/usr/bin/env python3

import os
import argparse
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import boto3
from botocore.client import Config

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ref_dir", default="reference_images", help="local folder with reference images")
    p.add_argument("--model_name", default=os.environ.get("MODEL_NAME","openai/clip-vit-base-patch32"))
    p.add_argument("--out_path", default="reference_embeddings.pt")
    p.add_argument("--s3_key", default=os.environ.get("EMB_S3_KEY","models/reference_embeddings.pt"))
    p.add_argument("--bucket", default=os.environ.get("S3_BUCKET_NAME"))
    return p.parse_args()

def make_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION","us-east-1"),
        endpoint_url=os.environ.get("WASABI_ENDPOINT_URL","https://s3.wasabisys.com"),
        config=Config(signature_version="s3v4"),
    )

def main():
    args = parse_args()
    model = CLIPModel.from_pretrained(args.model_name)
    processor = CLIPProcessor.from_pretrained(args.model_name)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)

    embs = []
    keys = []
    for fname in sorted(os.listdir(args.ref_dir)):
        if fname.lower().endswith((".png",".jpg",".jpeg")):
            p = os.path.join(args.ref_dir, fname)
            img = Image.open(p).convert("RGB")
            inputs = processor(images=img, return_tensors="pt").to(device)
            with torch.no_grad():
                feat = model.get_image_features(**inputs)
            feat = feat / feat.norm(p=2, dim=-1, keepdim=True)
            embs.append(feat.cpu().squeeze(0))
            # map to model filename rule - change as needed
            keys.append(f"models/{os.path.splitext(fname)[0]}.glb")

    if len(embs) == 0:
        print("No reference images found in", args.ref_dir)
        return

    embs_tensor = torch.stack(embs)
    torch.save({"embeddings": embs_tensor, "keys": keys}, args.out_path)
    print("Saved embeddings to", args.out_path)

    # upload to S3
    if args.bucket:
        s3 = make_s3_client()
        with open(args.out_path, "rb") as fh:
            s3.put_object(Bucket=args.bucket, Key=args.s3_key, Body=fh.read())
        print("Uploaded embeddings to s3://{}/{}".format(args.bucket, args.s3_key))
    else:
        print("No bucket provided; skip upload")

if __name__ == "__main__":
    main()
