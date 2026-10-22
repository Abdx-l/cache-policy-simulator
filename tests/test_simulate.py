import unittest

from simulate import Cache, compare, svg_chart


class CacheTests(unittest.TestCase):
    def test_lru_eviction_and_expiry(self):
        cache = Cache(2, "lru", ttl=5)
        cache.access(0, "a", 1, 100, 1)
        cache.access(1, "b", 1, 100, 1)
        self.assertTrue(cache.access(2, "a", 1, 100, 1))
        cache.access(3, "c", 1, 100, 1)
        self.assertEqual(set(cache.entries), {"a", "c"})
        self.assertFalse(cache.access(5, "a", 1, 100, 1))
        self.assertEqual(cache.evictions, 1)

    def test_lfu_keeps_frequent_item(self):
        cache = Cache(2, "lfu")
        for t, key in enumerate(["a", "b", "a", "a", "c"]):
            cache.access(t, key, 1, 10, 1)
        self.assertEqual(set(cache.entries), {"a", "c"})
        self.assertEqual(cache.summary()["hits"], 2)

    def test_oversized_object_and_report(self):
        trace = [(0, "large", 3, 10, 1), (1, "large", 3, 10, 1)]
        results = compare(trace, [2])
        self.assertEqual(results[0]["misses"], 2)
        self.assertIn("<svg", svg_chart(results))

