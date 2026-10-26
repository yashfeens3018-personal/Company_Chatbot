from langchain_community.document_loaders import GitLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os
from dotenv import load_dotenv

load_dotenv()

db_url=os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL is missing")

loader = GitLoader(
    clone_url="https://github.com/clef/handbook.git",
    repo_path="./data/clef-handbook",
    branch="master",
    file_filter=lambda path: (
    path.endswith(".md")
    and not any(
        path.endswith(name)
        for name in [
            "Clef Offer Letter.md",
            "Acknowledgment of Receipt.md",
            "Acknowledgement of Receipt.md",
            "Acknowledgement of Receipt of Changes.md",
            "README.md"
        ]
    )
),
)

documents = loader.load()

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,strip_headers=True
)

md_header_splits = []

for doc in documents:
    splits = markdown_splitter.split_text(doc.page_content)

    for split in splits:
        split.metadata.update(doc.metadata)

    md_header_splits.extend(splits)

chunk_size = 500
chunk_overlap = 100
text_splitter = RecursiveCharacterTextSplitter(
chunk_size=chunk_size, chunk_overlap=chunk_overlap)
splits = text_splitter.split_documents(md_header_splits)

embeddings=HuggingFaceEmbeddings(model_name='BAAI/bge-small-en-v1.5')

vector_store = Chroma(
    collection_name="Company_data",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db", 
)

vector_store.delete_collection()
vector_store = Chroma(
    collection_name="Company_data",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)
vector_store.add_documents(documents=splits)
print("saved the chunks embeddings in the vector store(ChromaDb)")

# query = "What are the current healthcare policies for employees?"

# docs = vector_store.similarity_search(query, k=8)

# for i, doc in enumerate(docs, 1):
#     print(f"\n--- Chunk {i} ---")
#     print(doc.page_content)
#     print("File:", doc.metadata.get("file_name"))