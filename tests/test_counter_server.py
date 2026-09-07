import json
import threading
import urllib.error
import urllib.request

import pytest

from counter_server import make_handler
from counter_store import CounterStore
from http.server import ThreadingHTTPServer


@pytest.fixture
def server(tmp_path):
    store = CounterStore(str(tmp_path / "visits.json"))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store))
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


def test_first_visit_returns_count_one(server):
    status, body = _get(f"{server}/api/visits")
    assert status == 200
    assert body == {"count": 1}


def test_repeated_visits_increment(server):
    _get(f"{server}/api/visits")
    _get(f"{server}/api/visits")
    status, body = _get(f"{server}/api/visits")
    assert status == 200
    assert body == {"count": 3}


def test_unknown_path_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(f"{server}/nope")
    assert excinfo.value.code == 404


def test_root_path_is_404_not_the_counter(server):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _get(f"{server}/")
    assert excinfo.value.code == 404


def test_post_is_405(server):
    req = urllib.request.Request(f"{server}/api/visits", method="POST", data=b"")
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(req, timeout=5)
    assert excinfo.value.code == 405


def test_response_is_json_content_type(server):
    with urllib.request.urlopen(f"{server}/api/visits", timeout=5) as resp:
        assert resp.headers.get("Content-Type") == "application/json"


def test_response_is_not_cached(server):
    with urllib.request.urlopen(f"{server}/api/visits", timeout=5) as resp:
        assert resp.headers.get("Cache-Control") == "no-store"


def test_concurrent_requests_each_get_a_unique_count(server):
    results = []
    lock = threading.Lock()

    def worker():
        _, body = _get(f"{server}/api/visits")
        with lock:
            results.append(body["count"])

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == list(range(1, 21))
