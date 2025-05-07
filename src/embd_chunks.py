# src/embd_chunks.py

import json
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import logging
from dotenv import load_dotenv
import os
from logic.azure_calls import get_embedding, get_chat_completion

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
KB_PATH = BASE_DIR / "data" / "structured_kb.json"
EMBEDDINGS_PATH = BASE_DIR / "data" / "kb_embeddings.npz"
METADATA_PATH = BASE_DIR / "data" / "kb_metadata.json"
FAISS_INDEX_PATH = BASE_DIR / "data" / "kb_index.faiss"

def is_kb_ready() -> bool:
    """Check if the knowledge base files already exist."""
    return all(path.exists() for path in [KB_PATH, METADATA_PATH, FAISS_INDEX_PATH, EMBEDDINGS_PATH])


def normalize_hmo_tier(hmo: str, tier: str) -> Tuple[str, str]:
    """Normalize HMO and tier names to a standard format."""

    HMO_MAP: dict[str, str] = {
        "maccabi": "מכבי", "מכבי": "מכבי",
        "meuhedet": "מאוחדת", "מאוחדת": "מאוחדת",
        "clalit": "כללית", "כללית": "כללית"
    }

    TIER_MAP: dict[str, str] = {
        "gold": "זהב", "זהב": "זהב",
        "silver": "כסף", "כסף": "כסף",
        "bronze": "ארד", "ארד": "ארד"
    }

    hmo_normalized = HMO_MAP.get(hmo.lower())
    tier_normalized = TIER_MAP.get(tier.lower())

    if not hmo_normalized or not tier_normalized:
        raise ValueError(f"❌ Invalid HMO or tier: '{hmo}' or '{tier}'")

    return hmo_normalized, tier_normalized


def build_faiss_index(vectors: List[List[float]]) -> faiss.IndexFlatL2:
    """Create FAISS index from vectors  """
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


# def filter_by_hmo_tier(metadata: List[Dict], hmo: str, tier: str) -> List[int]:
#     """Filter metadata by HMO and tier."""
#     return [i for i, chunk in enumerate(metadata)
#             if chunk.get("hmo") == hmo and chunk.get("tier") == tier]

def filter_by_hmo_tier(metadata: List[Dict], hmo: str, tier: str) -> List[int]:
    """ Filter metadata by HMO and tier."""
    filtered_indices = []
    for i, chunk in enumerate(metadata):
        hmo_val = chunk.get("hmo")
        tier_val = chunk.get("tier")
        if (hmo_val is None or hmo_val == hmo) and (tier_val is None or tier_val == tier):
            filtered_indices.append(i)
    
    return filtered_indices
def get_top_matches(index, query_vec, mask_indices, top_k=5) -> List[int]:
    """
    Given a user query embedding, retrieves top-k nearest text chunks (using Euclidean distance). 
    Returns :
    - I: the indices of the closest vectors in the FAISS index
    - D: the corresponding distances 
    """

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

def get_answer_from_metadata(question: str, context_chunks: List[str], hmo: str, tier: str, language: str) -> str:
    """Ask GPT using retrieved context chunks and user question."""
    prompt = (
        "Based on the user's HMO and insurance tier, answer the following question "
        "using the information provided below.\n\n"
        f"Your answer must be in the language: {language}\n\n" 
        f"User's HMO: {hmo}\n"
        f"User's insurance tier: {tier}\n\n"
        f"User's question: {question}\n\n"
        f"Data for answer:\n"
        f"{' '.join(f'- {chunk}' for chunk in context_chunks)}\n\n"
    )

    messages = [{"role": "user", "content": prompt}]
    return get_chat_completion(messages, temperature=0.3)

def build_and_save_index():
    """
    Main pipeline: load "structured_kb.json", read structured data, create embeddings.
    Save embeddings to kb_embeddings.npz, FAISS index to kb_index.faiss, metadata to kb_meta_data.json.
    """
    # load all chunks from the knowledge base- structured_kb.json
    with open(KB_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    logging.info(f"Generating embeddings for {len(chunks)} chunks...")

    # list of texts to embed
    texts = [chunk["text"] for chunk in chunks]\
    # Get embeddings for each text chunk
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
