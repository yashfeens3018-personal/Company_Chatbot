from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

vector_store = Chroma(
    collection_name="Company_data",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)