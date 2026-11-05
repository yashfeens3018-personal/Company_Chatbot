"""
RAGAS evaluation of the Clef handbook RAG chatbot, judged by open-mistral-7b through LangChain.

Put this file next to test_rag_eval.py (it reuses its dataset loader and fallback detector).

    pip install ragas langchain-mistralai langchain-huggingface pandas python-dotenv

    # run the graph fresh on every answerable question, then score with RAGAS
    python -m yourpackage.test_ragas_eval --chat-module yourpackage.chat --limit 5

    # reuse answers/chunks already produced by test_rag_eval.py --mode e2e (no graph calls)
    python -m yourpackage.test_ragas_eval --chat-module yourpackage.chat --reuse-e2e eval_results_e2e.json
    (with --reuse-e2e the chat module is not imported, so --chat-module can be omitted)

Outputs (prefix set by --out, default "ragas_results"):
    <out>_ragas.csv           one row per question with every metric score
    <out>_ragas.json          same, but contexts kept as lists
    <out>_ragas_summary.json  overall + per-question-type means, NaN counts, skipped questions, run settings

Metrics (all scored by the same open-mistral-7b judge):
    faithfulness                          is the answer supported by the retrieved chunks?
    answer_relevancy                      does the answer address the question? (needs embeddings)
    llm_context_precision_with_reference  are the relevant chunks ranked high among the retrieved ones?
    context_recall                        do the retrieved chunks cover the reference answer?
    factual_correctness (--factual)       claim-level match of the answer vs the reference answer
"""
import argparse
import importlib
import json
import math
import time
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

try:  # run as `python -m yourpackage.test_ragas_eval`
    from .test_rag_eval import chunk_text, detect_fallback, load_dataset
except ImportError:  # run as a plain script from the same folder
    from test_rag_eval import chunk_text, detect_fallback, load_dataset

import ragas
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    FactualCorrectness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)
from ragas.run_config import RunConfig

warnings.filterwarnings("ignore", category=DeprecationWarning)  # ragas 0.4 deprecates ragas.metrics imports

load_dotenv()

JUDGE_MODEL = "open-mistral-7b"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # same model used at ingestion


# --------------------------------------------------------------------------- collecting answers + contexts
def collect_from_graph(items, chat, sleep):
    """Run the compiled LangGraph app on each question and keep the answer + the chunks it retrieved."""
    from langchain_core.messages import HumanMessage

    records = []
    for n, item in enumerate(items, 1):
        rec = {"id": item["id"], "question_type": item["question_type"], "question": item["question"],
               "reference": item["reference_answer"]}
        try:
            result = chat.app.invoke({"messages": [HumanMessage(content=item["question"])]})
            chunks = result.get("Retrieved_chunks") or []
            rec.update(
                response=result["messages"][-1].content,
                contexts=[chunk_text(c) for c in chunks],
                intent=(result.get("intent") or {}).get("intent"),
                rewritten_query=result.get("Rag_query"),
            )
        except Exception as exc:
            rec["error"] = repr(exc)
        records.append(rec)
        print(f"  [{n:>2}/{len(items)}] {item['id']} intent={rec.get('intent')} err={'error' in rec}")
        time.sleep(sleep)
    return records


def collect_from_e2e_file(items, path):
    """Reuse answers/chunks saved by `test_rag_eval.py --mode e2e` so the graph is not called again."""
    saved = {r["id"]: r for r in json.loads(Path(path).read_text(encoding="utf-8"))}
    records = []
    for item in items:
        rec = {"id": item["id"], "question_type": item["question_type"], "question": item["question"],
               "reference": item["reference_answer"]}
        old = saved.get(item["id"])
        if old is None:
            rec["error"] = "id not found in e2e results file"
        elif "error" in old:
            rec["error"] = old["error"]
        else:
            rec.update(
                response=old.get("answer", ""),
                contexts=[c["text"] for c in old.get("retrieved", [])],
                intent=old.get("intent"),
                rewritten_query=old.get("rewritten_query"),
            )
        records.append(rec)
    return records


def skip_reason(rec):
    """RAGAS cannot score a question with no answer or no retrieved chunks, so those are set aside (and reported)."""
    if rec.get("error"):
        return f"error: {rec['error'][:80]}"
    if not rec.get("contexts"):
        return f"no retrieved chunks (intent={rec.get('intent')})"
    fb = detect_fallback(rec.get("response"))
    if fb:
        return f"canned fallback reply ({fb})"
    return None


# --------------------------------------------------------------------------- scoring
def build_judge():
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_mistralai import ChatMistralAI

    class SafeChatMistralAI(ChatMistralAI):
        """ChatMistralAI sums token_usage values when it merges several generations (ResponseRelevancy asks for 3).
        Newer Mistral responses contain nested dicts there, and `dict += dict` raises TypeError.
        Per-message usage_metadata is unaffected; only the merged llm_output usage is dropped."""

        def _combine_llm_outputs(self, llm_outputs):
            return {"model_name": self.model}

    llm = SafeChatMistralAI(model=JUDGE_MODEL, temperature=0, max_retries=5)  # reads MISTRAL_API_KEY from env
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return LangchainLLMWrapper(llm), LangchainEmbeddingsWrapper(embeddings)


def clean(x):
    """NaN -> None so the JSON files are valid."""
    return None if isinstance(x, float) and math.isnan(x) else x


def summarise(df, metric_cols):
    overall = {}
    for m in metric_cols:
        s = df[m]
        overall[m] = {"mean": clean(float(s.mean())) if s.notna().any() else None,
                      "n_valid": int(s.notna().sum()), "n_nan": int(s.isna().sum())}
    by_type = {}
    for t, g in df.groupby("question_type"):
        by_type[t] = {"n": int(len(g)), **{m: clean(float(g[m].mean())) if g[m].notna().any() else None for m in metric_cols}}
    return overall, by_type


def print_summary(overall, by_type, n_total, n_scored, skipped):
    print("\n" + "=" * 72)
    print(f"RAGAS (judge: {JUDGE_MODEL})   scored {n_scored}/{n_total} answerable questions")
    print("=" * 72)
    print(f"{'metric':<40}{'mean':>8}{'valid':>8}{'NaN':>6}")
    for m, v in overall.items():
        mean = "  n/a" if v["mean"] is None else f"{v['mean']:8.3f}"
        print(f"{m:<40}{mean:>8}{v['n_valid']:>8}{v['n_nan']:>6}")
    print("\nBy question type:")
    for t, v in by_type.items():
        cells = "  ".join(f"{k}={'n/a' if x is None else format(x, '.2f')}" for k, x in v.items() if k != "n")
        print(f"  {t:<13}(n={v['n']}) {cells}")
    if skipped:
        print(f"\nSkipped (not scored, so the means above exclude them): {len(skipped)}")
        for s in skipped[:10]:
            print(f"  {s['id']}: {s['reason']}")
    nan_total = sum(v["n_nan"] for v in overall.values())
    if nan_total:
        print(f"\n{nan_total} metric score(s) are NaN: the judge returned output RAGAS could not parse "
              f"or a call timed out. With a 7B judge this is common; check the NaN column above.")


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chat-module", help="dotted path of your chat file (not needed with --reuse-e2e)")
    ap.add_argument("--reuse-e2e", help="path to eval_results_e2e.json from test_rag_eval.py to reuse answers/chunks")
    ap.add_argument("--dataset", default=None, help="dataset .json/.csv (default: clef_rag_eval_dataset.* next to this file)")
    ap.add_argument("--types", nargs="*", help="only these question types, e.g. direct specific")
    ap.add_argument("--limit", type=int, help="only the first N answerable questions (smoke test)")
    ap.add_argument("--factual", action="store_true", help="also compute factual_correctness (extra judge calls)")
    ap.add_argument("--workers", type=int, default=2, help="parallel judge calls (lower if you hit Mistral rate limits)")
    ap.add_argument("--timeout", type=int, default=180, help="seconds per judge call")
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between graph calls (fresh runs only)")
    ap.add_argument("--out", default="ragas_results", help="output file prefix")
    args = ap.parse_args()

    here = Path(__file__).parent
    dataset_path = args.dataset or next(
        (str(p) for p in (here / "clef_rag_eval_dataset.json", here / "clef_rag_eval_dataset.csv") if p.exists()), None)
    if not dataset_path or not Path(dataset_path).exists():
        raise SystemExit("Dataset not found. Put clef_rag_eval_dataset.json/.csv next to this file or pass --dataset PATH")

    # RAGAS needs a reference answer, so only answerable questions are scored
    items = [d for d in load_dataset(dataset_path) if d["answerable"]]
    if args.types:
        items = [d for d in items if d["question_type"] in args.types]
    if args.limit:
        items = items[: args.limit]
    print(f"Loaded {len(items)} answerable questions")

    # 1. answers + retrieved contexts
    if args.reuse_e2e:
        records = collect_from_e2e_file(items, args.reuse_e2e)
    else:
        if not args.chat_module:
            raise SystemExit("Pass --chat-module (or --reuse-e2e FILE)")
        chat = importlib.import_module(args.chat_module)
        print("Running the graph...")
        records = collect_from_graph(items, chat, args.sleep)

    scorable, skipped = [], []
    for r in records:
        reason = skip_reason(r)
        (skipped.append({"id": r["id"], "reason": reason}) if reason else scorable.append(r))
    if not scorable:
        raise SystemExit("Nothing to score (every question errored, was misrouted, or got a canned fallback).")

    # 2. RAGAS
    evaluator_llm, evaluator_embeddings = build_judge()
    metrics = [Faithfulness(), ResponseRelevancy(), LLMContextPrecisionWithReference(), LLMContextRecall()]
    if args.factual:
        metrics.append(FactualCorrectness())

    samples = [
        SingleTurnSample(user_input=r["question"], retrieved_contexts=r["contexts"],
                         response=r["response"], reference=r["reference"])
        for r in scorable
    ]
    print(f"\nScoring {len(samples)} questions with {len(metrics)} metrics (judge {JUDGE_MODEL})...")
    result = evaluate(
        dataset=EvaluationDataset(samples=samples),
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        run_config=RunConfig(timeout=args.timeout, max_retries=10, max_wait=60, max_workers=args.workers),
        raise_exceptions=False,  # a failed judge call becomes NaN instead of killing the run
        show_progress=True,
    )
    df = result.to_pandas()  # same row order as `samples`
    metric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    df.insert(0, "id", [r["id"] for r in scorable])
    df.insert(1, "question_type", [r["question_type"] for r in scorable])
    df["intent"] = [r.get("intent") for r in scorable]
    df["rewritten_query"] = [r.get("rewritten_query") for r in scorable]

    # 3. save
    out = args.out
    df.to_json(f"{out}_ragas.json", orient="records", indent=2, force_ascii=False)
    flat = df.copy()
    flat["retrieved_contexts"] = flat["retrieved_contexts"].apply(lambda c: "\n---\n".join(c))
    flat.to_csv(f"{out}_ragas.csv", index=False, encoding="utf-8-sig")

    overall, by_type = summarise(df, metric_cols)
    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "judge_model": JUDGE_MODEL,
        "embedding_model": EMBED_MODEL,
        "ragas_version": ragas.__version__,
        "source": f"reused {args.reuse_e2e}" if args.reuse_e2e else f"graph run via {args.chat_module}",
        "n_answerable": len(items),
        "n_scored": len(scorable),
        "n_skipped": len(skipped),
        "skipped": skipped,
        "overall": overall,
        "by_question_type": by_type,
    }
    Path(f"{out}_ragas_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print_summary(overall, by_type, len(items), len(scorable), skipped)
    print(f"\nSaved {out}_ragas.csv / .json and {out}_ragas_summary.json")


if __name__ == "__main__":
    main()