import os, json, hashlib
from pathlib import Path
from git import Repo  # GitPython, already installed as a GitLoader dependency
from dotenv import load_dotenv
from langchain_community.document_loaders import GitLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

REPO_URL = "https://github.com/clef/handbook.git"
REPO_PATH = "./data/clef-handbook"
BRANCH = "master"
PERSIST_DIR = "./chroma_langchain_db"
MANIFEST_PATH = os.path.join(PERSIST_DIR, "manifest.json")

CHUNK_SIZE, CHUNK_OVERLAP = 500, 100
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
# "context_header" is a version tag: bump it whenever the header format below changes,
# so the whole index is rebuilt (old chunks were embedded without / with a different header).
CONFIG = {
    "chunk_size": CHUNK_SIZE,
    "chunk_overlap": CHUNK_OVERLAP,
    "model": EMBED_MODEL,
    "context_header": 1,
}

EXCLUDED = [
    "Clef Offer Letter.md", "Acknowledgment of Receipt.md",
    "Acknowledgement of Receipt.md", "Acknowledgement of Receipt of Changes.md",
    "README.md",
]

HEADER_KEYS = ("Header 1", "Header 2", "Header 3")


def add_context_header(chunk):
    """Prepend 'Document: ... / Section: A > B > C' to the chunk text so the embedding
    (and the LLM) knows where the chunk came from. Headers were stripped by the splitter,
    so without this a chunk like 'CLEF, INC.' has no idea it belongs to the mission statement."""
    meta = chunk.metadata
    doc_title = Path(meta.get("source", "")).stem
    breadcrumb = " > ".join(meta[k] for k in HEADER_KEYS if meta.get(k))

    lines = []
    if doc_title:
        lines.append(f"Document: {doc_title}")
    if breadcrumb:
        lines.append(f"Section: {breadcrumb}")

    meta["doc_title"] = doc_title  # also kept as metadata (useful for filtering/debugging later)
    meta["section_path"] = breadcrumb
    if lines:
        chunk.page_content = "\n".join(lines) + "\n\n" + chunk.page_content
    return chunk


if os.path.exists(REPO_PATH):
    repo = Repo(REPO_PATH)
    repo.remotes.origin.pull(BRANCH)

loader = GitLoader(
    clone_url=REPO_URL,
    repo_path=REPO_PATH,
    branch=BRANCH,
    file_filter=lambda p: p.endswith(".md") and not any(p.endswith(n) for n in EXCLUDED),
)
documents = loader.load()

# 2. Hash current files and compare with the manifest
def sha(text): return hashlib.sha256(text.encode("utf-8")).hexdigest()

current = {d.metadata["source"]: d for d in documents}
current_hashes = {src: sha(d.page_content) for src, d in current.items()}

manifest = {"config": CONFIG, "files": {}}
if os.path.exists(MANIFEST_PATH):
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

try:
    vector_store = Chroma(
        collection_name="Company_data",
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
except Exception as e:
    print(f"Failed to initialize Chroma: {e}")
    raise

# Config changed -> full rebuild
if manifest.get("config") != CONFIG:
    print("Config changed, rebuilding everything")
    vector_store.delete_collection()
    vector_store = Chroma(
        collection_name="Company_data",
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
    manifest = {"config": CONFIG, "files": {}}

old_hashes = manifest["files"]

added    = [s for s in current_hashes if s not in old_hashes]
modified = [s for s in current_hashes if s in old_hashes and old_hashes[s] != current_hashes[s]]
deleted  = [s for s in old_hashes if s not in current_hashes]

print(f"added={len(added)} modified={len(modified)} deleted={len(deleted)} "
      f"unchanged={len(current_hashes) - len(added) - len(modified)}")

# 3. Remove stale chunks (modified + deleted files)
stale = modified + deleted
if stale:
    try:
        vector_store.delete(where={"source": {"$in": stale}})
    except Exception as e:
        print(f"Failed to delete stale documents: {e}")
        raise

# 4. Split + add context header + embed only added/modified files
to_process = [current[s] for s in added + modified]

if to_process:
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")],
        strip_headers=True,
    )
    md_splits = []
    for doc in to_process:
        for split in markdown_splitter.split_text(doc.page_content):
            split.metadata.update(doc.metadata)  # keeps "source" for later deletes
            md_splits.append(split)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    splits = text_splitter.split_documents(md_splits)

    # Add the header AFTER splitting: every chunk gets it, and it doesn't eat into chunk_size
    # or get split away from the text it describes.
    splits = [add_context_header(c) for c in splits]

    try:
        vector_store.add_documents(splits)
    except Exception as e:
        print(f"Failed to insert documents into Chroma: {e}")
        raise

# 5. Save manifest only after everything succeeded (write it, atomically)
manifest["config"] = CONFIG
manifest["files"] = current_hashes
os.makedirs(PERSIST_DIR, exist_ok=True)
tmp_path = MANIFEST_PATH + ".tmp"
with open(tmp_path, "w") as f:
    json.dump(manifest, f, indent=2)
os.replace(tmp_path, MANIFEST_PATH)  # a crash mid-write can't leave a corrupt manifest

print("Index up to date")