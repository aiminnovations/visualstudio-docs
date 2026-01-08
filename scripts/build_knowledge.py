import os
import lancedb
import voyageai
import time

# CONFIGURATION
DOCS_DIR = "./docs-ai"
DB_PATH = "./docs-ai/my_knowledge_db"
EMBEDDING_MODEL = "voyage-law-3"  # Best for legal documents


def load_and_chunk_md_files(directory):
    """
    Simple chunker. For 'voyage-context-3', you would need to pass
    nested lists (docs -> chunks), but for 'voyage-law-3', flat chunks work great.
    """
    chunks = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Split by headers
                sections = content.split("\n## ")
                for i, section in enumerate(sections):
                    text = ("## " + section) if i > 0 else section
                    if text.strip():
                        chunks.append(
                            {"filename": file, "text": text.strip(), "path": file_path}
                        )
    return chunks


def main():
    print(f"1. Scanning {DOCS_DIR}...")
    data = load_and_chunk_md_files(DOCS_DIR)

    if not data:
        print("   No data found.")
        return

    print(f"   Found {len(data)} chunks.")

    print(f"2. Generating Embeddings ({EMBEDDING_MODEL})...")
    vo_client = voyageai.Client()

    # Embed in batches to be safe
    texts = [d["text"] for d in data]
    batch_size = 100
    all_vectors = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # input_type="document" is CRITICAL for Voyage accuracy
        result = vo_client.embed(batch, model=EMBEDDING_MODEL, input_type="document")
        all_vectors.extend(result.embeddings)
        time.sleep(0.2)

    # Attach vectors
    table_data = []
    for i, item in enumerate(data):
        item["vector"] = all_vectors[i]
        table_data.append(item)

    print(f"3. Saving to LanceDB...")
    db = lancedb.connect(DB_PATH)
    db.create_table("dev_docs", data=table_data, mode="overwrite")
    print("✅ Knowledge Base Built.")


if __name__ == "__main__":
    main()
