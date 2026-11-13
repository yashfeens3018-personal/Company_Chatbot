"""
Concurrency tests for the chat router. No LLM, no database, no Chroma: the real graph is
replaced by a fake one that sleeps briefly (this WIDENS the race window so bugs show up
every time instead of once in a blue moon).

Put this file at  tests/test_chat_concurrency.py  (project root) and run from the project root:

    uv run pytest tests/test_chat_concurrency.py -v

Race bugs are probabilistic, so also run it many times:

    for i in $(seq 1 20); do uv run pytest tests/test_chat_concurrency.py -q || break; done
"""
import importlib
import sys
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage

ROUTER_MODULE = "company_project.api.chat"


class FakeGraph:
    """Stands in for the compiled LangGraph app."""

    def __init__(self, delay=0.05):
        self.delay = delay
        self.calls = []              # (user_email, [human messages it was given]) per call
        self.in_flight = 0
        self.max_in_flight = 0
        self.fail_on = set()
        self._lock = threading.Lock()

    def invoke(self, state):
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            humans = [m.content for m in state["messages"] if isinstance(m, HumanMessage)]
            self.calls.append((state["user"]["email"], humans))
        try:
            time.sleep(self.delay)
            last = state["messages"][-1].content
            if last in self.fail_on:
                raise RuntimeError("boom")
            reply = AIMessage(content=f"echo[{state['user']['email']}] {last}")
            return {"messages": list(state["messages"]) + [reply]}
        finally:
            with self._lock:
                self.in_flight -= 1


@pytest.fixture
def api(monkeypatch):
    """Import a FRESH copy of the router (fresh state) wired to a FakeGraph."""
    graph = FakeGraph()
    stubs = {
        "company_project.AI_Chat.chat": types.SimpleNamespace(app=graph),
        "company_project.AI_Chat.cache": types.SimpleNamespace(purge_stale=lambda: None),
        "company_project.auth.security": types.SimpleNamespace(get_user=lambda: None),
    }
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)
    sys.modules.pop(ROUTER_MODULE, None)
    module = importlib.import_module(ROUTER_MODULE)
    yield module, graph
    sys.modules.pop(ROUTER_MODULE, None)


def make_user(tag):
    return {"email": f"{tag}@example.com", "role": "Employee"}


def send(module, user, text, conversation_id):
    request = module.ChatRequest(message=text, conversation_id=conversation_id)
    return module.chat(request, user).answer   # called the way FastAPI's threadpool calls it


def burst(fn, jobs, workers=20):
    """Run fn(*job) for every job at (nearly) the same time. Exceptions are re-raised."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda job: fn(*job), jobs))


def test_same_conversation_loses_no_messages(api):
    """10 simultaneous messages to ONE conversation: all must end up in its history."""
    module, graph = api
    module.MAX_HISTORY = 1000
    user = make_user("a")
    texts = [f"m{i}" for i in range(10)]

    burst(lambda t: send(module, user, t, "conv-1"), [(t,) for t in texts])
    send(module, user, "final", "conv-1")

    _, history_seen_by_last_call = graph.calls[-1]
    assert sorted(history_seen_by_last_call) == sorted(texts + ["final"])


def test_users_never_see_each_others_messages(api):
    """Two users, SAME conversation_id string, interleaved: histories must stay separate."""
    module, graph = api
    module.MAX_HISTORY = 1000
    jobs = [(u, f"{u}-{i}") for i in range(15) for u in ("a", "b")]

    results = burst(lambda u, t: (u, t, send(module, make_user(u), t, "shared")), jobs)

    for u, text, answer in results:
        assert answer == f"echo[{u}@example.com] {text}"          # each caller got their own answer
    for email, humans in graph.calls:
        tag = email.split("@")[0]
        assert all(h.startswith(tag + "-") for h in humans), (email, humans)   # no foreign messages


def test_conversation_memory_is_bounded(api):
    module, _ = api
    if not hasattr(module, "store"):
        pytest.skip("this router version has no bounded conversation store")
    module.MAX_CONVERSATIONS = 20
    user = make_user("a")

    burst(lambda i: send(module, user, "hi", f"c{i}"), [(i,) for i in range(100)])

    assert len(module.store._items) <= 20


def test_graph_runs_are_capped(api):
    """15 users at once, cap of 3: never more than 3 graph runs in flight."""
    module, graph = api
    module._graph_slots = threading.BoundedSemaphore(3)
    user = make_user("a")

    burst(lambda i: send(module, user, "hi", f"c{i}"), [(i,) for i in range(15)])

    assert graph.max_in_flight <= 3, f"saw {graph.max_in_flight} graph runs at once"


def test_failed_turn_does_not_poison_or_deadlock_the_conversation(api):
    module, graph = api
    module.CONVERSATION_LOCK_WAIT = 2   # a leaked lock would make the last call fail fast, not hang
    user = make_user("a")

    send(module, user, "first", "c1")
    graph.fail_on = {"boom"}
    with pytest.raises(HTTPException) as err:
        send(module, user, "boom", "c1")
    assert err.value.status_code == 502

    graph.fail_on = set()
    send(module, user, "after", "c1")
    assert graph.calls[-1][1] == ["first", "after"]    # the failed message was not saved


def test_second_message_gets_409_if_conversation_stays_busy(api):
    module, _ = api
    if not hasattr(module, "store"):
        pytest.skip("this router version has no per-conversation lock")
    module.CONVERSATION_LOCK_WAIT = 0.1
    user = make_user("a")

    conv = module.store.get_or_create((user["email"], "c1"))
    with conv.lock:                                    # pretend an earlier message is still running
        with pytest.raises(HTTPException) as err:
            send(module, user, "hello", "c1")
    assert err.value.status_code == 409