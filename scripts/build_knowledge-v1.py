import os
import lancedb
import voyageai
import time

# CONFIGURATION
DOCS_DIR = "./docs-ai"
DB_PATH = "./my_knowledge_db"
# Voyage model optimized for code/technical docs
EMBEDDING_MODEL = "voyage-code-3"


def get_voyage_embeddings(texts, client):
    """
    Batches text and sends to Voyage AI for embedding.
    """
    # Voyage recommends input_type="document" for indexing
    # We do simple batching here to be safe (Voyage often allows large batches)
    batch_size = 100
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            result = client.embed(batch, model=EMBEDDING_MODEL, input_type="document")
            all_embeddings.extend(result.embeddings)
            # polite rate-limit sleep if you have thousands of docs
            time.sleep(0.2)
        except Exception as e:
            print(f"Error embedding batch: {e}")

    return all_embeddings


def load_and_chunk_md_files(directory):
    chunks = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Split by headers (Markdown Level 2)
                sections = content.split("\n## ")
                for i, section in enumerate(sections):
                    text = ("## " + section) if i > 0 else section
                    if text.strip():
                        chunks.append(
                            {"filename": file, "text": text.strip(), "path": file_path}
                        )
    return chunks


def main():
    print("1. Initializing Voyage AI client...")
    vo_client = voyageai.Client()  # Automatically picks up VOYAGE_API_KEY

    print(f"2. Scanning files in {DOCS_DIR}...")
    data = load_and_chunk_md_files(DOCS_DIR)
    texts = [item["text"] for item in data]
    print(f"   Found {len(data)} chunks.")

    if not data:
        print("   No data found.")
        return

    print(f"3. Generating embeddings using {EMBEDDING_MODEL}...")
    vectors = get_voyage_embeddings(texts, vo_client)

    # Attach vectors to data objects
    table_data = []
    for i, item in enumerate(data):
        item["vector"] = vectors[i]
        table_data.append(item)

    print(f"4. Saving to LanceDB at {DB_PATH}...")
    db = lancedb.connect(DB_PATH)

    # Create table (overwrite mode ensures clean state)
    # LanceDB automatically infers vector size from the first item
    db.create_table("dev_docs", data=table_data, mode="overwrite")

    print("Success! Knowledge base built with Voyage embeddings.")


if __name__ == "__main__":
    main()
