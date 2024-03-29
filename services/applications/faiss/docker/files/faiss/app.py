import argparse
from pathlib import Path
import faiss
import numpy as np
from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
import os
import sqlite3
from open_clip import create_model_from_pretrained, get_tokenizer
import logging


logging.basicConfig(level=logging.DEBUG)


root_path = os.getenv("INGRESS_PATH", None)

app = FastAPI(root_path=root_path)

# TODO This has to be changed again
base_path = Path("/kaapana/mounted/faiss/")
base_path = Path("")
# Filepath for the FAISS index
index_file_path = base_path / "faiss_index.idx"
dimension = 512

# Database setup and connection
db_path = str(base_path / "uid_mapping.db")
try:
    conn = sqlite3.connect(db_path)
    logging.info("Successfully connected to the database.")
except sqlite3.OperationalError as e:
    logging.error(f"Error connecting to database at {db_path}: {e}")
index = None


def setup_database():
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS uid_mapping (
            numeric_id INTEGER PRIMARY KEY,
            combined_uid TEXT UNIQUE NOT NULL
        );
    """
    )
    conn.commit()


def setup_faiss_index(dimension, index_file_path):
    """
    Set up and return a FAISS index. If an index file already exists at index_file_path,
    it's loaded from disk. Otherwise, a new index is created.

    Args:
    - dimension (int): The dimensionality of the vectors to be indexed.
    - index_file_path (str): Path to the FAISS index file.

    Returns:
    - faiss.Index: A FAISS index object, ready to be used for adding and searching vectors.
    """
    if os.path.exists(index_file_path):
        # Load the index from file if it exists
        print("Loading existing index from file.")
        index = faiss.read_index(index_file_path)
    else:
        # Create a new index
        print("Creating a new index.")
        base_index = faiss.IndexFlatL2(dimension)  # Using L2 distance for similarity
        # Wrap the base index in an IndexIDMap
        index = faiss.IndexIDMap2(base_index)
        # Note: Depending on your specific needs, you might choose a different base index type
        # for more efficient search at the cost of some accuracy (e.g., IndexIVFFlat).

    return index


def get_or_create_numeric_id(seriesInstanceUID, sopInstanceUID):
    combined_uid = f"{seriesInstanceUID}_{sopInstanceUID}"
    cursor = conn.cursor()
    try:
        # Attempt to insert the new UID (this fails if it already exists)
        cursor.execute(
            "INSERT INTO uid_mapping (combined_uid) VALUES (?)", (combined_uid,)
        )
        numeric_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        # UID already exists, retrieve its numeric ID
        cursor.execute(
            "SELECT numeric_id FROM uid_mapping WHERE combined_uid = ?", (combined_uid,)
        )
        numeric_id = cursor.fetchone()[0]
    return numeric_id


def retrieve_uids(numeric_ids):
    placeholders = ", ".join("?" for _ in numeric_ids)
    query = f"SELECT combined_uid FROM uid_mapping WHERE numeric_id IN ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(query, numeric_ids)
    return [row[0] for row in cursor.fetchall()]


@app.on_event("startup")
def startup_event():
    setup_database()
    global index
    index = setup_faiss_index(dimension, index_file_path)


@app.on_event("shutdown")
async def shutdown_event():
    global conn, index, index_file_path
    print("Application is shutting down. Cleaning up resources...")

    # Save the FAISS index to disk if necessary
    if index is not None:
        print(f"Saving FAISS index to {index_file_path}")
        faiss.write_index(index, index_file_path)

    # Close the SQLite database connection
    if conn:
        conn.close()
        print("Closed the database connection.")


@app.put("/encode")
async def encode_image(seriesInstanceUID: str, sopInstanceUID: str, image: UploadFile):
    from PIL import Image
    import io

    device = "cpu"
    model, image_processor = create_model_from_pretrained(
        "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
    )
    model.to(device).eval()
    image_bytes = await image.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    image_tensor = image_processor(image).unsqueeze(0).to(device)
    print(image_tensor.shape)
    query_vector = model.encode_image(image_tensor).detach().numpy()
    # Normalize the vector
    query_vector /= np.linalg.norm(query_vector)
    numeric_id = get_or_create_numeric_id(seriesInstanceUID, sopInstanceUID)
    # Add to FAISS (Assuming 'index' is your FAISS index variable)
    index.add_with_ids(query_vector, np.array([numeric_id]).astype(np.int64))
    return JSONResponse(content={"message": "Image encoded and stored successfully."})


@app.get("/search")
async def search(prompt: str, k: int = 2):
    device = "cpu"  # torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _ = create_model_from_pretrained(
        "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224",
        # cache_dir=checkpoint_path / "BiomedCLIP",
    )
    tokenizer = get_tokenizer(
        "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
    )

    text = tokenizer(prompt).to(device)
    model.to(device).eval()
    query_vector = model.encode_text(text.input_ids).detach().numpy()
    # Normalize the query vector
    query_vector /= np.linalg.norm(query_vector)
    D, I = index.search(query_vector, k)  # Perform the search
    original_uids = retrieve_uids(I[0].tolist())
    return JSONResponse(content={"distances": D[0].tolist(), "uids": original_uids})


@app.get("/")
async def default():
    return "Hello, World!"


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
