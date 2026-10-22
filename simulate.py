"""Replay requests through capacity-limited LRU and LFU caches."""
import argparse
import csv
import html
import json
from pathlib import Path


class Cache:
    def __init__(self, capacity, policy="lru", ttl=None):
        if capacity <= 0 or policy not in ("lru", "lfu") or (ttl is not None and ttl <= 0):
            raise ValueError("invalid capacity, policy, or TTL")
        self.capacity, self.policy, self.ttl = capacity, policy, ttl
        self.entries = {}
        self.used = 0
        self.clock = 0
        self.hits = self.misses = self.evictions = 0
        self.total_ms = 0.0

    def _remove(self, key):
        self.used -= self.entries.pop(key)["size"]

    def _expire(self, now):
        for key, entry in list(self.entries.items()):
            if entry["expires"] is not None and now >= entry["expires"]:
                self._remove(key)

    def access(self, now, key, size, origin_ms, cache_ms):
        if size <= 0 or now < 0 or min(origin_ms, cache_ms) < 0:
            raise ValueError("invalid trace row")
        self.clock += 1
        self._expire(now)
        if key in self.entries:
            entry = self.entries[key]
            entry["last"] = self.clock
            entry["frequency"] += 1
            self.hits += 1
            self.total_ms += cache_ms
            return True
        self.misses += 1
        self.total_ms += origin_ms
        if size > self.capacity:
            return False
        while self.used + size > self.capacity:
            if self.policy == "lru":
                victim = min(self.entries, key=lambda k: (self.entries[k]["last"], self.entries[k]["born"]))
            else:
                victim = min(self.entries, key=lambda k: (self.entries[k]["frequency"], self.entries[k]["born"]))
            self._remove(victim)
            self.evictions += 1
        self.entries[key] = {"size": size, "born": self.clock, "last": self.clock,
                             "frequency": 1, "expires": now + self.ttl if self.ttl else None}
        self.used += size
        return False

    def summary(self):
        total = self.hits + self.misses
        return {"policy": self.policy.upper(), "capacity": self.capacity, "requests": total,
                "hits": self.hits, "misses": self.misses, "hit_rate": round(self.hits / total, 4) if total else 0,
                "evictions": self.evictions, "total_ms": round(self.total_ms, 2),
                "mean_ms": round(self.total_ms / total, 2) if total else 0}


def read_trace(path):
    with open(path, newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    required = {"time", "key", "size", "origin_ms", "cache_ms"}
    if rows and not required <= rows[0].keys():
        raise ValueError("trace needs time,key,size,origin_ms,cache_ms")
    trace = []
    for row in rows:
        trace.append((float(row["time"]), row["key"], int(row["size"]), float(row["origin_ms"]), float(row["cache_ms"])))
    if any(b[0] < a[0] for a, b in zip(trace, trace[1:])):
        raise ValueError("trace must be sorted by time")
    return trace


def compare(trace, capacities, ttl=None):
    results = []
    for capacity in capacities:
        for policy in ("lru", "lfu"):
            cache = Cache(capacity, policy, ttl)
            for row in trace:
                cache.access(*row)
            results.append(cache.summary())
    return results


def svg_chart(results):
    width, row_height = 640, 35
    height = 70 + len(results) * row_height
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#101828"/>',
            '<text x="20" y="30" fill="white" font-family="sans-serif" font-size="18">Cache hit rate by policy and capacity</text>']
    for index, row in enumerate(results):
        y = 58 + index * row_height
        label = html.escape(f"{row['policy']}  {row['capacity']}")
        bar = int(380 * row["hit_rate"])
        color = "#42c7a1" if row["policy"] == "LRU" else "#75a8ff"
        body.append(f'<text x="20" y="{y + 15}" fill="white" font-family="sans-serif" font-size="13">{label}</text>')
        body.append(f'<rect x="160" y="{y}" width="{bar}" height="20" fill="{color}"/>')
        body.append(f'<text x="{170 + bar}" y="{y + 15}" fill="white" font-family="sans-serif" font-size="13">{row["hit_rate"]:.1%}</text>')
    body.append("</svg>")
    return "\n".join(body) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace")
    parser.add_argument("--capacities", default="2,4,8")
    parser.add_argument("--ttl", type=float)
    parser.add_argument("--svg", help="Write comparison SVG")
    parser.add_argument("--json", help="Write metrics JSON")
    args = parser.parse_args()
    results = compare(read_trace(args.trace), [int(x) for x in args.capacities.split(",")], args.ttl)
    for row in results:
        print(f"{row['policy']:3} capacity={row['capacity']:4} hit={row['hit_rate']:.1%} mean={row['mean_ms']:.2f}ms evictions={row['evictions']}")
    if args.svg:
        Path(args.svg).write_text(svg_chart(results), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

