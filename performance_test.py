#!/usr/bin/env python3
"""
Performance test for module linting improvements.
"""

import time

from nf_core.modules.lint.meta_yml_updater import get_biotools_response_cached, get_cached_edam_formats


def test_edam_caching_performance():
    """Test EDAM caching performance improvement"""
    print("🔬 Testing EDAM Caching Performance")
    print("-" * 40)

    # Clear any existing cache by accessing the global
    import nf_core.modules.lint.meta_yml_updater as updater_module

    updater_module._edam_cache = None

    # Test multiple sequential calls (simulating linting multiple modules)
    times = []

    for i in range(5):
        start = time.time()
        edam_data = get_cached_edam_formats()
        end = time.time()
        duration = end - start
        times.append(duration)

        print(f"Call {i + 1}: {duration:.3f}s ({'LOADED' if i == 0 else 'CACHED'}) - {len(edam_data)} formats")

    # Calculate improvement
    first_call = times[0]
    avg_cached = sum(times[1:]) / len(times[1:]) if len(times) > 1 else 0
    speedup = first_call / avg_cached if avg_cached > 0 else float("inf")

    print("\\n📈 Performance Results:")
    print(f"   First call (network): {first_call:.3f}s")
    print(f"   Cached calls avg:     {avg_cached:.6f}s")
    print(f"   Speedup factor:       {speedup:.0f}x faster")
    print(f"   Total time saved:     {first_call * 4 - sum(times):.3f}s (for 5 modules)")

    return speedup


def test_biotools_caching_performance():
    """Test bio.tools caching performance"""
    print("\\n🔬 Testing Bio.tools Caching Performance")
    print("-" * 40)

    # Clear cache
    get_biotools_response_cached.cache_clear()

    test_tools = ["samtools", "bwa", "fastqc", "samtools", "bwa"]  # Some duplicates
    times = []

    for i, tool in enumerate(test_tools):
        start = time.time()

        # Mock the actual bio.tools call to avoid real network requests
        from unittest.mock import patch

        with patch("nf_core.modules.lint.meta_yml_updater.get_biotools_response") as mock:
            mock.return_value = {"list": [{"name": tool, "biotoolsCURIE": f"biotools:{tool}"}]}
            get_biotools_response_cached(tool)

        end = time.time()
        duration = end - start
        times.append(duration)

        cache_info = get_biotools_response_cached.cache_info()
        cache_status = "CACHED" if cache_info.hits > 0 and tool in [test_tools[j] for j in range(i)] else "LOADED"

        print(
            f"Query {i + 1} ({tool}): {duration:.6f}s ({cache_status}) - Cache: {cache_info.hits}/{cache_info.hits + cache_info.misses}"
        )

    cache_info = get_biotools_response_cached.cache_info()
    hit_rate = (
        cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
    )

    print("\\n📈 Cache Performance:")
    print(f"   Cache hits: {cache_info.hits}/{cache_info.hits + cache_info.misses}")
    print(f"   Hit rate: {hit_rate:.1%}")
    print(f"   Unique tools cached: {cache_info.currsize}")

    return hit_rate


if __name__ == "__main__":
    print("🚀 Module Linting Performance Optimization Test")
    print("=" * 50)

    # Test EDAM caching
    edam_speedup = test_edam_caching_performance()

    # Test bio.tools caching
    biotools_hit_rate = test_biotools_caching_performance()

    print("\\n🎉 Performance Test Results Summary:")
    print(f"   🔥 EDAM caching speedup: {edam_speedup:.0f}x faster")
    print(f"   🔥 Bio.tools cache hit rate: {biotools_hit_rate:.1%}")
    print("\\n💡 Expected real-world impact:")
    print("   • Significant reduction in network requests")
    print("   • Near-instant subsequent EDAM lookups")
    print("   • Faster linting of modules with repeated tools")
    print("   • Better scaling with number of modules")
