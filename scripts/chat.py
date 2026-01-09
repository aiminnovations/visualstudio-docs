import lancedb
import voyageai
import anthropic
import sys

# CONFIGURATION
DB_PATH = "./docs-ai/my_knowledge_db"
EMBEDDING_MODEL = "voyage-law-3"
RERANK_MODEL = "rerank-2"  # Optimized for code/technical accuracy
CLAUDE_MODEL = "claude-sonnet-4-5"


def retrieve_and_rerank(query, tbl, vo_client):
    """
    1. Vector Search (Fast, Broad) -> Get top 20
    2. Voyage Rerank (Slow, Smart) -> Get top 5
    """
    # STAGE 1: Fast Vector Search (Broad sweep)
    query_vector = vo_client.embed(
        [query], model=EMBEDDING_MODEL, input_type="query"
    ).embeddings[0]

    # Get top 20 candidates (broad context)
    initial_results = tbl.search(query_vector).limit(20).to_pandas()

    if initial_results.empty:
        return []

    # Prepare documents for Reranker
    # We need a list of strings: [chunk1_text, chunk2_text, ...]
    documents = initial_results["text"].tolist()

    # STAGE 2: Reranking
    rerank_response = vo_client.rerank(
        query=query,
        documents=documents,
        model=RERANK_MODEL,
        top_k=5,  # Refine down to the absolute best 5
    )

    # Map back to the original metadata (filename, etc)
    final_results = []
    for r in rerank_response.results:
        # r.index corresponds to the index in the 'documents' list we sent
        original_row = initial_results.iloc[r.index]
        final_results.append(
            {
                "filename": original_row["filename"],
                "text": original_row["text"],
                "score": r.relevance_score,
            }
        )

    return final_results


def ask_claude(query, context_list, ant_client):
    context_text = ""
    for item in context_list:
        context_text += f"---\nFILE: {item['filename']} (Relevance: {item['score']:.2f})\nCONTENT:\n{item['text']}\n"

    system_prompt = (
        "You are an expert trial lawyer specializing in defense. Answer using ONLY the provided context."
        "If the answer isn't in the context, say so."
    )
    user_message = f"### CONTEXT:\n{context_text}\n\n### QUESTION:\n{query}"

    with ant_client.messages.stream(
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        model=CLAUDE_MODEL,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print()


def main():
    try:
        db = lancedb.connect(DB_PATH)
        tbl = db.open_table("dev_docs")
        vo_client = voyageai.Client()
        ant_client = anthropic.Anthropic()
    except Exception as e:
        print(f"Startup Error: {e}")
        return

    print("\n⚡ Voyage RAG (Law-3 + Rerank-2) Ready. Type 'exit' to quit.\n")

    while True:
        query = input("\n> ")
        if query.lower() in ["exit", "quit"]:
            break
        if not query.strip():
            continue

        print("   [1/3] Retrieving candidates...")
        # See how we pass the client to the new function
        results = retrieve_and_rerank(query, tbl, vo_client)

        if not results:
            print("   No docs found.")
            continue

        print("   [2/3] Reranking complete. Top matches:")
        for r in results[:2]:  # Show user what we found (optional)
            print(f"         - {r['filename']} (Score: {r['score']:.3f})")

        print("   [3/3] Generating answer...\n")
        ask_claude(query, results, ant_client)


if __name__ == "__main__":
    main()
