import argparse
import faiss
import numpy as np
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

# Initialize a FAISS index
dimension = 64  # Example dimension size for the vector embeddings
index = faiss.IndexFlatL2(dimension)  # Using L2 distance for similarity search
# Adding a couple of vectors to the index for testing
vectors = np.random.random((2, dimension)).astype("float32")
index.add(vectors)


@app.get("/test")
async def test():
    # Perform a search for demonstration purposes
    query_vector = np.random.random((1, dimension)).astype("float32")
    k = 2  # Number of nearest neighbors to retrieve
    D, I = index.search(query_vector, k)  # D: Distances, I: Indices of the neighbors
    return JSONResponse(content={"distances": D.tolist(), "indices": I.tolist()})


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
        default="5000",
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
