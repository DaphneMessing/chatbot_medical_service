# build_and_query_kb.py- just a script to run the process of parsing html files, generating embeddings, and querying the knowledge base.

import logging
import json
import numpy as np
from src.extract_data_embd import run_extraction
from src.embd_chunks import (
    build_and_save_index,
    load_data,
    get_embedding,
    filter_by_hmo_tier,
    get_top_matches,
    get_answer_from_metadata
)

def ask_question(question: str, hmo: str, tier: str, top_k: int = 5):
    print(f"\n🔍 Question: {question}")
    print(f"📄 HMO: {hmo} | Tier: {tier}")

    # Load FAISS index and metadata
    index, metadata = load_data()

    # Embed the question
    query_vector = get_embedding(question)

    # Filter metadata by HMO and tier
    mask = filter_by_hmo_tier(metadata, hmo=hmo, tier=tier)

    # Retrieve top matching chunks
    top_indices = get_top_matches(index, query_vector, mask, top_k=top_k)
    context_chunks = [metadata[i]["text"] for i in top_indices]

    # Get GPT-generated answer
    answer = get_answer_from_metadata(question, context_chunks)
    print(f"\n💬 Answer:\n{answer}\n")

def build_kb_and_query():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("\n🔧 Step 1: Extracting structured text from HTML files...")
    run_extraction()

    print("\n⚙️  Step 2: Generating embeddings and building FAISS index...")
    build_and_save_index()

    print("\n✅ Knowledge base is ready!")

    # Phase 2: Ask a sample question
    sample_question = "מה ההטבות על דיקור סיני במסלול זהב במכבי?"
    sample_hmo = "מכבי"
    sample_tier = "זהב"

    ask_question(sample_question, sample_hmo, sample_tier)

if __name__ == "__main__":
    build_kb_and_query()
