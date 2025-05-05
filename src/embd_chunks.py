# src/embd_chunks.py

import json
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict
import logging
from dotenv import load_dotenv
import os

# ✅ Import from centralized Azure logic
from logic.azure_calls import get_embedding, get_chat_completion

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
KB_PATH = BASE_DIR / "data" / "structured_kb.json"
EMBEDDINGS_PATH = BASE_DIR / "data" / "kb_embeddings.npz"
METADATA_PATH = BASE_DIR / "data" / "kb_metadata.json"
FAISS_INDEX_PATH = BASE_DIR / "data" / "kb_index.faiss"

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def build_faiss_index(vectors: List[List[float]]) -> faiss.IndexFlatL2:
    """Create FAISS index from vectors."""
    dim = len(vectors[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(vectors).astype("float32"))
    return index

def load_data():
    """Load FAISS index and metadata."""
    index = faiss.read_index(str(FAISS_INDEX_PATH))
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return index, metadata

def filter_by_hmo_tier(metadata: List[Dict], hmo: str, tier: str) -> List[int]:
    """Return indexes that match the user HMO and tier."""
    return [i for i, chunk in enumerate(metadata)
            if chunk.get("hmo") == hmo and chunk.get("tier") == tier]

def get_top_matches(index, query_vec, mask_indices, top_k=5) -> List[int]:
    """Get top K matches from the FAISS index."""
    if mask_indices:
        all_vecs = np.load(EMBEDDINGS_PATH)["vectors"]
        vectors_to_search = all_vecs[mask_indices]
        local_index = faiss.IndexFlatL2(all_vecs.shape[1])
        local_index.add(vectors_to_search.astype("float32"))
        D, I = local_index.search(np.array([query_vec]).astype("float32"), top_k)
        return [mask_indices[i] for i in I[0]]
    else:
        D, I = index.search(np.array([query_vec]).astype("float32"), top_k)
        return I[0]

def get_answer_from_metadata(question: str, context_chunks: List[str]) -> str:
    """Ask GPT-4o using retrieved context and user question."""
    prompt = (
        "Based on the user's HMO and insurance tier, answer the following question "
        "using the information provided below:\n\n"
        + "\n".join(f"- {chunk}" for chunk in context_chunks)
        + f"\n\nUser's question: {question}"
    )

    messages = [{"role": "user", "content": prompt}]
    return get_chat_completion(messages, temperature=0.3)

def build_and_save_index():
    """Main pipeline: read structured data, create embeddings, save index + metadata."""
    with open(KB_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    logging.info(f"Generating embeddings for {len(chunks)} chunks...")
    texts = [chunk["text"] for chunk in chunks]
    vectors = [get_embedding(text) for text in texts]

    # Save embeddings
    np.savez_compressed(EMBEDDINGS_PATH, vectors=np.array(vectors))

    # Save metadata
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # Build and save FAISS index
    index = build_faiss_index(vectors)
    faiss.write_index(index, str(FAISS_INDEX_PATH))

    logging.info("✅ Embeddings, metadata, and FAISS index saved.")

if __name__ == "__main__":
    build_and_save_index()
