# Cache Policy Simulator

Replay a timestamped request trace through LRU and LFU caches. Compare hit rate, origin fetches, evictions, and estimated latency as capacity or TTL changes. The simulator uses byte-sized entries, a deterministic LFU tie-breaker, and optional time-to-live expiry. It writes a compact SVG comparison chart without a plotting dependency.

```sh
python simulate.py examples/trace.csv --capacities 2,4,8 --ttl 30 --svg comparison.svg
python -m unittest discover -s tests -v
```

CSV columns: `time,key,size,origin_ms,cache_ms`. Times and latency fields are nonnegative numbers; size is a positive integer. Repeated keys retain the original size until the next miss. Capacity is in the same units as size. An object larger than the cache remains a miss. LFU counts reset when an entry is evicted.

