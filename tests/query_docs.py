import lancedb
from sentence_transformers import SentenceTransformer

# Load DB and Model
db = lancedb.connect("./docs-ai/my_knowledge_db")
tbl = db.open_table("dev_docs")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Ask a question
query = "How does user authentication work?"
query_vector = model.encode([query])[0]

# Search
results = tbl.search(query_vector).limit(3).to_pandas()

print("--- AI Context Found ---")
for index, row in results.iterrows():
    print(f"Source: {row['filename']}")
    print(f"Content snippet: {row['text'][:200]}...\n")
