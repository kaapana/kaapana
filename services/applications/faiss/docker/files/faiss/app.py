import argparse
from asyncio import Lock
from contextlib import asynccontextmanager
from pathlib import Path
import faiss
import numpy as np
from fastapi import FastAPI, UploadFile
import uvicorn
import os
from open_clip import create_model_from_pretrained, get_tokenizer
import logging
from PIL import Image
import io
import torch
from mappings_manager import MappingsManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


root_path = os.getenv("INGRESS_PATH", None)

base_path = Path("/kaapana/mounted/faiss/")
# base_path = Path("")
# Filepath for the FAISS index
FAISS_INDEX_PATH = base_path / "faiss_index.idx"
DIMENSION = 512
MODEL_NAME = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
DEVICE = "cpu"

# Initialize a lock for file operations
file_lock = Lock()

# Database setup and connection
MAPPINGS_FILE_PATH = base_path / "uid_mappings.json"
mappings_manager = None
index = None


def get_faiss_index():
    if Path(FAISS_INDEX_PATH).exists():
        logger.info("Loading existing FAISS index")
        index = faiss.read_index(str(FAISS_INDEX_PATH), faiss.IO_FLAG_ONDISK_SAME_DIR)
    else:
        logger.info("Creating a new FAISS index")
        base_index = faiss.IndexFlatL2(DIMENSION)
        index = faiss.IndexIDMap2(base_index)
    return index


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mappings_manager, index
    mappings_manager = MappingsManager(MAPPINGS_FILE_PATH)
    index = get_faiss_index()
    model_utility = ModelUtility.initialize_model()
    logger.info("Application started")
    yield
    await mappings_manager.shutdown()
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    logger.info("Application shutdown")


app = FastAPI(root_path=root_path, lifespan=lifespan)


# Model Utility
class ModelUtility:
    model = None
    tokenizer = None
    preprocessor = None

    @classmethod
    def initialize_model(cls):
        if cls.model is None or cls.tokenizer is None or cls.preprocessor is None:
            cls.model, cls.preprocessor = create_model_from_pretrained(MODEL_NAME)
            cls.tokenizer = get_tokenizer(MODEL_NAME)
            cls.model.to(DEVICE).eval()

    @classmethod
    def get_model(cls):
        # Assuming the model, tokenizer, and preprocessor are always initialized at startup,
        # we can now directly return them without additional checks.
        return cls.model, cls.tokenizer, cls.preprocessor


@app.put("/encode")
async def encode_image(
    seriesInstanceUID: str,
    sopInstanceUID: str,
    image: UploadFile,
):
    model, _, preprocessor = ModelUtility.get_model()

    image_bytes = await image.read()

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.error(f"Error converting image to RGB: {e}")
        raise e

    image = preprocessor(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        image_features = model.encode_image(image).cpu().numpy()

    # Normalize the feature vector
    image_features = image_features / np.linalg.norm(
        image_features, axis=1, keepdims=True
    )

    numeric_id = await mappings_manager.get_numeric_id(
        seriesInstanceUID, sopInstanceUID
    )

    # Add to FAISS index
    index.add_with_ids(
        image_features.astype(np.float32), np.array([numeric_id]).astype(np.int64)
    )

    return {"message": "Image encoded and stored successfully", "id": numeric_id}


@app.get("/search")
async def search(query: str, k: int = 5):
    # Tokenize and encode the query text
    model, tokenizer, _ = ModelUtility.get_model()
    text_tokens = tokenizer([query]).to(DEVICE)
    with torch.no_grad():
        text_features = model.encode_text(text_tokens).cpu().numpy()

    # Normalize the feature vector
    text_features = text_features / np.linalg.norm(text_features, axis=1, keepdims=True)

    # Search in FAISS
    D, I = index.search(text_features.astype(np.float32), k)

    # Use the mappings_manager to get UID pairs from numeric IDs
    uids = await mappings_manager.search(I[0].tolist())

    # Split UID pairs into seriesInstanceUID and sopInstanceUID
    uid_pairs = [uid.split("|") for uid in uids if uid is not None]

    return {"distances": D[0].tolist(), "uids": uid_pairs}


@app.get("/")
async def root():
    return {"message": "Hello from the image encoding and searching API"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Run app in debug mode. Changes in code will update the app automatically.",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=5000,
        help="Specify the port where the app should run (localhost:port), default is 5000",
    )
    parser.add_argument(
        "-host",
        "--host_name",
        type=str,
        default="0.0.0.0",
        help="Name of the host on which the app is run, by default it is '0.0.0.0'",
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host_name, port=args.port, reload=args.debug)
