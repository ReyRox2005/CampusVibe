# ingest.py - The corrected script to build the searchable index

import os
# NOTE: We use VectorStoreIndex from core as it's the base class
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.ingestion import IngestionPipeline
# Imports for the specific components we installed
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.storage.storage_context import StorageContext
import faiss
# We also need the SentenceSplitter to ensure documents are broken into proper chunks
from llama_index.core.node_parser import SentenceSplitter

# --- Configuration ---
# 1. Directory where your PDF/notes are located 
DATA_DIR = "./notes_data" 
# 2. Cost-free embedding model 
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# 3. Dimensionality of the vector space for the chosen model
VECTOR_DIMENSION = 384 

def create_or_update_index():
    # 1. Setup the Embedding Model (Runs locally, no cost)
    embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    print(f"Using Embedding Model: {EMBED_MODEL}")

    # 2. Load Documents
    if not os.path.exists(DATA_DIR):
        print(f"Data directory '{DATA_DIR}' not found. Please create it and add notes.")
        return

    # Load data, which often results in a list of Documents (one per file/page)
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    print(f"Loaded {len(documents)} documents from {DATA_DIR}")

    # 3. Setup FAISS (The local, cost-free Vector Store)
    # The size must match the dimension of the embedding model (384 for MiniLM)
    faiss_index = faiss.IndexFlatL2(VECTOR_DIMENSION)
    vector_store = FaissVectorStore(faiss_index=faiss_index)

    # 4. Create Storage Context
    # This object holds the reference to our vector store and is needed to build the index
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 5. Create the Ingestion Pipeline
    # Added SentenceSplitter to ensure chunking happens before embedding
    print("Building index... (This may take a moment)")
    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=1024, chunk_overlap=20), # Chunking step
            embed_model                                         # Embedding step
        ],
        vector_store=vector_store
    )
    
    # --- FIX APPLIED HERE ---
    # pipeline.run() returns a list of Nodes, NOT the index object.
    nodes = pipeline.run(documents=documents)
    print(f"Processed {len(nodes)} nodes (chunks).")
    
    # We must explicitly create the index object from the processed nodes and storage context
    index = VectorStoreIndex(
    nodes=nodes, 
    storage_context=storage_context,
    # === NEW: Pass the embed model explicitly to prevent OpenAI fallback ===
    embed_model=embed_model
    )
    # --- END FIX ---
    
    # 6. Save the Index to Disk
    # This saves all necessary metadata and the FAISS index to the ./storage folder
    index.storage_context.persist(persist_dir="./storage")
    print(f"Index successfully built and saved to ./storage!")


if __name__ == "__main__":
    create_or_update_index()