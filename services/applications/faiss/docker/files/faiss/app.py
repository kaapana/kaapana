import argparse
import faiss
import numpy as np
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import os
from open_clip import create_model_from_pretrained, get_tokenizer

root_path = os.getenv("INGRESS_PATH", None)

app = FastAPI(root_path=root_path)

# Filepath for the FAISS index
index_file = "/kaapana/mounted/faiss/faiss_index.idx"

# Initialize or load a FAISS index
dimension = 512  # Example dimension size for the vector embeddings

if os.path.exists(index_file):
    index = faiss.read_index(index_file)  # Load the index if it exists
else:
    index = faiss.IndexFlatL2(dimension)  # Initialize a new index otherwise
    # Optionally, add vectors to the index at initialization
    vectors = np.random.random((2, dimension)).astype("float32")
    index.add(vectors)
    # Save the newly created index
    faiss.write_index(index, index_file)


@app.on_event("shutdown")
def save_index_on_shutdown():
    """Save the FAISS index to disk when the application shuts down."""
    faiss.write_index(index, index_file)


@app.get("/search")
async def search(prompt: str):
    device = "cpu"  # torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, image_processor = create_model_from_pretrained(
        "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224",
        # cache_dir=checkpoint_path / "BiomedCLIP",
    )
    tokenizer = get_tokenizer(
        "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
    )

    text = tokenizer(prompt).to(device)
    model.to(device).eval()

    query_vector = model.encode_text(text).detach().numpy()

    k = 2
    D, I = index.search(query_vector, k)
    return JSONResponse(content={"distances": D.tolist(), "indices": I.tolist()})


@app.get("/test")
async def test():
    # TODO: this endpoint is not working yet due to the path adjustments done during deployment -> not sure yet how to solve
    # Perform a search for demonstration purposes
    query_vector = np.random.random((1, dimension)).astype("float32")
    k = 2  # Number of nearest neighbors to retrieve
    D, I = index.search(query_vector, k)  # D: Distances, I: Indices of the neighbors
    return JSONResponse(content={"distances": D.tolist(), "indices": I.tolist()})


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
