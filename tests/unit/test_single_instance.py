from __future__ import annotations

import uuid

from songkey.platform.windows.single_instance import SingleInstanceGuard


def test_first_acquire_succeeds():
    name = rf"Local\SongKeyTest-{uuid.uuid4().hex}"
    guard = SingleInstanceGuard(name)
    try:
        assert guard.acquire() is True
    finally:
        guard.release()


def test_second_acquire_with_same_name_reports_already_running():
    name = rf"Local\SongKeyTest-{uuid.uuid4().hex}"
    first = SingleInstanceGuard(name)
    second = SingleInstanceGuard(name)
    try:
        assert first.acquire() is True
        assert second.acquire() is False
    finally:
        first.release()
        second.release()


def test_release_then_reacquire_succeeds():
    name = rf"Local\SongKeyTest-{uuid.uuid4().hex}"
    guard = SingleInstanceGuard(name)
    guard.acquire()
    guard.release()

    guard2 = SingleInstanceGuard(name)
    try:
        assert guard2.acquire() is True
    finally:
        guard2.release()


def test_context_manager_releases_on_exit():
    name = rf"Local\SongKeyTest-{uuid.uuid4().hex}"
    with SingleInstanceGuard(name) as guard:
        assert guard.acquire() is True

    guard2 = SingleInstanceGuard(name)
    try:
        assert guard2.acquire() is True
    finally:
        guard2.release()
