"""A probabilistically balanced ordered map built on a skip list.

The implementation keeps a single linked structure of levels.  Each key is
stored exactly once in the bottom (level 0) list, and probabilistically
promoted to higher levels.  Search, insertion, and deletion are expected
O(log n) with a small constant factor.

Design decisions worth noting:

* The promotion probability is fixed at 0.5.  A tunable probability would be
  nice, but exposing it invites callers to pick values that break the
  expected-complexity guarantee.  The constant is documented instead.
* The maximum level is capped so a pathological random sequence cannot grow
  the level array without bound.  The cap is generous relative to realistic
  map sizes.
* We use a sentinel head node at every level.  This removes the need to
  special-case insertion and deletion at the front of the list.
* The random source is injectable.  Tests pass a deterministic generator so
  the shape of the list is reproducible; production callers get the module
  level ``random`` instance.
"""

from __future__ import annotations

import random
from typing import Any, Dict, Iterator, List, Optional, Tuple


# Fixed promotion probability.  See module docstring.
_PROMOTION_PROBABILITY = 0.5

# Hard cap on the number of levels.  With p=0.5 the expected level of a node
# is 1/(1-p) = 2, so 32 levels cover maps far larger than any realistic use.
_MAX_LEVEL = 32


class _Node:
    """A single key/value slot with forward pointers for each level."""

    __slots__ = ("key", "value", "forward")

    def __init__(self, key: Any, value: Any, level: int) -> None:
        self.key = key
        self.value = value
        # forward[i] is the next node at level i.  The list is indexed from 0.
        self.forward: List[Optional["_Node"]] = [None] * (level + 1)


class SkipListMap:
    """An ordered mapping backed by a skip list.

    Keys must be comparable with ``<`` and ``==``.  Values may be anything.
    The mapping preserves insertion order only in the sense that iteration is
    in ascending key order; it does not preserve the order in which keys were
    first inserted.
    """

    def __init__(self, random_source: Optional[random.Random] = None) -> None:
        """Create an empty map.

        Args:
            random_source: Optional ``random.Random`` instance used to decide
                promotion.  Passing a seeded instance makes the list shape
                deterministic, which is useful for tests and reproducible
                benchmarks.  When omitted, the module level ``random``
                functions are used.
        """
        self._random = random_source if random_source is not None else random
        self._level = 0
        # The head node is a sentinel; its key is never compared against a
        # real key because every search starts at the head.
        self._head = _Node(None, None, _MAX_LEVEL)
        self._size = 0

    # -- introspection -------------------------------------------------

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: Any) -> bool:
        return self._find_node(key) is not None

    def __iter__(self) -> Iterator[Any]:
        node = self._head.forward[0]
        while node is not None:
            yield node.key
            node = node.forward[0]

    # -- core operations -----------------------------------------------

    def get(self, key: Any, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if it is absent."""
        node = self._find_node(key)
        if node is None:
            return default
        return node.value

    def put(self, key: Any, value: Any) -> None:
        """Insert or replace *key* with *value*."""
        update = self._build_update(key)
        node = update[0].forward[0]
        if node is not None and node.key == key:
            node.value = value
            return

        level = self._random_level()
        new_node = _Node(key, value, level)

        if level > self._level:
            # Extend the head's forward pointers so the new level is reachable.
            for i in range(self._level + 1, level + 1):
                update[i] = self._head
            self._level = level

        for i in range(level + 1):
            new_node.forward[i] = update[i].forward[i]
            update[i].forward[i] = new_node

        self._size += 1

    def delete(self, key: Any) -> bool:
        """Remove *key*.

        Returns True if the key was present, False otherwise.
        """
        update = self._build_update(key)
        node = update[0].forward[0]
        if node is None or node.key != key:
            return False

        for i in range(self._level + 1):
            if update[i].forward[i] is not node:
                break
            update[i].forward[i] = node.forward[i]

        # Shrink the head if the top levels are now empty.
        while self._level > 0 and self._head.forward[self._level] is None:
            self._level -= 1

        self._size -= 1
        return True

    def items(self) -> Iterator[Tuple[Any, Any]]:
        """Iterate over ``(key, value)`` pairs in ascending key order."""
        node = self._head.forward[0]
        while node is not None:
            yield (node.key, node.value)
            node = node.forward[0]

    def keys(self) -> Iterator[Any]:
        """Iterate over keys in ascending order."""
        node = self._head.forward[0]
        while node is not None:
            yield node.key
            node = node.forward[0]

    def values(self) -> Iterator[Any]:
        """Iterate over values in ascending key order."""
        node = self._head.forward[0]
        while node is not None:
            yield node.value
            node = node.forward[0]

    def as_dict(self) -> Dict[Any, Any]:
        """Return a plain ``dict`` with the same contents.

        Useful for callers that want a snapshot rather than a live view.
        """
        return {k: v for k, v in self.items()}

    # -- internals -----------------------------------------------------

    def _random_level(self) -> int:
        """Return a level in ``[0, _MAX_LEVEL]``.

        The distribution is geometric with p=0.5, truncated at _MAX_LEVEL.
        """
        level = 0
        while level < _MAX_LEVEL and self._random.random() < _PROMOTION_PROBABILITY:
            level += 1
        return level

    def _find_node(self, key: Any) -> Optional[_Node]:
        """Return the node holding *key*, or None."""
        node = self._head
        for i in range(self._level, -1, -1):
            while node.forward[i] is not None and node.forward[i].key < key:
                node = node.forward[i]
        candidate = node.forward[0]
        if candidate is not None and candidate.key == key:
            return candidate
        return None

    def _build_update(self, key: Any) -> List[_Node]:
        """Return the rightmost node at each level whose forward key is >= *key*.

        The returned list has length ``_MAX_LEVEL + 1``.  Levels above the
        current top are filled with the head node so callers can index it
        uniformly when extending the list.
        """
        update: List[_Node] = [self._head] * (_MAX_LEVEL + 1)
        node = self._head
        for i in range(self._level, -1, -1):
            while node.forward[i] is not None and node.forward[i].key < key:
                node = node.forward[i]
            update[i] = node
        return update


# A small alias so callers who prefer the short name can use it.  The class
# is not a set, so the name is deliberately not ``SkipListSet``.
SkipList = SkipListMap
