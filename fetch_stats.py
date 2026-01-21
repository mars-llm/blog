#!/usr/bin/env python3
"""Fetch Bitcoin and Lightning Network decentralization stats.

Writes to stats.json for inclusion in static site build.
Uses mempool.space API (no auth required).
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATS_FILE = ROOT / "stats.json"

MEMPOOL_API = "https://mempool.space/api/v1"
MEMPOOL_API_V2 = "https://mempool.space/api"


def fetch_json(url: str, timeout: int = 30) -> dict | list | None:
    """Fetch JSON from URL, return None on error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mars-blog-stats/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        print(f"Error fetching {url}: {e}")
        return None


def format_number(n: int | float, decimals: int = 0) -> str:
    """Format large numbers with K/M/T suffixes."""
    if n >= 1_000_000_000_000:
        return f"{n / 1_000_000_000_000:.{decimals}f}T"
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.{decimals}f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.{decimals}f}M"
    if n >= 1_000:
        return f"{n / 1_000:.{decimals}f}K"
    return f"{n:.{decimals}f}" if decimals else str(int(n))


def fetch_bitcoin_stats() -> dict:
    """Fetch Bitcoin network stats from mempool.space."""
    stats = {}

    # Block height and difficulty
    tip = fetch_json(f"{MEMPOOL_API_V2}/blocks/tip/height")
    if tip is not None:
        stats["block_height"] = tip
        stats["block_height_fmt"] = format_number(tip)

    # Hashrate and difficulty
    hashrate_data = fetch_json(f"{MEMPOOL_API}/mining/hashrate/3d")
    if hashrate_data and "currentHashrate" in hashrate_data:
        hr = hashrate_data["currentHashrate"]
        stats["hashrate_eh"] = round(hr / 1e18, 1)
        stats["hashrate_fmt"] = f"{stats['hashrate_eh']} EH/s"
    if hashrate_data and "currentDifficulty" in hashrate_data:
        diff = hashrate_data["currentDifficulty"]
        stats["difficulty"] = diff
        stats["difficulty_fmt"] = format_number(diff, 1)

    # Mempool stats
    mempool = fetch_json(f"{MEMPOOL_API_V2}/mempool")
    if mempool:
        stats["mempool_tx_count"] = mempool.get("count", 0)
        stats["mempool_tx_count_fmt"] = format_number(mempool.get("count", 0))
        stats["mempool_size_mb"] = round(mempool.get("vsize", 0) / 1_000_000, 1)

    # Fee estimates (sat/vB)
    fees = fetch_json(f"{MEMPOOL_API_V2}/v1/fees/recommended")
    if fees:
        stats["fee_fast"] = fees.get("fastestFee", 0)
        stats["fee_medium"] = fees.get("halfHourFee", 0)
        stats["fee_slow"] = fees.get("hourFee", 0)

    return stats


def fetch_lightning_stats() -> dict:
    """Fetch Lightning Network stats from mempool.space."""
    stats = {}

    ln_stats = fetch_json(f"{MEMPOOL_API}/lightning/statistics/latest")
    if ln_stats:
        stats["node_count"] = ln_stats.get("latest", {}).get("node_count", 0)
        stats["node_count_fmt"] = format_number(ln_stats.get("latest", {}).get("node_count", 0))
        stats["channel_count"] = ln_stats.get("latest", {}).get("channel_count", 0)
        stats["channel_count_fmt"] = format_number(ln_stats.get("latest", {}).get("channel_count", 0))

        capacity_sat = ln_stats.get("latest", {}).get("total_capacity", 0)
        stats["capacity_btc"] = round(capacity_sat / 1e8, 0)
        stats["capacity_btc_fmt"] = format_number(stats["capacity_btc"])

        if stats["channel_count"] > 0:
            avg_capacity = capacity_sat / stats["channel_count"]
            stats["avg_channel_sat"] = int(avg_capacity)
            stats["avg_channel_sat_fmt"] = format_number(avg_capacity)

    return stats


def main():
    print("Fetching Bitcoin stats...")
    btc = fetch_bitcoin_stats()

    print("Fetching Lightning stats...")
    ln = fetch_lightning_stats()

    stats = {
        "bitcoin": btc,
        "lightning": ln,
    }

    print(f"Writing stats to {STATS_FILE}")
    STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print("Done!")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
