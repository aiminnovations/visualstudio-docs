"""
Script to build a knowledge base from PDF and Markdown files using VoyageAI for embeddings and LanceDB for storage.
"""

import os
import time
import argparse
import logging
import lancedb
import voyageai
from dotenv import load_dotenv
from pypdf import PdfReader  # <--- The new SDK

# Suppress annoying pypdf warnings
logging.getLogger("pypdf").setLevel(logging.ERROR)

load_dotenv()

# CONFIGURATION
DEFAULT_INPUT_DIR = "E:\\My Drive\\sean@group9\\5_LAW - REFERENCE\\LAW-RCW"
DEFAULT_OUTPUT_DIR = "G:\\Code\\llm-docs\\docs-ai"
EMBEDDING_MODEL = "voyage-law-2"
BATCH_SIZE = 8
RPM_DELAY = 1


def process_pdf(file_path, filename):
    """
    Reads a PDF and creates a chunk for every page.
    Best for legal docs so citations can reference 'Page X'.
    """
    chunks = []
    try:
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                # Add "Page X" to the text so the AI sees it
                page_label = f"Page {i+1}"
                chunks.append(
                    {
                        "filename": f"{filename} ({page_label})",  # e.g. "manual.pdf (Page 1)"
                        "text": f"## {filename} - {page_label}\n{text.strip()}",
                        "path": file_path,
                    }
                )
    except Exception as e:
        print(f"   ⚠️ Error reading PDF {filename}: {e}")
    return chunks


def process_markdown(file_path, filename):
    """
    Reads Markdown and splits by headers (##).
    """
    chunks = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        sections = content.split("\n## ")
        for i, section in enumerate(sections):
            text = ("## " + section) if i > 0 else section
            if text.strip():
                chunks.append(
                    {"filename": filename, "text": text.strip(), "path": file_path}
                )
    except Exception as e:
        print(f"   ⚠️ Error reading MD {filename}: {e}")
    return chunks


def load_and_chunk_files(directory):
    """
    Walks through the directory and processes supported files.
    """
    all_chunks = []
    print(f"   Scanning {directory}...")

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            print(f"   Processing: {file[:50]}...", end="\r", flush=True)

            # ROUTER: Decide how to handle the file based on extension
            if file.lower().endswith(".pdf"):
                pdf_chunks = process_pdf(file_path, file)
                all_chunks.extend(pdf_chunks)

            elif file.lower().endswith(".md"):
                md_chunks = process_markdown(file_path, file)
                all_chunks.extend(md_chunks)

    return all_chunks


def embed_batch_safe(client, batch_texts, model, retry_count=0, max_retries=5):
    """
    Embeds a batch of text with robust rate limit and error handling.
    """
    try:
        return client.embed(batch_texts, model=model, input_type="document").embeddings
    except Exception as e:
        error_msg = str(e).lower()
        # Handle Rate Limits and Transient Server Errors
        if any(
            x in error_msg
            for x in ["rate limit", "429", "500", "502", "503", "timeout"]
        ):
            if retry_count >= max_retries:
                print(
                    f"\n   ❌ Max retries ({max_retries}) exceeded. Giving up on this batch."
                )
                raise e

            wait_time = min(
                300, 30 * (2**retry_count)
            )  # Exponential backoff capped at 5 mins
            print(
                f"\n   ⚠️  API Issue ({e}). Retrying in {wait_time}s... (Attempt {retry_count + 1}/{max_retries + 1})"
            )
            time.sleep(wait_time)
            return embed_batch_safe(
                client, batch_texts, model, retry_count + 1, max_retries
            )
        else:
            # For other errors, log and re-raise (or could return Empty to skip)
            print(f"\n   ❌ Critical Error: {e}")
            raise e


def main():
    """
    Main execution function.
    """
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

    # 1. LOAD FILES
    print("1. Loading documents...")
    data = load_and_chunk_files(input_path)

    if not data:
        print("   No .md or .pdf files found.")
        return
    print(f"   Found {len(data)} total chunks (Pages/Sections).")

    # 2. CONNECT TO DB & CHECK PROGRESS
    print(f"2. Connecting to LanceDB at {output_db_path}...")
    db = lancedb.connect(output_db_path)
    table_name = "dev_docs"
    existing_filenames = set()

    if table_name in db.list_tables():
        print("   Found existing table. Loading processed files to resume...")
        tbl = db.open_table(table_name)
        # Efficiently just grab filenames
        try:
            # Use PyArrow to avoid Pandas dependency if possible, or fallback
            existing_filenames = set(
                tbl.search()
                .select(["filename"])
                .limit(None)
                .to_arrow()["filename"]
                .to_pylist()
            )
            print(f"   Skipping {len(existing_filenames)} already processed chunks.")
        except Exception as e:
            print(
                f"   Warning: Could not read existing data ({e}). Starting fresh check."
            )

    # 3. FILTER JOBS
    data_to_process = [d for d in data if d["filename"] not in existing_filenames]

    if not data_to_process:
        print("   ✅ All files already processed! Nothing to do.")
        return

    print(f"   Processing {len(data_to_process)} new chunks...")

    # 4. EMBED AND SAVE INCREMENTALLY
    print(f"4. Generating Embeddings ({EMBEDDING_MODEL})...")
    try:
        vo_client = voyageai.Client()
    except Exception as e:
        print(f"Client Error: {e}")
        return

    texts = [d["text"] for d in data_to_process]
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    # Process in batches
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i : i + BATCH_SIZE]
        batch_items = data_to_process[i : i + BATCH_SIZE]  # The original dicts

        current_batch_num = (i // BATCH_SIZE) + 1
        print(
            f"   Batch {current_batch_num}/{total_batches} ({len(batch_items)} items)...",
            end="",
            flush=True,
        )

        try:
            # Embed
            vectors = embed_batch_safe(vo_client, batch_texts, EMBEDDING_MODEL)

            # Attach vectors
            for item, vector in zip(batch_items, vectors):
                item["vector"] = vector

            # Save IMMEDIATELY
            if table_name in db.list_tables():
                tbl = db.open_table(table_name)
                tbl.add(batch_items)
            else:
                tbl = db.create_table(table_name, data=batch_items)

            print(" Saved.")
            time.sleep(RPM_DELAY)

        except Exception as e:
            print(f"\n   ❌ Error on batch {current_batch_num}: {e}")
            print("   ⚠️  Progress saved up to previous batch. Exiting safely.")
            return

    print("✅ Knowledge Base Update Complete.")


if __name__ == "__main__":
    main()
