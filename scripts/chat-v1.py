import lancedb
import voyageai
import anthropic
import sys

# CONFIGURATION
DB_PATH = "./docs-ai/my_knowledge_db"
EMBEDDING_MODEL = "voyage-law-3"
CLAUDE_MODEL = "claude-sonnet-4-5"  # Best for coding tasks


def search_docs(query, tbl, vo_client):
    """
    Embeds query via Voyage and searches LanceDB.
    """
    # 1. Embed question (input_type="query" is crucial for retrieval quality)
    query_vector = vo_client.embed(
        [query], model=EMBEDDING_MODEL, input_type="query"
    ).embeddings[0]

    # 2. Search DB (Retrieve top 5 chunks for better context)
    results = tbl.search(query_vector).limit(5).to_pandas()
    return results


def ask_claude(query, context_df, ant_client):
    """
    Sends context + query to Anthropic Claude.
    """
    # Construct context block
    context_text = ""
    for _, row in context_df.iterrows():
        context_text += f"---\nFILE: {row['filename']}\nCONTENT:\n{row['text']}\n"

    system_prompt = (
        "You are an expert software architect acting as a 'Context Engine'. "
        "You have access to the user's local documentation below. "
        "Answer the question using ONLY the provided context. "
        "If the context doesn't contain the answer, say 'I don't have that information in the docs'."
    )

    user_message = (
        f"### RETRIEVED DOCUMENTATION:\n{context_text}\n\n"
        f"### USER QUESTION:\n{query}"
    )

    # Stream the response for a "live" feel
    with ant_client.messages.stream(
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        model=CLAUDE_MODEL,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print()  # Newline at end


def main():
    try:
        db = lancedb.connect(DB_PATH)
        tbl = db.open_table("dev_docs")
        vo_client = voyageai.Client()
        ant_client = anthropic.Anthropic()
    except Exception as e:
        print(f"Startup Error: {e}")
        print("Check your API keys and ensure you ran build_knowledge.py")
        return

    print("\n⚡ Terminal Dev Assistant (Voyage + Claude) Ready.")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            query = input("\n> ")
            if query.lower() in ["exit", "quit"]:
                break
            if not query.strip():
                continue

            print(f"   [Searching docs...]")
            results = search_docs(query, tbl, vo_client)

            if results.empty:
                print("   No relevant docs found.")
                continue

            print("   [Thinking...]\n")
            ask_claude(query, results, ant_client)

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
