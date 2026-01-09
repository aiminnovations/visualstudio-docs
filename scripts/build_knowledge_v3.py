import os
import lancedb
import voyageai
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

# CONFIGURATION
DEFAULT_INPUT_DIR = "E:\\My Drive\\sean@group9\\6_LAW - RESEARCH"
DEFAULT_OUTPUT_DIR = "./docs-ai"
EMBEDDING_MODEL = "voyage-law-2"
BATCH_SIZE = 30  # Reduced batch size to stay safer
RPM_DELAY = 2  # Seconds to wait between successful batches (throttling)


def load_and_chunk_md_files(directory):
    chunks = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

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


def embed_batch_safe(client, batch_texts, model, retry_count=0):
    """
    Tries to embed a batch. If it hits a rate limit, it waits and retries.
    """
    try:
        # input_type="document" is critical for Voyage RAG
        return client.embed(batch_texts, model=model, input_type="document").embeddings
    except Exception as e:
        error_msg = str(e).lower()
        if "rate limit" in error_msg or "429" in error_msg:
            wait_time = 30 + (retry_count * 10)  # Wait 30s, then 40s, etc.
            print(f"\n   ⚠️  Rate Limit Hit. Cooling down for {wait_time} seconds...")
            time.sleep(wait_time)
            # Recursive retry
            return embed_batch_safe(client, batch_texts, model, retry_count + 1)
        else:
            # If it's a real error (not just rate limit), raise it
            raise e


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_db_path = os.path.abspath(args.output)

    if not os.path.exists(input_path):
        print(f"Error: Directory {input_path} not found.")
        return
    if not os.path.exists(output_db_path):
        os.makedirs(output_db_path)

    print(f"1. Scanning files in {input_path}...")
    data = load_and_chunk_md_files(input_path)
    if not data:
        print("   No data found.")
        return
    print(f"   Found {len(data)} chunks.")

    print(f"2. Generating Embeddings (Smart Mode)...")
    try:
        vo_client = voyageai.Client()
    except Exception as e:
        print(f"Client Error: {e}")
        return

    texts = [d["text"] for d in data]
    all_vectors = []

    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        current_batch_num = (i // BATCH_SIZE) + 1

        print(
            f"   Processing Batch {current_batch_num}/{total_batches}...",
            end="",
            flush=True,
        )

        try:
            vectors = embed_batch_safe(vo_client, batch, EMBEDDING_MODEL)
            all_vectors.extend(vectors)
            print(" Done.")

            # Small artificial delay to respect TPM nicely
            time.sleep(RPM_DELAY)

        except Exception as e:
            print(f"\n   ❌ Critical Error on batch {current_batch_num}: {e}")
            return

    # Attach vectors to data
    table_data = []
    for i in range(len(all_vectors)):
        item = data[i]
        item["vector"] = all_vectors[i]
        table_data.append(item)

    print(f"3. Saving to LanceDB at {output_db_path}...")
    db = lancedb.connect(output_db_path)
    db.create_table("dev_docs", data=table_data, mode="overwrite")

    print("✅ Success! Database updated.")


if __name__ == "__main__":
    main()
