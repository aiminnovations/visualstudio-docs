import os
import lancedb
from sentence_transformers import SentenceTransformer
import pandas as pd

# CONFIGURATION
DOCS_DIR = "./docs-ai"  # Folder containing your .md files
DB_PATH = "./docs-ai/my_knowledge_db"  # Where LanceDB will save data
MODEL_NAME = "all-MiniLM-L6-v2"  # Small, fast, local embedding model


def load_and_chunk_md_files(directory):
    """
    Reads MD files and splits them by Level 2 headers (##).
    Adjust regex/splitting logic if your docs use different headers.
    """
    chunks = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Simple strategy: Split by "## " to get sections
                # This keeps the header context with the body text
                sections = content.split("\n## ")

                for i, section in enumerate(sections):
                    # Add back the "## " unless it's the very first preamble
                    text = ("## " + section) if i > 0 else section

                    # Clean up empty sections
                    if text.strip():
                        chunks.append(
                            {"filename": file, "text": text.strip(), "path": file_path}
                        )
    return chunks


def main():
    print("1. Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"2. Scanning files in {DOCS_DIR}...")
    data = load_and_chunk_md_files(DOCS_DIR)
    print(f"   Found {len(data)} chunks of documentation.")

    if not data:
        print("   No data found! Check your directory path.")
        return

    print("3. Generating embeddings (vectors)...")
    # Generate vectors for all text chunks
    vectors = model.encode([item["text"] for item in data])

    # Combine data with vectors into a list of dicts for LanceDB
    table_data = []
    for i, item in enumerate(data):
        item["vector"] = vectors[i]
        table_data.append(item)

    print(f"4. Saving to LanceDB at {DB_PATH}...")
    db = lancedb.connect(DB_PATH)

    # Overwrite the table if it exists to keep it fresh
    tbl = db.create_table("dev_docs", data=table_data, mode="overwrite")

    print("Success! Database built.")
    print("You can now query this DB for context.")


if __name__ == "__main__":
    main()
