# ── Cell 06: RAG Engine (ChromaDB) ──────────────────────────────────────────────
# Uses globals from prior cells: client, EMBEDDING_MODEL

import chromadb
import hashlib

rag_collection = None


def init_rag(persist_dir: str = "./data/chroma"):
    """Initialize ChromaDB persistent client and collection."""
    global rag_collection
    try:
        chroma_client = chromadb.PersistentClient(path=persist_dir)
        rag_collection = chroma_client.get_or_create_collection(
            name="kotlin_springboot_docs",
            metadata={"hnsw:space": "cosine"},
        )
        print(f"✅ RAG inicializado — colección: 'kotlin_springboot_docs', "
              f"documentos existentes: {rag_collection.count()}")
    except Exception as e:
        print(f"❌ Error inicializando RAG: {e}")
        raise


def chunk_document(
    text: str,
    source_name: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list:
    """Split *text* into overlapping character-based chunks.

    Returns list of {"text": str, "metadata": {"source": str, "chunk_index": int}}.
    """
    if not text or not text.strip():
        return []

    chunks: list = []
    start = 0
    index = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        # Skip empty trailing chunks
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "metadata": {"source": source_name, "chunk_index": index},
            })
            index += 1

        # Advance by (chunk_size - overlap), but at least 1 char to avoid infinite loop
        step = max(chunk_size - overlap, 1)
        start += step

    return chunks


def embed_and_store(chunks: list, collection):
    """Generate embeddings via OpenAI and store in ChromaDB (batches of 100)."""
    if not chunks:
        return

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]

        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
        except Exception as e:
            print(f"❌ Error generando embeddings (batch {i // batch_size}): {e}")
            continue

        ids = []
        documents = []
        metadatas = []
        for c in batch:
            uid = hashlib.md5(
                f"{c['metadata']['source']}_{c['metadata']['chunk_index']}".encode()
            ).hexdigest()
            ids.append(uid)
            documents.append(c["text"])
            metadatas.append(c["metadata"])

        try:
            collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as e:
            print(f"❌ Error almacenando en ChromaDB (batch {i // batch_size}): {e}")


def rag_search(query: str, n_results: int = 5) -> str:
    """Search the RAG collection. Returns a formatted numbered list with source attribution."""
    global rag_collection
    if rag_collection is None or rag_collection.count() == 0:
        return "No se encontraron resultados relevantes."

    try:
        # Embed the query
        query_response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[query],
        )
        query_embedding = query_response.data[0].embedding

        results = rag_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, rag_collection.count()),
        )

        if not results["documents"] or not results["documents"][0]:
            return "No se encontraron resultados relevantes."

        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        formatted_lines: list = []
        for idx, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), 1):
            # Cosine distance → similarity (ChromaDB returns distance, lower = better)
            relevance = max(0.0, 1.0 - dist)
            source = meta.get("source", "desconocido")
            snippet = doc[:200].replace("\n", " ")
            formatted_lines.append(
                f"{idx}. [Fuente: {source}] (relevancia: {relevance:.2f})\n   {snippet}..."
            )

        return "\n".join(formatted_lines)

    except Exception as e:
        return f"Error en búsqueda RAG: {e}"


def ingest_document(text: str, source_name: str, collection=None):
    """Convenience: chunk + embed + store. Uses global rag_collection if *collection* is None."""
    global rag_collection
    target = collection if collection is not None else rag_collection
    if target is None:
        print("❌ No hay colección RAG disponible. Ejecutá init_rag() primero.")
        return

    chunks = chunk_document(text, source_name)
    if not chunks:
        print(f"⚠️  Documento '{source_name}' vacío o sin contenido útil, se omitió.")
        return

    embed_and_store(chunks, target)
    print(f"📄 Documento '{source_name}' ingestado — {len(chunks)} chunks almacenados.")


# ── Initialization ──────────────────────────────────────────────────────────────
init_rag()
print(f"🔍 RAG Engine listo — colección contiene {rag_collection.count()} documentos.")
