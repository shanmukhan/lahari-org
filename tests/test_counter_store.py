import json
import os
import threading

import pytest

from counter_store import CounterStore


def test_get_on_missing_file_is_zero(tmp_path):
    store = CounterStore(str(tmp_path / "visits.json"))
    assert store.get() == 0


def test_increment_and_get_starts_at_one(tmp_path):
    store = CounterStore(str(tmp_path / "visits.json"))
    assert store.increment_and_get() == 1


def test_increment_and_get_persists_across_instances(tmp_path):
    path = str(tmp_path / "visits.json")
    CounterStore(path).increment_and_get()
    CounterStore(path).increment_and_get()
    assert CounterStore(path).increment_and_get() == 3


def test_get_does_not_mutate_the_counter(tmp_path):
    store = CounterStore(str(tmp_path / "visits.json"))
    store.increment_and_get()
    store.get()
    store.get()
    assert store.increment_and_get() == 2


def test_creates_parent_directory_if_missing(tmp_path):
    path = str(tmp_path / "nested" / "dir" / "visits.json")
    store = CounterStore(path)
    assert store.increment_and_get() == 1
    assert os.path.isfile(path)


def test_file_contains_expected_json_shape(tmp_path):
    path = tmp_path / "visits.json"
    CounterStore(str(path)).increment_and_get()
    with open(path) as f:
        data = json.load(f)
    assert data == {"count": 1}


def test_corrupt_file_is_treated_as_zero(tmp_path):
    path = tmp_path / "visits.json"
    path.write_text("not valid json{{{")
    store = CounterStore(str(path))
    assert store.get() == 0
    assert store.increment_and_get() == 1


def test_missing_count_key_is_treated_as_zero(tmp_path):
    path = tmp_path / "visits.json"
    path.write_text(json.dumps({"unrelated": True}))
    store = CounterStore(str(path))
    assert store.get() == 0


def test_no_stray_temp_files_left_behind(tmp_path):
    store = CounterStore(str(tmp_path / "visits.json"))
    store.increment_and_get()
    store.increment_and_get()
    remaining = {p.name for p in tmp_path.iterdir()}
    assert remaining == {"visits.json", "visits.json.lock"}


def test_concurrent_increments_are_not_lost(tmp_path):
    path = str(tmp_path / "visits.json")
    threads_n = 8
    increments_per_thread = 25

    def worker():
        store = CounterStore(path)
        for _ in range(increments_per_thread):
            store.increment_and_get()

    threads = [threading.Thread(target=worker) for _ in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert CounterStore(path).get() == threads_n * increments_per_thread


def test_default_directory_when_path_has_no_dirname(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    store = CounterStore("visits.json")
    assert store.increment_and_get() == 1
    assert (tmp_path / "visits.json").is_file()
