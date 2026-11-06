# skip-list-utils

A small ordered map backed by a probabilistically balanced skip list.

```python
from skip_list_utils import SkipListMap

m = SkipListMap()
m.put("b", 2)
m.put("a", 1)
m.put("c", 3)

assert m.get("a") == 1
assert list(m) == ["a", "b", "c"]
assert list(m.items()) == [("a", 1), ("b", 2), ("c", 3)]
assert m.delete("b") is True
assert m.delete("b") is False
assert m.as_dict() == {"a": 1, "c": 3}
```

## Why this exists

A balanced binary search tree gives worst-case O(log n) lookups, but the
rebalancing logic is fiddly to get right and easy to get subtly wrong.  A skip
list gives the same expected complexity with a much simpler implementation:
no rotations, no colour bits, just a linked list with a few extra forward
pointers.  The trade-off is that the bound is probabilistic rather than
worst-case, and the constant factor is a little larger because each search
walks several levels.

The promotion probability is fixed at 0.5.  That is the value most analyses
assume, and exposing it as a parameter would let callers pick a number that
quietly breaks the expected-complexity guarantee.  The maximum level is capped
at 32 so a long run of promotions cannot grow the level array without bound.

## API

`SkipListMap` is the exported class.  `SkipList` is an alias for it, kept
because the short name reads better at call sites that already know what a
skip list is.

| Method | Behaviour |
| --- | --- |
| `SkipListMap(random_source=None)` | Create an empty map.  Pass a seeded `random.Random` to make the list shape reproducible. |
| `put(key, value)` | Insert or replace. |
| `get(key, default=None)` | Return the value, or `default` if absent. |
| `delete(key)` | Remove `key`; return `True` if it was present. |
| `__contains__(key)` | Membership test. |
| `__len__()` | Number of entries. |
| `__iter__()` | Iterate keys in ascending order. |
| `keys()`, `values()`, `items()` | Iterators in ascending key order. |
| `as_dict()` | Snapshot as a plain `dict`. |

## Edge cases

Keys are compared with `<` and `==`, not hashed.  That means tuples and other
comparable objects work as keys, but it also means two keys that compare equal
are treated as the same entry even if they are not identical objects.  If your
keys do not define a total order, the map will not behave as you expect.

`delete` returns a boolean rather than raising on a missing key, which is the
convention most callers expect from a map.  The head and tail of the list are
handled by a sentinel node, so deleting the first or last key is not a special
case for callers.
