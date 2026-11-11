import csv
import sys

import numpy as np


def get_embeddings(model_name: str | None):
    if model_name:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model_name)
    from company_project.AI_Chat.Vector_db.vector_db import embeddings
    return embeddings


def main(path: str, model_name: str | None = None) -> None:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    embeddings = get_embeddings(model_name)
    print(f"Model: {model_name or 'vector_db.py embeddings'}")

    a = np.array(embeddings.embed_documents([r["query_a"] for r in rows]))
    b = np.array(embeddings.embed_documents([r["query_b"] for r in rows]))
    # normalise explicitly: dot product == cosine similarity
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    b /= np.linalg.norm(b, axis=1, keepdims=True)
    sims = (a * b).sum(axis=1)
    should_hit = np.array([r["should_hit"].strip().lower() in ("1", "true", "yes", "y") for r in rows])

    if should_hit.sum() == 0 or (~should_hit).sum() == 0:
        sys.exit("Need both should_hit=1 and should_hit=0 rows.")

    pos, neg = sims[should_hit], sims[~should_hit]
    separation = float((pos[:, None] > neg[None, :]).mean())
    print(f"{len(pos)} paraphrase pairs      : min={pos.min():.3f}  mean={pos.mean():.3f}")
    print(f"{len(neg)} different-answer pairs: max={neg.max():.3f}  mean={neg.mean():.3f}")
    print(f"Separation score: {separation:.3f}\n")

    print("threshold  hit_rate_on_paraphrases  false_hits")
    safe = None
    for t in np.arange(0.70, 1.0, 0.01):
        t = round(float(t), 2)
        served = sims >= t
        hit_rate = served[should_hit].mean()
        false_hits = int(served[~should_hit].sum())
        print(f"{t:9.2f}  {hit_rate:23.0%}  {false_hits:10d}")
        if false_hits == 0 and safe is None:
            safe = t

    if safe is None:
        print("\nEvery threshold up to 0.99 still has false hits. Look at the hard negatives below.")
    else:
        print(f"\nLowest threshold with zero false hits: {safe:.2f}  (consider adding ~0.01-0.02 margin)")

    print("\nMost dangerous negatives (different answer, highest similarity):")
    for i in np.argsort(-np.where(should_hit, -1, sims))[:5]:
        if not should_hit[i]:
            print(f"  {sims[i]:.3f}  A: {rows[i]['query_a']!r}\n         B: {rows[i]['query_b']!r}")

    print("\nHardest paraphrases (should hit, lowest similarity):")
    for i in np.argsort(np.where(should_hit, sims, 2))[:5]:
        if should_hit[i]:
            print(f"  {sims[i]:.3f}  A: {rows[i]['query_a']!r}\n         B: {rows[i]['query_b']!r}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)