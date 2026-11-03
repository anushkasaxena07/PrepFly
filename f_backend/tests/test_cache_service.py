"""
Unit and Integration Tests for PrepFly Caching Engine.
Validates:
- L1 InMemory LRU Cache (get, set, delete, TTL expiration, max size eviction)
- Multi-tier Cache Manager with dogpile / stampede protection
- Function & Route caching decorators (@cached, @cache_invalidate)
- AI LLM prompt-response caching (SHA-256)
- HTTP ETag generation & 304 conditional responses
"""

import time
import unittest
import threading
from flask import Flask

from services.cache_service import (
    InMemoryLRUCache,
    TieredCacheManager,
    cached,
    cache_invalidate,
    get_cached_ai_response,
    save_cached_ai_response,
    generate_etag,
    conditional_etag_response,
    cache_manager,
)


class TestCacheService(unittest.TestCase):

    def setUp(self):
        # Fresh in-memory cache for each test
        self.cache = InMemoryLRUCache(max_size=5, default_ttl=2)
        cache_manager.clear()

    def test_basic_get_set_delete(self):
        """Should store, retrieve, and delete items from in-memory cache."""
        self.assertIsNone(self.cache.get("key1"))
        self.cache.set("key1", {"data": "prepfly"}, ttl=10)
        self.assertEqual(self.cache.get("key1"), {"data": "prepfly"})
        
        # Delete
        self.assertTrue(self.cache.delete("key1"))
        self.assertIsNone(self.cache.get("key1"))
        self.assertFalse(self.cache.delete("non_existent"))

    def test_ttl_expiration(self):
        """Should expire items after their TTL passes."""
        self.cache.set("short_key", "temporary_val", ttl=1)
        self.assertEqual(self.cache.get("short_key"), "temporary_val")

        time.sleep(1.1)
        self.assertIsNone(self.cache.get("short_key"))

    def test_lru_eviction(self):
        """Should evict the least recently used item when max_size is reached."""
        small_cache = InMemoryLRUCache(max_size=3, default_ttl=60)
        small_cache.set("k1", 1)
        small_cache.set("k2", 2)
        small_cache.set("k3", 3)

        # Access k1 to make it most recently used
        _ = small_cache.get("k1")

        # Insert k4, which should evict k2 (oldest unaccessed item)
        small_cache.set("k4", 4)

        self.assertEqual(small_cache.get("k1"), 1)
        self.assertIsNone(small_cache.get("k2"))
        self.assertEqual(small_cache.get("k3"), 3)
        self.assertEqual(small_cache.get("k4"), 4)

    def test_delete_prefix(self):
        """Should delete all keys matching a given prefix."""
        self.cache.set("user:1:profile", "alice")
        self.cache.set("user:1:settings", "dark_mode")
        self.cache.set("user:2:profile", "bob")

        deleted_count = self.cache.delete_prefix("user:1:")
        self.assertEqual(deleted_count, 2)
        self.assertIsNone(self.cache.get("user:1:profile"))
        self.assertIsNone(self.cache.get("user:1:settings"))
        self.assertEqual(self.cache.get("user:2:profile"), "bob")

    def test_cache_telemetry_stats(self):
        """Should accurately record hits, misses, writes, and hit ratio percentage."""
        c = InMemoryLRUCache(max_size=10, default_ttl=60)
        c.set("item", "value")
        _ = c.get("item")  # hit
        _ = c.get("item")  # hit
        _ = c.get("missing")  # miss

        stats = c.stats()
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["writes"], 1)
        self.assertAlmostEqual(stats["hit_ratio_percent"], 66.67, places=1)

    def test_stampede_protection_single_flight(self):
        """Multiple concurrent requests for the same key should only execute fetch_fn once."""
        manager = TieredCacheManager(l1_max_size=10, l1_default_ttl=10)
        compute_counter = [0]
        counter_lock = threading.Lock()

        def expensive_fetch():
            time.sleep(0.05)
            with counter_lock:
                compute_counter[0] += 1
            return "computed_result"

        threads = []
        results = [None] * 5

        def worker(idx):
            results[idx] = manager.get_or_set("heavy_metric", expensive_fetch, ttl=10)

        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should receive the computed result
        for res in results:
            self.assertEqual(res, "computed_result")

        # The expensive fetch function should have run only once
        self.assertEqual(compute_counter[0], 1)

    def test_cached_decorator_function(self):
        """@cached decorator should cache function returns based on arguments."""
        calls = [0]

        @cached(ttl=60, key_prefix="calc_test")
        def add_numbers(a, b):
            calls[0] += 1
            return a + b

        self.assertEqual(add_numbers(2, 3), 5)
        self.assertEqual(calls[0], 1)

        # Second call with same arguments should hit cache
        self.assertEqual(add_numbers(2, 3), 5)
        self.assertEqual(calls[0], 1)

        # Call with different arguments should compute fresh
        self.assertEqual(add_numbers(4, 5), 9)
        self.assertEqual(calls[0], 2)

    def test_cache_invalidate_decorator(self):
        """@cache_invalidate should clear cached prefixes on mutation execution."""
        cache_manager.set("org_data:org_123", {"name": "College A"})
        self.assertIsNotNone(cache_manager.get("org_data:org_123"))

        @cache_invalidate(prefixes=["org_data:org_123"])
        def update_org():
            return True

        update_org()
        self.assertIsNone(cache_manager.get("org_data:org_123"))

    def test_ai_response_caching(self):
        """AI prompt-response caching should store and return identical responses."""
        prompt = "How would you design a distributed caching layer with Redis?"
        model = "gemini-2.5-flash"
        mock_response = {
            "title": "Distributed Cache Architecture",
            "components": ["L1 In-Memory", "L2 Redis Cluster", "Cache Invalidation Bus"]
        }

        self.assertIsNone(get_cached_ai_response(prompt, model_name=model))
        save_cached_ai_response(prompt, mock_response, model_name=model, ttl=3600)

        cached_output = get_cached_ai_response(prompt, model_name=model)
        self.assertIsNotNone(cached_output)
        self.assertEqual(cached_output["title"], "Distributed Cache Architecture")

    def test_etag_and_304_conditional_response(self):
        """Should generate RFC-compliant ETag and return HTTP 304 when client sends matching If-None-Match."""
        app = Flask(__name__)

        test_data = {"questions": [{"id": 1, "title": "LRU Cache"}]}
        etag = generate_etag(test_data)
        self.assertTrue(etag.startswith('"') and etag.endswith('"'))

        # Request 1: No If-None-Match -> Expect HTTP 200 with ETag header
        with app.test_request_context("/api/questions"):
            resp = conditional_etag_response(test_data, status_code=200, max_age=60)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers.get("ETag"), etag)
            self.assertIn("max-age=60", resp.headers.get("Cache-Control"))
            self.assertEqual(resp.headers.get("X-Cache"), "MISS-ETAG")

        # Request 2: With matching If-None-Match -> Expect HTTP 304 Not Modified
        with app.test_request_context("/api/questions", headers={"If-None-Match": etag}):
            resp_conditional = conditional_etag_response(test_data, status_code=200, max_age=60)
            self.assertEqual(resp_conditional.status_code, 304)
            self.assertEqual(resp_conditional.headers.get("ETag"), etag)
            self.assertEqual(resp_conditional.headers.get("X-Cache"), "HIT-ETAG")

    def test_cache_stats_and_clear_endpoints(self):
        """Should verify /api/cache/stats returns telemetry and /api/cache/clear flushes keys."""
        from app import app
        client = app.test_client()

        cache_manager.set("test_key_abc", "value123", ttl=60)

        # GET /api/cache/stats
        stats_res = client.get("/api/cache/stats")
        self.assertEqual(stats_res.status_code, 200)
        data = stats_res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("l1_memory", data)
        self.assertIn("overall_hit_ratio_percent", data)

        # POST /api/cache/clear with prefix
        clear_prefix_res = client.post("/api/cache/clear", json={"prefix": "test_key_"})
        self.assertEqual(clear_prefix_res.status_code, 200)
        self.assertIsNone(cache_manager.get("test_key_abc"))

        # POST /api/cache/clear full flush
        cache_manager.set("k_full_flush", 100)
        clear_all_res = client.post("/api/cache/clear", json={})
        self.assertEqual(clear_all_res.status_code, 200)
        self.assertIsNone(cache_manager.get("k_full_flush"))


if __name__ == "__main__":
    unittest.main()
