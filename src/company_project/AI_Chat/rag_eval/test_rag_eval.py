"""
    python -m yourpackage.test_rag_eval --chat-module yourpackage.chat --mode retrieval
    python -m yourpackage.test_rag_eval --chat-module yourpackage.chat --mode e2e --judge
    python -m yourpackage.test_rag_eval --chat-module yourpackage.chat --mode intent
    python -m yourpackage.test_rag_eval --chat-module yourpackage.chat --mode both --limit 10

Modes
  retrieval : raw question -> vector_store (k up to 5). No LLM calls. Free and fast.
  intent    : question -> chat.intent_classification ONLY (1 Mistral call each, no DB, no retrieval).
              Scores the 50 handbook questions (expected RAG_Query) plus built-in control
              questions (database / mixed / irrelevant / unclear / extra handbook) so you can see
              whether a prompt change fixed routing without breaking the other intents.
  e2e       : question -> your compiled LangGraph `app`. Checks intent routing, the
              rewritten rag_query, the 3 chunks your graph retrieves, and the answer.
              Unanswerable questions are graded as grounded decline / fallback / answered.
  both      : retrieval + e2e.      all : retrieval + intent + e2e.
  compare   : reads eval_results_retrieval.json and eval_results_e2e.json (same --out prefix) and lists
              questions where the graph's routing / query rewrite lost evidence the raw question found.
"""
import argparse
import csv
import importlib
import json
import re
import time
from collections import defaultdict
from pathlib import Path

KS = (1, 3, 5, 7, 8) 
DECLINE_PATTERNS = re.compile(
    r"(does not|doesn't|do not|don't|did not|didn't|cannot|can't|could not|couldn't|unable to)\s+"
    r"(contain|mention|provide|specify|include|say|state|find|answer|have)|"
    r"not (mentioned|specified|provided|available|stated|included|found|covered)|"
    r"no (information|mention|details|data)|insufficient|missing|"
    r"(information|details?) (is|are) (not|missing|unavailable)|i (am|'m) (sorry|not sure)",
    re.I,
)


# Fixed replies from the chatbot's non-answer nodes (see chat.py). Matched on normalised lowercase text.
FALLBACK_MARKERS = {
    "clarification_fallback": ("could not understand your previous request", "make your query a bit more clear"),
    "irrelevant_fallback": ("i can help with company records, policies, documents",),
    "other_non_answer": ("not implemented yet", "missing these mandatory arguments"),
}
SAFE_CATEGORIES = ("grounded_decline", "clarification_fallback", "irrelevant_fallback", "other_non_answer")

# Held-out routing controls: (question, accepted intents). None of these appear in the prompt examples or the 50-question set.
ROUTING_CONTROLS = [
    ("What is the current status of ticket 212?", {"Database_Query"}),
    ("Which assets are assigned to Fatima Noor?", {"Database_Query"}),
    ("Show me all announcements published this week.", {"Database_Query"}),
    ("How many sick leave days does employee 8 have remaining?", {"Database_Query"}),
    ("Who is the project manager of the Apollo project?", {"Database_Query"}),
    ("What is the job title and department of Sarah Khan?", {"Database_Query"}),
    ("Which of my leave requests are still pending?", {"Database_Query"}),
    ("What is the company's sabbatical policy, and what is the status of my latest leave request?", {"Mixed:have both queries"}),
    ("How does the complaint procedure work, and which tickets are assigned to Omar Siddiqui?", {"Mixed:have both queries"}),
    ("What's the weather like in Karachi today?", {"Irrelevant"}),
    ("Write me a short poem about the ocean.", {"Irrelevant"}),
    ("Can you check that for me?", {"Unclear", "Irrelevant"}),
    ("What is the company's policy on equal opportunity employment?", {"RAG_Query"}),
    ("How does the company handle budgeting for team expenses?", {"RAG_Query"}),
    ("What file sharing practices does the company expect from employees?", {"RAG_Query"}),
    ("What is Sarah Khan's salary?", {"Database_Query"}),
    ("How are Clef's convertible notes converted into equity?", {"RAG_Query"}),
    ("What happens to my ownership percentage when the company issues new shares?", {"RAG_Query"}),
]


# --------------------------------------------------------------------------- helpers
def norm(text) -> str:
    text = str(text or "")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[*#`]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def detect_fallback(answer):
    """Return the fallback category if the reply is one of the bot's canned non-answers, else None."""
    a = norm(answer)
    for category, markers in FALLBACK_MARKERS.items():
        if any(m in a for m in markers):
            return category
    return None


def chunk_text(chunk) -> str:
    return getattr(chunk, "page_content", str(chunk))


def chunk_meta(chunk) -> dict:
    return getattr(chunk, "metadata", {}) or {}


def file_matches(meta: dict, doc_path: str) -> bool:
    """GitLoader stores the repo-relative path in `source` / `file_path` and the bare name in `file_name`."""
    want = doc_path.replace("\\", "/").lstrip("./").lower()
    want_name = Path(doc_path).name.lower()
    for key in ("source", "file_path", "file_name", "path"):
        value = meta.get(key)
        if not value:
            continue
        v = str(value).replace("\\", "/").lstrip("./").lower()
        if v.endswith(want) or Path(v).name == want_name:
            return True
    return False


def evidence_matches(chunk, ev: dict) -> bool:
    """A chunk 'contains' an evidence passage if it has the keyphrase, or is a (large) slice of the passage."""
    c = norm(chunk_text(chunk))
    if norm(ev["keyphrase"]) in c:
        return True
    return len(c) >= 60 and c in norm(ev["text"])


def analyse_chunks(item: dict, chunks: list) -> dict:
    """Per-question retrieval metrics for an ordered list of chunks."""
    evidence = item["relevant_evidence"]
    acceptable_files = set(item["source_documents"]) | set(item.get("also_acceptable_sources", []))
    out = {}
    first_rank = None
    for rank, ch in enumerate(chunks, start=1):
        if any(evidence_matches(ch, ev) for ev in evidence):
            first_rank = rank
            break
    out["first_evidence_rank"] = first_rank
    for k in KS:
        top = chunks[:k]
        out[f"file_hit@{k}"] = any(file_matches(chunk_meta(c), f) for c in top for f in acceptable_files)
        covered = [any(evidence_matches(c, ev) for c in top) for ev in evidence]
        out[f"evidence_hit@{k}"] = any(covered)
        out[f"evidence_coverage@{k}"] = sum(covered) / len(covered)
        out[f"evidence_full@{k}"] = all(covered)
    out["mrr"] = 1 / first_rank if first_rank and first_rank <= KS[-1] else 0.0
    return out


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def short(text, n=110):
    text = re.sub(r"\s+", " ", str(text))
    return text if len(text) <= n else text[: n - 1] + "…"


# --------------------------------------------------------------------------- retrieval-only
def run_retrieval(dataset, vector_store, max_k):
    rows = []
    for item in dataset:
        row = {"id": item["id"], "question_type": item["question_type"], "question": item["question"]}
        try:
            try:
                scored = vector_store.similarity_search_with_score(item["question"], k=max_k)
                chunks = [c for c, _ in scored]
                row["top1_score"] = float(scored[0][1]) if scored else None
            except Exception:
                chunks = vector_store.similarity_search(item["question"], k=max_k)
                row["top1_score"] = None
            row["retrieved"] = [
                {"file": chunk_meta(c).get("source") or chunk_meta(c).get("file_path"), "text": chunk_text(c)}
                for c in chunks
            ]
            if item["answerable"]:
                row.update(analyse_chunks(item, chunks))
        except Exception as exc:  # keep going on API / DB errors
            row["error"] = repr(exc)
        rows.append(row)
    return rows


def print_retrieval_summary(rows):
    types = ["direct", "paraphrased", "specific", "multi-part"]
    header = f"{'type':<12}{'n':>3} " + " ".join(f"file@{k:<2}" for k in KS) + " | " + " ".join(f"evid@{k:<2}" for k in KS) + f" |    MRR | full@{KS[-1]} (all evidence)"
    print("\n" + "=" * len(header))
    print("RETRIEVAL-ONLY (raw question -> vector_store)")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    groups = {t: [r for r in rows if r["question_type"] == t and "error" not in r] for t in types}
    groups["ALL answerable"] = [r for t in types for r in groups[t]]
    for name, rs in groups.items():
        if not rs:
            continue
        files = " ".join(f"{mean(r[f'file_hit@{k}'] for r in rs):6.2f} " for k in KS)
        evid = " ".join(f"{mean(r[f'evidence_hit@{k}'] for r in rs):6.2f} " for k in KS)
        print(f"{name:<12}{len(rs):>3} {files}| {evid}| {mean(r['mrr'] for r in rs):6.2f} | {mean(r[f'evidence_full@{KS[-1]}'] for r in rs):6.2f}")
    ans_scores = [r["top1_score"] for r in rows if r["question_type"] != "unanswerable" and r.get("top1_score") is not None]
    una_scores = [r["top1_score"] for r in rows if r["question_type"] == "unanswerable" and r.get("top1_score") is not None]
    if ans_scores and una_scores:
        print(f"\nTop-1 score (Chroma distance, LOWER = closer): answerable mean {mean(ans_scores):.3f} vs unanswerable mean {mean(una_scores):.3f}")
        print("If these overlap heavily, a score threshold alone will not make the bot refuse unanswerable questions.")
    errors = [r for r in rows if "error" in r]
    if errors:
        print(f"\n{len(errors)} question(s) errored, e.g. {errors[0]['id']}: {errors[0]['error']}")


def print_misses(rows, k=KS[-1], limit=10):
    misses = [r for r in rows if r["question_type"] != "unanswerable" and "error" not in r and not r[f"evidence_hit@{k}"]]
    if not misses:
        return
    print(f"\nQuestions with NO evidence in top-{k} ({len(misses)} total, showing {min(limit, len(misses))}):")
    for r in misses[:limit]:
        print(f"  {r['id']} [{r['question_type']}] {short(r['question'], 90)}")
        for i, ch in enumerate(r["retrieved"][:3], 1):
            print(f"      {i}. {ch['file']} :: {short(ch['text'], 80)}")


# --------------------------------------------------------------------------- end-to-end
def run_intent(dataset, chat, sleep, controls=True):
    """Call ONLY the intent classifier (one Mistral call per question). Prints are silenced."""
    import contextlib
    import io

    from langchain_core.messages import HumanMessage

    cases = [(d["id"], d["question_type"], d["question"], {"RAG_Query"}) for d in dataset]
    if controls:
        cases += [(f"c{i:02d}", "control", q, exp) for i, (q, exp) in enumerate(ROUTING_CONTROLS, 1)]
    rows = []
    for n, (qid, qtype, question, expected) in enumerate(cases, 1):
        row = {"id": qid, "question_type": qtype, "question": question, "expected": "/".join(sorted(expected))}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                out = chat.intent_classification({"messages": [HumanMessage(content=question)]})
            got = out["intent"]["intent"]
            row.update(intent=got, correct=got in expected, reason=out["intent"].get("reason"), rewritten_query=out.get("Rag_query"), database_query=out.get("Database_query"))
        except Exception as exc:
            row["error"] = repr(exc)
        rows.append(row)
        print(f"  [{n:>2}/{len(cases)}] {qid} expected={row['expected']} got={row.get('intent')}")
        time.sleep(sleep)
    return rows


def print_intent_summary(rows):
    ok = [r for r in rows if "error" not in r]
    print("\n" + "=" * 72)
    print("INTENT CLASSIFICATION ONLY")
    print("=" * 72)
    print(f"Completed without error: {len(ok)}/{len(rows)}")
    hand = [r for r in ok if r["question_type"] != "control"]
    ctrl = [r for r in ok if r["question_type"] == "control"]
    if hand:
        print(f"\nHandbook questions (expected RAG_Query): {sum(r['correct'] for r in hand)}/{len(hand)} = {mean(r['correct'] for r in hand):.2f}")
        for t in ["direct", "paraphrased", "specific", "multi-part", "unanswerable"]:
            rs = [r for r in hand if r["question_type"] == t]
            if rs:
                print(f"   {t:<13}{sum(r['correct'] for r in rs)}/{len(rs)}")
    if ctrl:
        print(f"\nControls (should NOT all go to RAG): {sum(r['correct'] for r in ctrl)}/{len(ctrl)} = {mean(r['correct'] for r in ctrl):.2f}")
        print("   A prompt that fixes the handbook score by sending everything to RAG will fail these.")
    wrong = [r for r in ok if not r["correct"]]
    if wrong:
        print(f"\nMisrouted ({len(wrong)}):")
        for r in wrong:
            print(f"   {r['id']} expected {r['expected']} -> {r['intent']}: {short(r['question'], 70)}")
            print(f"        model's reason: {short(r.get('reason'), 100)}")
    confusion = defaultdict(int)
    for r in ok:
        confusion[(r["expected"], r["intent"])] += 1
    print("\nConfusion (expected -> got : count):")
    for (e, g), c in sorted(confusion.items(), key=lambda kv: -kv[1]):
        print(f"   {e:<26}-> {g:<26}: {c}")


def run_compare(prefix, k):
    """Compare raw-question retrieval (retrieval mode) with the graph's rewritten query (e2e mode). Needs both result files."""
    try:
        raw = {r["id"]: r for r in json.loads(Path(f"{prefix}_retrieval.json").read_text(encoding="utf-8"))}
        e2e = {r["id"]: r for r in json.loads(Path(f"{prefix}_e2e.json").read_text(encoding="utf-8"))}
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing results file ({exc.filename}). Run --mode retrieval and --mode e2e (same --out prefix) first.")
    key = f"evidence_hit@{k}"
    ids = [i for i in raw if i in e2e and key in raw[i] and key in e2e[i] and "error" not in raw[i] and "error" not in e2e[i]]
    raw_hits = {i for i in ids if raw[i][key]}
    e2e_hits = {i for i in ids if e2e[i][key]}
    print("\n" + "=" * 72)
    print(f"RAW QUESTION vs GRAPH (intent routing + query rewrite), evidence in top-{k}")
    print("=" * 72)
    print(f"Questions compared: {len(ids)}   raw hits: {len(raw_hits)}   graph hits: {len(e2e_hits)}")
    for title, group in (("REGRESSIONS (raw question found it, graph did not)", raw_hits - e2e_hits), ("IMPROVEMENTS (graph found it, raw question did not)", e2e_hits - raw_hits)):
        print(f"\n{title}: {len(group)}")
        for i in sorted(group):
            r = e2e[i]
            why = f"routed to {r.get('intent')}" if not r.get("routed_to_rag") else "query rewritten"
            print(f"  {i} [{why}] {short(r['question'], 80)}")
            if r.get("routed_to_rag"):
                print(f"        rewrite: {short(r.get('rewritten_query'), 100)}")


def make_judge(model):
    from typing import Literal, TypedDict

    class Verdict(TypedDict):
        verdict: Literal["correct", "partially_correct", "incorrect"]
        reason: str

    judge = model.with_structured_output(Verdict)

    def run(question, reference, answer):
        prompt = (
            "You are grading a chatbot answer against a reference answer.\n"
            f"Question: {question}\nReference answer: {reference}\nChatbot answer: {answer}\n\n"
            "correct = the chatbot answer contains the key facts of the reference and nothing contradictory.\n"
            "partially_correct = some key facts are right but others are missing or wrong.\n"
            "incorrect = wrong, contradictory, or says it cannot answer."
        )
        return judge.invoke(prompt)

    return run


def make_abstain_judge(model):
    from typing import Literal, TypedDict

    class Abstain(TypedDict):
        verdict: Literal["abstained", "hallucinated"]
        reason: str

    judge = model.with_structured_output(Abstain)

    def run(question, answer):
        prompt = (
            "A company handbook does NOT contain the information needed to answer the question below.\n"
            f"Question: {question}\nChatbot answer: {answer}\n\n"
            "abstained = the chatbot says the information is not available / not covered / not found in the documents "
            "(it may mention related general information as long as it does not claim to answer the specific question).\n"
            "hallucinated = the chatbot gives a specific answer, number or policy as if it were true."
        )
        return judge.invoke(prompt)

    return run


def run_e2e(dataset, chat, judge_on, sleep):
    from langchain_core.messages import HumanMessage

    judge = make_judge(chat.model) if judge_on else None
    abstain_judge = make_abstain_judge(chat.model) if judge_on else None
    rows = []
    for n, item in enumerate(dataset, 1):
        row = {"id": item["id"], "question_type": item["question_type"], "question": item["question"], "answerable": item["answerable"]}
        try:
            result = chat.app.invoke({"messages": [HumanMessage(content=item["question"])]})
            intent = (result.get("intent") or {}).get("intent")
            chunks = result.get("Retrieved_chunks") or []
            answer = result["messages"][-1].content
            row.update(
                intent=intent,
                routed_to_rag=intent == "RAG_Query",
                rewritten_query=result.get("Rag_query"),
                database_query=result.get("Database_query"),
                answer=answer,
                retrieved=[{"file": chunk_meta(c).get("source") or chunk_meta(c).get("file_path"), "text": chunk_text(c)} for c in chunks],
            )
            fallback = detect_fallback(answer)
            if item["answerable"]:
                row["response_category"] = fallback or "answered"
                row.update(analyse_chunks(item, chunks))  # no chunks (misrouted) => counted as a retrieval miss
                if judge:
                    if fallback:  # canned non-answer: no need to spend an LLM call
                        row["judge_verdict"], row["judge_reason"] = "incorrect", f"canned fallback reply ({fallback})"
                    else:
                        v = judge(item["question"], item["reference_answer"], answer)
                        row["judge_verdict"], row["judge_reason"] = v["verdict"], v["reason"]
            else:
                # Unanswerable: grounded decline (ideal) > canned fallback (safe, but blames the wording) > answered (hallucination risk)
                if fallback:
                    category = fallback
                elif abstain_judge:
                    v = abstain_judge(item["question"], answer)
                    category = "grounded_decline" if v["verdict"] == "abstained" else "answered"
                    row["judge_reason"] = v["reason"]
                else:
                    category = "grounded_decline" if DECLINE_PATTERNS.search(answer) else "answered"
                row["response_category"] = category
                row["safe"] = category in SAFE_CATEGORIES
        except Exception as exc:
            row["error"] = repr(exc)
        rows.append(row)
        print(f"  [{n:>2}/{len(dataset)}] {item['id']} intent={row.get('intent')} err={'error' in row}")
        time.sleep(sleep)
    return rows


def print_e2e_summary(rows, judged):
    ok = [r for r in rows if "error" not in r]
    print("\n" + "=" * 72)
    print("END-TO-END (question -> LangGraph app)")
    print("=" * 72)
    print(f"Completed without error: {len(ok)}/{len(rows)}")
    print(f"Intent routed to RAG_Query: {mean(r['routed_to_rag'] for r in ok):.2f}  (all 50 questions are handbook questions)")
    wrong = [r for r in ok if not r["routed_to_rag"]]
    for r in wrong[:10]:
        print(f"   misrouted {r['id']} -> {r['intent']}: {short(r['question'], 80)}")
    types = ["direct", "paraphrased", "specific", "multi-part"]
    print("\nANSWERABLE questions (a misrouted question counts as a retrieval miss and, with --judge, as incorrect)")
    print(f"{'type':<14}{'n':>3} " + " ".join(f"evid@{k:<2}" for k in KS) + f" | full@{KS[-1]}" + ("  correct  partial" if judged else ""))
    for t in types + ["ALL answerable"]:
        rs = [r for r in ok if r["answerable"] and (t == "ALL answerable" or r["question_type"] == t)]
        if not rs:
            continue
        line = f"{t:<14}{len(rs):>3} " + " ".join(f"{mean(r[f'evidence_hit@{k}'] for r in rs):6.2f} " for k in KS) + f"| {mean(r[f'evidence_full@{KS[-1]}'] for r in rs):6.2f}"
        if judged:
            js = [r for r in rs if "judge_verdict" in r]
            if js:
                line += f"  {mean(r['judge_verdict']=='correct' for r in js):7.2f} {mean(r['judge_verdict']=='partially_correct' for r in js):7.2f}"
        print(line)
    print("(evid@k = answer passage inside the first k retrieved chunks. The graph itself passes the first chat.RETRIEVAL_K chunks to the LLM.)")
    una = [r for r in ok if not r["answerable"]]
    if una:
        count = lambda cat: sum(r["response_category"] == cat for r in una)
        fallbacks = sum(r["response_category"] in ("clarification_fallback", "irrelevant_fallback", "other_non_answer") for r in una)
        print(f"\nUNANSWERABLE QUESTIONS (n={len(una)}) - the handbook has no answer, so the bot should NOT invent one")
        print(f"  grounded decline (ideal: says the info isn't in the documents) : {count('grounded_decline')}/{len(una)}")
        print(f"  canned fallback ('could not understand', irrelevant, etc.)     : {fallbacks}/{len(una)}   (safe, but says nothing useful about the handbook)")
        print(f"  answered anyway (hallucination risk)                           : {count('answered')}/{len(una)}")
        print(f"  => no-hallucination rate: {mean(r['safe'] for r in una):.2f}   ideal-decline rate: {mean(r['response_category'] == 'grounded_decline' for r in una):.2f}")
        ans_rows = [r for r in ok if r["answerable"]]
        ans_fb = sum(r["response_category"] != "answered" for r in ans_rows)
        print(f"  The same canned fallbacks also fired on {ans_fb}/{len(ans_rows)} ANSWERABLE questions.")
        print("  If that is much above zero, the fallback is a routing failure, not careful abstention: it would refuse questions the handbook can answer too.")
        if not judged:
            print("  (decline detection here is a keyword heuristic; re-run with --judge for an LLM check, and read the answers in the results file)")
    rewrites = [r for r in ok if r.get("rewritten_query")]
    if rewrites:
        print("\nSample query rewrites by the intent classifier:")
        for r in rewrites[:4]:
            print(f"  Q: {short(r['question'], 70)}\n  R: {short(r['rewritten_query'], 70)}")


# --------------------------------------------------------------------------- main

def load_dataset(path) -> list:
    """Load the eval dataset from .json or .csv (the CSV stores lists as joined strings)."""
    path = Path(path)
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    items = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            texts = [t for t in row["relevant_evidence"].split("\n---\n")] if row["relevant_evidence"] else []
            keys = row["evidence_keyphrases"].split(" | ") if row["evidence_keyphrases"] else []
            if len(texts) != len(keys):  # keyphrase contained ' | ' or evidence contained a '---' rule
                raise ValueError(f"{row['id']}: {len(texts)} evidence passages but {len(keys)} keyphrases in CSV; use the JSON file instead")
            docs = row["source_documents"].split(" | ") if row["source_documents"] else []
            items.append({
                "id": row["id"],
                "question": row["question"],
                "question_type": row["question_type"],
                "reference_answer": row["reference_answer"],
                "source_document": row["source_document"] or None,
                "source_documents": docs,
                "relevant_evidence": [{"file": None, "section": None, "keyphrase": k, "text": t} for k, t in zip(keys, texts)],
                "answerable": row["answerable"].strip().lower() == "true",
                "also_acceptable_sources": row["also_acceptable_sources"].split(" | ") if row["also_acceptable_sources"] else [],
                "notes": row["notes"],
            })
    return items

def save(rows, path_json, path_csv):
    Path(path_json).write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    flat_keys = sorted({k for r in rows for k, v in r.items() if not isinstance(v, (list, dict))})
    with open(path_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=flat_keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in flat_keys})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chat-module", required=True, help="dotted path of your chat file, e.g. mypkg.chat")
    ap.add_argument("--dataset", default=None, help="path to the dataset .json or .csv (default: clef_rag_eval_dataset.json/.csv next to this file)")
    ap.add_argument("--mode", choices=["retrieval", "intent", "e2e", "both", "all", "compare"], default="retrieval")
    ap.add_argument("--compare-k", type=int, default=5, help="compare mode: evidence-in-top-k to compare (one of %s)" % (KS,))
    ap.add_argument("--no-controls", action="store_true", help="intent mode: skip the built-in control questions")
    ap.add_argument("--types", nargs="*", help="only these question types, e.g. direct multi-part unanswerable")
    ap.add_argument("--limit", type=int, help="only the first N questions (smoke test)")
    ap.add_argument("--judge", action="store_true", help="LLM-judge answer correctness in e2e mode (extra Mistral calls)")
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between e2e questions (API rate limits)")
    ap.add_argument("--out", default="eval_results", help="output file prefix")
    args = ap.parse_args()

    here = Path(__file__).parent
    dataset_path = args.dataset or next((str(p) for p in (here / "clef_rag_eval_dataset.json", here / "clef_rag_eval_dataset.csv") if p.exists()), None)
    if not dataset_path or not Path(dataset_path).exists():
        raise SystemExit("Dataset not found. Put clef_rag_eval_dataset.json/.csv next to this file or pass --dataset PATH")
    dataset = load_dataset(dataset_path)
    if args.types:
        dataset = [d for d in dataset if d["question_type"] in args.types]
    if args.limit:
        dataset = dataset[: args.limit]
    print(f"Loaded {len(dataset)} questions")

    if args.mode == "compare":
        run_compare(args.out, args.compare_k)
        return

    chat = importlib.import_module(args.chat_module)  # will hang here if your chat file still has an unguarded input loop

    if args.mode in ("retrieval", "both", "all"):
        rows = run_retrieval(dataset, chat.vector_store, max(KS))
        print_retrieval_summary(rows)
        print_misses(rows)
        save(rows, f"{args.out}_retrieval.json", f"{args.out}_retrieval.csv")
    if args.mode in ("intent", "all"):
        print("\nRunning intent classification only (1 Mistral call per question)...")
        rows = run_intent(dataset, chat, args.sleep, controls=not args.no_controls)
        print_intent_summary(rows)
        save(rows, f"{args.out}_intent.json", f"{args.out}_intent.csv")
    if args.mode in ("e2e", "both", "all"):
        print("\nRunning end-to-end (this makes Mistral calls)...")
        rows = run_e2e(dataset, chat, args.judge, args.sleep)
        print_e2e_summary(rows, args.judge)
        save(rows, f"{args.out}_e2e.json", f"{args.out}_e2e.csv")
    print(f"\nSaved per-question results to {args.out}_*.json / .csv")


if __name__ == "__main__":
    main()