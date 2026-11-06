"""Tests for skip_list_utils.core.

All tests use a seeded random source so the shape of the skip list is
reproducible.  Nothing here depends on wall-clock time or on a particular
Python build.
"""

import random
import unittest

from skip_list_utils import SkipList, SkipListMap


class TestSkipListMap(unittest.TestCase):
    def _make(self) -> SkipListMap:
        # Seed 1234 is arbitrary but fixed; any seed would do as long as the
        # tests do not depend on a specific promotion pattern.
        return SkipListMap(random_source=random.Random(1234))

    def test_empty_map(self) -> None:
        m = self._make()
        self.assertEqual(len(m), 0)
        self.assertNotIn("a", m)
        self.assertIsNone(m.get("a"))
        self.assertEqual(m.get("a", "fallback"), "fallback")
        self.assertEqual(list(m), [])
        self.assertEqual(list(m.items()), [])
        self.assertEqual(m.as_dict(), {})

    def test_single_insert_and_get(self) -> None:
        m = self._make()
        m.put("a", 1)
        self.assertEqual(len(m), 1)
        self.assertIn("a", m)
        self.assertEqual(m.get("a"), 1)
        self.assertEqual(m.get("b"), None)

    def test_replace_existing_key(self) -> None:
        m = self._make()
        m.put("a", 1)
        m.put("a", 2)
        self.assertEqual(len(m), 1)
        self.assertEqual(m.get("a"), 2)

    def test_ordering_is_ascending(self) -> None:
        m = self._make()
        for k in [5, 1, 4, 2, 3]:
            m.put(k, k * 10)
        self.assertEqual(list(m), [1, 2, 3, 4, 5])
        self.assertEqual(list(m.items()), [(1, 10), (2, 20), (3, 30), (4, 40), (5, 50)])
        self.assertEqual(list(m.values()), [10, 20, 30, 40, 50])

    def test_delete_present_and_absent(self) -> None:
        m = self._make()
        for k in [1, 2, 3]:
            m.put(k, k)
        self.assertTrue(m.delete(2))
        self.assertFalse(m.delete(2))
        self.assertEqual(list(m), [1, 3])
        self.assertEqual(len(m), 2)

    def test_delete_head_key(self) -> None:
        m = self._make()
        for k in [1, 2, 3]:
            m.put(k, k)
        self.assertTrue(m.delete(1))
        self.assertEqual(list(m), [2, 3])

    def test_delete_tail_key(self) -> None:
        m = self._make()
        for k in [1, 2, 3]:
            m.put(k, k)
        self.assertTrue(m.delete(3))
        self.assertEqual(list(m), [1, 2])

    def test_delete_only_key(self) -> None:
        m = self._make()
        m.put("only", 1)
        self.assertTrue(m.delete("only"))
        self.assertEqual(len(m), 0)
        self.assertEqual(list(m), [])

    def test_many_keys(self) -> None:
        m = self._make()
        keys = list(range(200))
        # Insert in a shuffled order so the promotion pattern is exercised.
        shuffled = keys[:]
        random.Random(99).shuffle(shuffled)
        for k in shuffled:
            m.put(k, k * k)
        self.assertEqual(len(m), 200)
        self.assertEqual(list(m), keys)
        for k in keys:
            self.assertEqual(m.get(k), k * k)

    def test_duplicate_inserts_do_not_change_size(self) -> None:
        m = self._make()
        for _ in range(5):
            m.put("x", 1)
        self.assertEqual(len(m), 1)

    def test_as_dict_snapshot_is_independent(self) -> None:
        m = self._make()
        m.put("a", 1)
        snapshot = m.as_dict()
        m.put("b", 2)
        self.assertEqual(snapshot, {"a": 1})
        self.assertEqual(m.as_dict(), {"a": 1, "b": 2})

    def test_skip_list_alias(self) -> None:
        self.assertIs(SkipList, SkipListMap)
        m = SkipList(random_source=random.Random(7))
        m.put("k", "v")
        self.assertEqual(m.get("k"), "v")

    def test_keys_are_compared_not_hashed(self) -> None:
        # Tuples are comparable with < and ==, so they work as keys even
        # though they are not hashable in the sense of a dict key.
        m = self._make()
        m.put((2, "b"), 2)
        m.put((1, "a"), 1)
        m.put((2, "a"), 3)
        self.assertEqual(list(m), [(1, "a"), (2, "a"), (2, "b")])
        self.assertEqual(m.get((2, "a")), 3)


if __name__ == "__main__":
    unittest.main()
