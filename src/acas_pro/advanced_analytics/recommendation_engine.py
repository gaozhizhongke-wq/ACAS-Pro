#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Recommendation Engine
Item-based collaborative filtering and popularity-based recommendations.

No external ML dependencies — pure numpy implementation.
"""

from __future__ import annotations

import numpy as np
from collections import defaultdict
from typing import List, Dict, Any, Optional


class RecommendationEngine:
    """
    Product/recommendation engine using:
      1. Item-based Collaborative Filtering (IBCF) — cosine similarity
      2. Popularity-based fallback — top items by interaction count

    Args:
        min_interactions: Minimum interactions before an item is recommended
        top_k: Number of recommendations to return
        similarity_threshold: Minimum similarity score to include (0-1)
    """

    def __init__(
        self,
        min_interactions: int = 2,
        top_k: int = 10,
        similarity_threshold: float = 0.1,
    ) -> None:
        self.min_interactions = min_interactions
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self._item_users: Dict[str, set] = defaultdict(set)  # item_id -> set of user_ids
        self._user_items: Dict[str, set] = defaultdict(set)  # user_id -> set of item_ids
        self._item_popularity: Dict[str, int] = defaultdict(int)
        self._fitted = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, interactions: List[Dict[str, str]]) -> "RecommendationEngine":
        """
        Build the recommendation model from user-item interaction data.

        Args:
            interactions: List of {"user_id": str, "item_id": str} dicts.
                         Optionally include "rating": float (1-5) for weighted similarity.
        Returns:
            self (for chaining)
        """
        self._item_users.clear()
        self._user_items.clear()
        self._item_popularity.clear()

        for interaction in interactions:
            user_id = str(interaction.get("user_id", ""))
            item_id = str(interaction.get("item_id", ""))
            if not user_id or not item_id:
                continue
            self._item_users[item_id].add(user_id)
            self._user_items[user_id].add(item_id)
            self._item_popularity[item_id] += 1

        self._fitted = True
        return self

    def recommend(
        self,
        user_id: Optional[str] = None,
        item_ids: Optional[List[str]] = None,
        n: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get recommendations.

        If user_id is provided:
          - Uses item-based collaborative filtering to find similar items
            to ones the user has interacted with.
          - Falls back to popularity if user has no history.

        If item_ids is provided (no user_id):
          - Finds items similar to the given items (item-to-item recommendations).

        Args:
            user_id: Target user (optional)
            item_ids: List of item IDs to base recommendations on (optional)
            n: Override number of recommendations (default: self.top_k)

        Returns:
            Dict with:
              - recommendations: list of {"item_id": str, "score": float} sorted by score desc
              - score: overall confidence score (0-1) for these recommendations
              - method: 'ibcf' | 'popularity' | 'item_ibcf'
              - total_items: total unique items in model
        """
        n_recs = n or self.top_k

        if not self._fitted:
            return self._empty_result()

        # Item-based CF for known user
        if user_id and user_id in self._user_items:
            return self._recommend_for_user(user_id, n_recs)

        # Item-to-item similarity
        if item_ids:
            return self._recommend_similar_items(item_ids, n_recs)

        # Popularity fallback
        return self._popularity_recommendations(n_recs)

    # ------------------------------------------------------------------
    # Internal recommendation methods
    # ------------------------------------------------------------------

    def _cosine_similarity(self, users_a: set, users_b: set) -> float:
        """Cosine similarity between two user sets."""
        if not users_a or not users_b:
            return 0.0
        intersection = len(users_a & users_b)
        norm_a = np.sqrt(len(users_a))
        norm_b = np.sqrt(len(users_b))
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        return intersection / (norm_a * norm_b)

    def _recommend_for_user(self, user_id: str, n_recs: int) -> Dict[str, Any]:
        """IBCF: find items similar to ones user has interacted with."""
        user_items = self._user_items[user_id]
        user_items_list = list(user_items)

        # For each item the user has interacted with, find similar items
        candidate_scores: Dict[str, float] = defaultdict(float)

        for item_a in user_items_list:
            users_a = self._item_users[item_a]
            for item_b, users_b in self._item_users.items():
                if item_b in user_items:
                    continue
                if self._item_popularity[item_b] < self.min_interactions:
                    continue
                sim = self._cosine_similarity(users_a, users_b)
                if sim >= self.similarity_threshold:
                    candidate_scores[item_b] += sim

        if not candidate_scores:
            # Fall back to popularity
            return self._popularity_recommendations(n_recs, exclude=user_items)

        # Sort by score
        sorted_items = sorted(candidate_scores.items(), key=lambda x: -x[1])
        top_items = sorted_items[:n_recs]

        max_score = top_items[0][1] if top_items else 1.0
        recommendations = [
            {"item_id": item, "score": round(score / max_score, 4)}
            for item, score in top_items
        ]
        confidence = min(len(top_items) / self.top_k, 1.0) if top_items else 0.0

        return {
            "recommendations": recommendations,
            "score": round(confidence, 3),
            "method": "ibcf",
            "user_id": user_id,
            "based_on_items": user_items_list,
            "total_items": len(self._item_users),
        }

    def _recommend_similar_items(
        self, item_ids: List[str], n_recs: int
    ) -> Dict[str, Any]:
        """Item-to-item: find items similar to a given set of items."""
        candidate_scores: Dict[str, float] = defaultdict(float)
        valid_input = [i for i in item_ids if i in self._item_users]

        if not valid_input:
            return self._popularity_recommendations(n_recs)

        for item_a in valid_input:
            users_a = self._item_users[item_a]
            for item_b, users_b in self._item_users.items():
                if item_b in valid_input:
                    continue
                sim = self._cosine_similarity(users_a, users_b)
                if sim >= self.similarity_threshold:
                    candidate_scores[item_b] += sim

        if not candidate_scores:
            return self._popularity_recommendations(n_recs)

        sorted_items = sorted(candidate_scores.items(), key=lambda x: -x[1])
        top_items = sorted_items[:n_recs]
        max_score = top_items[0][1] if top_items else 1.0

        return {
            "recommendations": [
                {"item_id": item, "score": round(score / max_score, 4)}
                for item, score in top_items
            ],
            "score": round(min(len(top_items) / max(n_recs, 1), 1.0), 3),
            "method": "item_ibcf",
            "based_on_items": valid_input,
            "total_items": len(self._item_users),
        }

    def _popularity_recommendations(
        self, n_recs: int, exclude: Optional[set] = None
    ) -> Dict[str, Any]:
        """Popularity-based: top items by interaction count."""
        exclude = exclude or set()
        sorted_items = sorted(
            [(i, c) for i, c in self._item_popularity.items() if i not in exclude],
            key=lambda x: -x[1],
        )
        top_items = sorted_items[:n_recs]
        max_count = top_items[0][1] if top_items else 1

        return {
            "recommendations": [
                {"item_id": item, "score": round(count / max_count, 4)}
                for item, count in top_items
            ],
            "score": 0.5,  # Lower confidence for popularity-based
            "method": "popularity",
            "total_items": len(self._item_users),
        }

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "recommendations": [],
            "score": 0.0,
            "method": "none",
            "total_items": 0,
        }
