"""Provider outage pause for durable runs; fakes only, never a paid provider."""

import json
import time

import httpx
from test_style_runs import ScriptedProvider, database, owner, pump, request  # noqa: F401

from novelai_api.db import Database
from novelai_api.generations import GenerationManager, ResultCache
from novelai_api.lane_health import LaneHealth
from novelai_api.mcp_images import NovelAiMcpProvider
from novelai_api.style_experiments import StyleExperimentService


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


def test_backoff_doubles_caps_and_success_resets() -> None:
    clock = Clock()
    health = LaneHealth("novelai", clock=clock, base_delay=10, max_delay=35)
    assert health.ready() and health.paused_until() is None
    health.report("invalid_result")  # Not an outage signal.
    assert health.paused_until() is None
    for expected in (10, 20, 35, 35):
        health.report("provider_unavailable")
        assert health.paused_until() == clock.now + expected
    assert not health.ready()
    health.report(None)
    assert health.ready() and health.paused_until() is None


def test_probe_decides_resume_and_lane_without_probe_goes_half_open() -> None:
    clock = Clock()
    answers = [False, True]
    health = LaneHealth("novelai", lambda: answers.pop(0), clock=clock, base_delay=10)
    health.report("provider_rate_limited")
    assert not health.ready()  # Still cooling down: no probe yet.
    assert answers == [False, True]
    clock.now += 10
    assert not health.ready()  # Probe failed: backoff doubles.
    assert health.paused_until() == clock.now + 20
    clock.now += 20
    assert health.ready() and answers == []
    assert health.paused_until() is None

    gpt = LaneHealth("gpt", clock=clock, base_delay=10)
    gpt.report("provider_unavailable")
    assert not gpt.ready()
    clock.now += 10
    assert gpt.ready() and gpt.paused_until() is None


def test_outage_pauses_claims_without_consuming_items(database: Database) -> None:  # noqa: F811
    user = owner(database)
    provider = ScriptedProvider(["provider_unavailable"])
    manager = GenerationManager(database, provider, cache=ResultCache())
    clock = Clock()
    probes: list[bool] = [False, True]
    manager.health["novelai"] = LaneHealth(
        "novelai", lambda: probes.pop(0), clock=clock, base_delay=15,
    )
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, request(seed=9))
        assert run.total == "3"
        deadline = time.monotonic() + 3
        while service.store.get(user, run.id).processed_count != "1":
            assert time.monotonic() < deadline
            service.tick()
            time.sleep(0.005)
        for _ in range(20):
            service.tick()
        paused = service.store.get(user, run.id)
        # The failed group stays failed (no retry) and no further item is claimed.
        assert (paused.status, paused.failed_count, paused.next_ordinal) == ("running", "1", "2")
        assert paused.provider_paused_until == int(clock.now + 15)
        assert service.store.queue(user)[0].provider_paused_until == int(clock.now + 15)
        assert len(provider.calls) == 1

        clock.now += 15
        service.tick()  # Probe fails: still paused, still nothing claimed.
        assert service.store.get(user, run.id).provider_paused_until == int(clock.now + 30)
        assert len(provider.calls) == 1

        clock.now += 30
        done = pump(service, user, run.id)
    finally:
        service.stop()
        manager.stop()
    assert (done.status, done.succeeded_count, done.failed_count) == ("completed", "2", "1")
    assert done.provider_paused_until is None
    assert [call.experiment.ordinal for call in provider.calls] == ["1", "2", "3"]


def test_non_outage_failures_keep_advancing(database: Database) -> None:  # noqa: F811
    user = owner(database)
    provider = ScriptedProvider(["provider_error", "invalid_result"])
    manager = GenerationManager(database, provider, cache=ResultCache())
    service = StyleExperimentService(database, manager)
    manager.start()
    try:
        run = service.store.create(user, request(seed=3))
        done = pump(service, user, run.id)
    finally:
        service.stop()
        manager.stop()
    assert (done.failed_count, done.succeeded_count) == ("2", "1")
    assert manager.lane_paused_until("novelai") is None


def test_mcp_probe_sends_only_initialize() -> None:
    methods: list[str] = []

    def handler(status: int):
        def respond(http_request: httpx.Request) -> httpx.Response:
            methods.append(json.loads(http_request.content)["method"])
            assert http_request.headers["Authorization"] == "Bearer sentinel"
            return httpx.Response(status, json={"jsonrpc": "2.0", "id": 1, "result": {}})
        return respond

    def refuse(http_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("down", request=http_request)

    url = "https://mcp.invalid/mcp"
    assert NovelAiMcpProvider(url, "sentinel", transport=httpx.MockTransport(handler(200))).probe()
    assert not NovelAiMcpProvider(
        url, "sentinel", transport=httpx.MockTransport(handler(502)),
    ).probe()
    assert not NovelAiMcpProvider(url, "sentinel", transport=httpx.MockTransport(refuse)).probe()
    assert methods == ["initialize", "initialize"]
