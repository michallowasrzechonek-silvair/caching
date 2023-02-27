from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Set, Tuple
from unittest.mock import MagicMock

import pytest


def sorted_pairs(L: Iterable[Tuple[str, Any]]) -> Iterable[Tuple[str, Any]]:
    return sorted(L, key=lambda x: x[0])


@dataclass
class Node:
    children: Dict[Tuple[str, Any], "Node"] = field(default_factory=dict)
    callbacks: Set[Callable] = field(default_factory=set)


class Signal:
    """
    Signal is a publish-subscribe broker, allowing subscribers to listen to
    events and publishers to emit these events without worrying who listens to
    what, while efficiently invoking only subscribers that are interested in
    the published event.

    Subscribers provide a callback and a filter. Event matches the filter if
    (and only if):
        - event contains all fields specified by the filter
        - for these fields, values in the event are equal to ones in the filter
    which translates to the following predicate:

        def match(event, filter):
            if filter.keys() - event.keys():
                return False

            for key, value in filter.keys():
                if event[key] != value:
                    return False

            return True

    To avoid evaluating this predicate for all registered subscribers, we
    construct a N-tree, where children are indexed by `(field name, field
    value)` pair. To add subscription, we sort filter items by `field name` and
    insert each item as a node into the tree.

    For example, adding subscription with filter `f={a: 1, c:3, b: 2}` and
    callback `cb=F` to an empty `Signal` results in a following tree:

        <root>:
            (a, 1):
                (b, 2):
                    (c, 3): {F}

    adding another subscription with `f={a: 1, b: 3}` and `cb=G` to the same
    `Signal` results in:

        <root>:
            (a, 1):
                (b, 2):
                    (c, 3): {F}
                (b, 3): {G}

    and another one with `f={b: 4, d: 5}` and `cb=H`:

        <root>:
            (a, 1):
                (b, 2):
                    (c, 3): {F}
                (b, 3): {G}
            (b, 4):
                (d, 5): {H}

    and another one with `f={a: 1, b: 2} and `cb=I`:

        <root>:
            (a, 1):
                (b, 2): {I}
                    (c, 3): {F}
                (b, 3): {G}
            (b, 4):
                (d, 5): {H}


    When publishing, we again sort event items by field name, set the current
    node `N` to `<root>`, and then for each item `i`:

     - unconditionally call all callbacks attached to the `N`
     - if `N` contains a child matching `i`, recurse from `N` set that child
       and remaining event fields
     - otherwise, stay at `N` and proceed to the next item

    Note that a published event may match more than one subscriber's filter,
    whether they live on the same path through the tree, or not. That's why we
    call the lookup recursively and *do not* return from the current branch -
    instead we continue as usual with the current node, until each recursion
    branch exhausts event fields.
    """
    def __init__(self):
        self.root = Node()

    def publish(self, event: Dict[str, Any]):
        def _publish(node, match: Iterable[Tuple[str, Any]], event: Dict[str, Any]):
            for callback in node.callbacks:
                callback(event)

            while match:
                (key, value), *match = match
                if next := node.children.get((key, value)):
                    _publish(next, match, event)

        _publish(self.root, sorted_pairs(event.items()), event)

    def subscribe(self, filter: Dict[str, Any], callback: Callable):
        node = self.root

        for key, value in sorted_pairs(filter.items()):
            node = node.children.setdefault((key, value), Node())

        node.callbacks.add(callback)

        def unsubscribe():
            node.callbacks.remove(callback)

        return unsubscribe


@pytest.fixture
def signal():
    return Signal()


@pytest.fixture
def foo():
    return MagicMock()


@pytest.fixture
def bar():
    return MagicMock()


def test_exact(signal, foo, bar):
    signal.subscribe(dict(a=1, b=2), foo)
    signal.publish(dict(a=1, b=2))
    assert foo.call_count == 1


def test_exact_mismatch(signal, foo):
    signal.subscribe(dict(a=1), foo)
    signal.publish(dict(a=2))
    assert foo.call_count == 0


def test_prefix(signal, foo):
    signal.subscribe(dict(a=1, b=2), foo)
    signal.publish(dict(a=1, b=2, c=3))
    assert foo.call_count == 1


def test_prefix_mismatch(signal, foo):
    signal.subscribe(dict(a=1, b=2), foo)
    signal.publish(dict(a=1, b=3))
    assert foo.call_count == 0


def test_skip(signal, foo):
    signal.subscribe(dict(b=2), foo)
    signal.publish(dict(a=1, b=2))
    assert foo.call_count == 1


def test_skip_mismatch(signal, foo):
    signal.subscribe(dict(b=2), foo)
    signal.publish(dict(a=1, b=3))
    assert foo.call_count == 0


def test_overlap(signal, foo, bar):
    signal.subscribe(dict(a=1, b=2), foo)
    signal.subscribe(dict(a=1), bar)

    signal.publish(dict(a=1, b=2, c=3))

    assert foo.call_count == 1
    assert bar.call_count == 1


def test_overlap_prefix(signal, foo, bar):
    signal.subscribe(dict(a=1, b=2), foo)
    signal.subscribe(dict(b=2), bar)

    signal.publish(dict(a=1, b=2, c=3))

    assert foo.call_count == 1
    assert bar.call_count == 1


def test_overlap_skip(signal, foo, bar):
    signal.subscribe(dict(a=1, b=2), foo)
    signal.subscribe(dict(b=3), bar)

    signal.publish(dict(a=1, b=3, c=3))

    assert foo.call_count == 0
    assert bar.call_count == 1
