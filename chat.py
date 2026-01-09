from dotenv import load_dotenv

load_dotenv()  # This loads the variables from the .env file
import lancedb
from sentence_transformers import SentenceTransformer
import sys
import pandas as pd


# CONFIGURATION
DB_PATH = "./docs-ai/my_knowledge_db"
MODEL_NAME = "all-MiniLM-L6-v2"
MAX_CONTEXT_CHUNKS = 3  # How many snippets to retrieve


def rerank_documents(query, documents, model):
    """
    Simple reranking function using sentence similarity
    (Placeholder for the missing function)
    """
    # For now, just return the documents as-is
    # In a full implementation, this would use a reranking model
    return documents[:MAX_CONTEXT_CHUNKS]


def format_prompt(query, results):
    """
    Format the results into a prompt for Claude/ChatGPT
    """
    context_text = ""
    for _, row in results.iterrows():
        context_text += f"---\\nSOURCE: {row['filename']}\\nCONTENT:\\n{row['text']}\\n"

    prompt = f"""Based on the following legal documents, please answer this question: {query}

### LEGAL CONTEXT:
{context_text}

### INSTRUCTIONS:
- Use ONLY the provided context to answer
- Cite specific sources when possible
- If the answer isn't in the context, state that clearly
- Provide legal reasoning for your conclusions

### QUESTION:
{query}"""

    return prompt


def get_search_results(query, tbl, model):
    """
    Embeds the query and searches the LanceDB table.
    """
    # 1. Convert question to vector
    query_vector = model.encode([query])[0]

    # 2. Search DB (limit to top N most relevant chunks)
    results = tbl.search(query_vector).limit(MAX_CONTEXT_CHUNKS).to_pandas()
    return results


def ask_claude(query, context_list, ant_client):
    # 1. Build the Context String from your docs
    context_text = ""
    for item in context_list:
        # We include the filename and relevance score for transparency
        context_text += f"---\nSOURCE: {item['filename']} (Relevance: {item['score']:.2f})\nCONTENT:\n{item['text']}\n"

    # 2. The Static System Prompt (The Persona)
    # This tells Claude HOW to behave.
    system_instruction = (
        "You are Lex Ancile, an advanced legal AI assistant designed to provide precise and contextual legal insights.\n\n"
        "### PURPOSE\n"
        "Your purpose is to provide legal assistance and to democratize legal access.\n\n"
        "### KNOWLEDGE DOMAINS\n"
        "You have access to legal data for:\n"
        "- United States (Constitution, Statutes, Regulations, Case Law)\n"
        "- Washington State (Constitution, Statutes, Regulations, Case Law)\n"
        "- Tennessee (Constitution, Statutes, Regulations, Case Law)\n\n"
        "### GUIDELINES\n"
        "1. Analyze the input to ensure it is a valid legal query.\n"
        "2. Use ONLY the provided context to answer. Do not use outside knowledge unless necessary to interpret terms.\n"
        "3. Cite specific legal provisions (Statutes, Case names) from the context whenever possible.\n"
        "4. If the provided context does not contain the answer, state: 'The provided legal documents do not contain information regarding this specific query.'\n"
    )

    # 3. The User Message (The Data)
    # This combines the retrieved docs with the user's actual question.
    user_message = (
        f"### RETRIEVED LEGAL CONTEXT:\n{context_text}\n\n"
        f"### USER QUESTION:\n{query}"
    )

    # 4. Send to Claude
    print("   [Lex Ancile is analyzing...]\n")
    with ant_client.messages.stream(
        max_tokens=10000,  # Increased for detailed legal analysis
        system=system_instruction,
        messages=[{"role": "user", "content": user_message}],
        model=CLAUDE_MODEL,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print()  # Newline at end


def main():
    print("Initializing Chat Context Engine...")

    # Load resources once (fast)
    try:
        # Load DB and Tables
        db = lancedb.connect(DB_PATH)
        tbl = db.open_table("dev_docs")

        # Load the sentence transformer model
        model = SentenceTransformer(MODEL_NAME)

    except Exception as e:
        print(f"Startup Error: {e}")
        print("Check your .env file and database path.")
        return

    print("\n✅ Ready! Type your question below (or 'exit' to quit).")
    print("-------------------------------------------------------")

    while True:
        try:
            user_input = input("\nStart a chat > ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break

            if not user_input.strip():
                continue

            print("🔍 Searching your knowledge base...")
            results = get_search_results(user_input, tbl, model)

            if results.empty:
                print("No relevant documentation found.")
                continue

            # Generate the final prompt
            final_prompt = format_prompt(user_input, results)

            print("\n" + "=" * 20 + " COPIED TO CLIPBOARD (Simulated) " + "=" * 20)
            print("Here is the context the AI needs to answer your question:\n")
            print(final_prompt)
            print("=" * 60)
            print("(Copy the text above and paste it into ChatGPT/Claude/Gemini)")

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
