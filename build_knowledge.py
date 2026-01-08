import os
import lancedb
import voyageai
import time
import argparse
from dotenv import load_dotenv

# Load keys from .env
load_dotenv()

# CONFIGURATION DEFAULTS
DEFAULT_INPUT_DIR = (
    "E:\\My Drive\\sean@group9\\6_LAW - RESEARCH"  # Default source if none provided
)
DEFAULT_OUTPUT_DIR = "./llm-docs/docs-ai"  # Default target for the DB
EMBEDDING_MODEL = "voyage-law-3"


def load_and_chunk_md_files(directory):
    chunks = []
    # Walk through the provided directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Split by headers
                    sections = content.split("\n## ")
                    for i, section in enumerate(sections):
                        text = ("## " + section) if i > 0 else section
                        if text.strip():
                            chunks.append(
                                {
                                    "filename": file,
                                    "text": text.strip(),
                                    "path": file_path,
                                }
                            )
                except Exception as e:
                    print(f"Skipping file {file}: {e}")
    return chunks


def main():
    # 1. Setup Command Line Arguments
    parser = argparse.ArgumentParser(
        description="Build Knowledge Base from Markdown files."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=DEFAULT_INPUT_DIR,
        help="Path to source folder containing .md files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Path where the LanceDB should be saved",
    )

    args = parser.parse_args()

    # Ensure absolute paths
    input_path = os.path.abspath(args.input)
    output_db_path = os.path.abspath(args.output)

    print(f"--- Configuration ---")
    print(f"Source: {input_path}")
    print(f"Target DB: {output_db_path}")
    print(f"---------------------")

    # 2. Check if source exists
    if not os.path.exists(input_path):
        print(f"Error: The input directory '{input_path}' does not exist.")
        return

    # 3. Create output directory if it doesn't exist
    if not os.path.exists(output_db_path):
        os.makedirs(output_db_path)
        print(f"Created output directory: {output_db_path}")

    print(f"1. Scanning files...")
    data = load_and_chunk_md_files(input_path)

    if not data:
        print("   No .md files found in source directory.")
        return

    print(f"   Found {len(data)} chunks.")

    print(f"2. Generating Embeddings ({EMBEDDING_MODEL})...")
    try:
        vo_client = voyageai.Client()  # Picks up env var automatically
    except Exception as e:
        print(f"Voyage Client Error: {e}")
        return

    texts = [d["text"] for d in data]
    batch_size = 50  # Conservative batch size
    all_vectors = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            # input_type="document" is critical for storage
            result = vo_client.embed(
                batch, model=EMBEDDING_MODEL, input_type="document"
            )
            all_vectors.extend(result.embeddings)
            # Simple progress indicator
            print(f"   Processed {min(i + batch_size, len(texts))}/{len(texts)}...")
            time.sleep(0.2)
        except Exception as e:
            print(f"   Error on batch {i}: {e}")

    # Attach vectors
    table_data = []
    # Ensure we only zip valid matching lengths
    limit = min(len(data), len(all_vectors))
    for i in range(limit):
        item = data[i]
        item["vector"] = all_vectors[i]
        table_data.append(item)

    print(f"3. Saving to LanceDB...")
    db = lancedb.connect(output_db_path)
    db.create_table("dev_docs", data=table_data, mode="overwrite")

    print("✅ Knowledge Base Built Successfully.")


if __name__ == "__main__":
    main()
