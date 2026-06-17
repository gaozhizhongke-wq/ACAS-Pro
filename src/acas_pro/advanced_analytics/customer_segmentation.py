#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Customer Segmentation Engine
RFM (Recency, Frequency, Monetary) analysis for e-commerce customer segmentation.

No external ML dependencies — pure numpy implementation.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class RFMScore:
    r: int   # Recency score 1-5 (5=most recent)
    f: int   # Frequency score 1-5 (5=most frequent)
    m: int   # Monetary score 1-5 (5=highest spend)


class CustomerSegmentation:
    """
    Segment customers using RFM (Recency, Frequency, Monetary) analysis.

    Args:
        now_timestamp: Reference "now" as Unix timestamp. Defaults to current time.
        r_percentiles: Percentile boundaries for Recency (default 20/40/60/80/100)
        f_percentiles: Percentile boundaries for Frequency
        m_percentiles: Percentile boundaries for Monetary
    """

    def __init__(
        self,
        now_timestamp: Optional[int] = None,
        r_percentiles: tuple = (20, 40, 60, 80, 100),
        f_percentiles: tuple = (20, 40, 60, 80, 100),
        m_percentiles: tuple = (20, 40, 60, 80, 100),
    ) -> None:
        self.now_ts = now_timestamp
        self.r_pct = r_percentiles
        self.f_pct = f_percentiles
        self.m_pct = m_percentiles

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(
        self,
        data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Segment customers from transaction/order history.

        Args:
            data: List of customer transaction dicts, each containing:
                - customer_id: str
                - timestamp: int (Unix) or ISO str
                - amount: float (transaction value)
                - order_id: str (optional, for frequency counting)

        Returns:
            Dict with:
              - segments: list of segment labels per customer
              - distribution: segment counts and percentages
              - rfm_scores: per-customer R/F/M scores
              - summary: top characteristics per segment
        """
        if not data:
            return self._empty_result()

        # Parse timestamps
        import time as _time
        now = self.now_ts or int(_time.time())

        customers: Dict[str, Dict[str, Any]] = {}

        for txn in data:
            cid = str(txn.get("customer_id", txn.get("cid", "")))
            if not cid:
                continue

            try:
                ts = txn.get("timestamp")
                if isinstance(ts, str):
                    import datetime as _dt
                    parsed = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts = int(parsed.timestamp())
                ts = int(ts)
            except (ValueError, TypeError, OSError):
                ts = now

            amount = float(txn.get("amount", txn.get("monetary", 0.0)))

            if cid not in customers:
                customers[cid] = {
                    "customer_id": cid,
                    "recency": now - ts,    # lower = more recent
                    "frequency": 0,
                    "monetary": 0.0,
                }

            customers[cid]["frequency"] += 1
            customers[cid]["monetary"] += amount
            # Keep minimum recency (most recent purchase)
            if now - ts < customers[cid]["recency"]:
                customers[cid]["recency"] = now - ts

        if not customers:
            return self._empty_result()

        cid_list = list(customers.keys())
        recency_arr = np.array([customers[c]["recency"] for c in cid_list], dtype=np.float64)
        frequency_arr = np.array([float(customers[c]["frequency"]) for c in cid_list], dtype=np.float64)
        monetary_arr = np.array([customers[c]["monetary"] for c in cid_list], dtype=np.float64)

        # Compute percentile thresholds
        r_thresholds = np.percentile(recency_arr, self.r_pct)
        f_thresholds = np.percentile(frequency_arr, self.f_pct)
        m_thresholds = np.percentile(monetary_arr, self.m_pct)

        def _score_r(val: float) -> int:
            # Lower recency (more recent) = higher score
            for i, th in enumerate(r_thresholds):
                if val <= th:
                    return min(i + 1, 5)
            return 5

        def _score_f(val: float) -> int:
            for i, th in enumerate(f_thresholds):
                if val <= th:
                    return min(i + 1, 5)
            return 5

        def _score_m(val: float) -> int:
            for i, th in enumerate(m_thresholds):
                if val <= th:
                    return min(i + 1, 5)
            return 5

        def _label(r: int, f: int, m: int) -> str:
            # RFM segment naming convention
            if r >= 4 and f >= 4 and m >= 4:
                return "Champions"
            if r >= 4 and f <= 2:
                return "New Customers"
            if r >= 3 and f >= 3:
                return "Loyal Customers"
            if r >= 3 and f <= 2:
                return "Potential Loyalists"
            if r <= 2 and f >= 3:
                return "At Risk"
            if r <= 2 and f <= 2:
                return "Hibernating"
            return "Others"

        rfm_scores: Dict[str, Dict[str, Any]] = {}
        segment_counts: Dict[str, int] = {}

        for cid in cid_list:
            c = customers[cid]
            r = _score_r(c["recency"])
            f = _score_f(c["frequency"])
            m = _score_m(c["monetary"])
            label = _label(r, f, m)

            rfm_scores[cid] = {
                "customer_id": cid,
                "r": r,
                "f": f,
                "m": m,
                "rfm_combined": r * 100 + f * 10 + m,
                "segment": label,
            }
            segment_counts[label] = segment_counts.get(label, 0) + 1

        total = len(cid_list)
        distribution = {
            seg: {"count": cnt, "pct": round(cnt / total * 100, 2)}
            for seg, cnt in sorted(segment_counts.items(), key=lambda x: -x[1])
        }

        # Segment characteristics
        segment_summary: Dict[str, Dict[str, Any]] = {}
        for seg in segment_counts:
            seg_cids = [cid for cid, s in rfm_scores.items() if s["segment"] == seg]
            seg_r = [rfm_scores[c]["r"] for c in seg_cids]
            seg_f = [rfm_scores[c]["f"] for c in seg_cids]
            seg_m = [rfm_scores[c]["m"] for c in seg_cids]
            segment_summary[seg] = {
                "avg_r": round(float(np.mean(seg_r)), 2),
                "avg_f": round(float(np.mean(seg_f)), 2),
                "avg_m": round(float(np.mean(seg_m)), 2),
                "customer_count": len(seg_cids),
            }

        return {
            "segments": {cid: rfm_scores[cid]["segment"] for cid in cid_list},
            "distribution": distribution,
            "rfm_scores": rfm_scores,
            "segment_summary": segment_summary,
            "total_customers": total,
        }

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "segments": {},
            "distribution": {},
            "rfm_scores": {},
            "segment_summary": {},
            "total_customers": 0,
        }
