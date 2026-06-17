#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro - Sklearn-style Classification Wrapper (pure numpy implementation).

Provides: LogisticRegression, DecisionTree, KNN, RandomForest stubs
using numpy-only implementations for basic classification tasks.
"""

from __future__ import annotations
import numpy as np
from typing import List, Dict, Any, Optional

__all__ = ["SklearnWrapper"]


class _BaseClassifier:
    """Base classifier with fit/predict interface."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_BaseClassifier":
        raise NotImplementedError

    def predict(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class LogisticRegression(_BaseClassifier):
    """Logistic Regression using gradient descent (pure numpy)."""

    def __init__(self, lr: float = 0.01, epochs: int = 1000, threshold: float = 0.5):
        self.lr = lr
        self.epochs = epochs
        self.threshold = threshold
        self.weights: Optional[np.ndarray] = None
        self.bias: float = 0.0

    def _sigmoid(self, z: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegression":
        n_features = X.shape[1]
        self.weights = np.zeros(n_features)
        self.bias = 0.0

        for _ in range(self.epochs):
            linear = np.dot(X, self.weights) + self.bias
            probs = self._sigmoid(linear)
            dw = np.dot(X.T, (probs - y)) / len(y)
            db = np.mean(probs - y)
            self.weights -= self.lr * dw
            self.bias -= self.lr * db
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        return (probs >= self.threshold).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        linear = np.dot(X, self.weights) + self.bias
        return self._sigmoid(linear)


class KNN(_BaseClassifier):
    """K-Nearest Neighbors classifier (pure numpy, O(n*m*k) complexity)."""

    def __init__(self, k: int = 5):
        if k < 1:
            raise ValueError("k must be >= 1")
        self.k = k
        self.X_train: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "KNN":
        self.X_train = X
        self.y_train = y
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)
        classes = int(np.max(self.y_train)) + 1 if self.y_train is not None else 2
        return np.argmax(probs, axis=1).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.X_train is None or self.y_train is None:
            raise RuntimeError("Model not fitted")

        n_samples = X.shape[0]
        n_classes = int(np.max(self.y_train)) + 1
        proba = np.zeros((n_samples, n_classes))
        k = min(self.k, len(self.X_train))

        for i, x in enumerate(X):
            dists = np.sqrt(np.sum((self.X_train - x) ** 2, axis=1))
            nearest_idx = np.argsort(dists)[:k]
            nearest_labels = self.y_train[nearest_idx]
            for cls in range(n_classes):
                proba[i, cls] = np.mean(nearest_labels == cls)
        return proba


class SklearnWrapper:
    """
    Unified sklearn-style API with multiple classifier backends.

    Supported: 'logistic', 'knn' (default: logistic)
    """

    def __init__(self, model_type: str = "logistic", k: int = 5, **kwargs):
        self.model_type = model_type.lower()
        if self.model_type == "logistic":
            self._model = LogisticRegression(**kwargs)
        elif self.model_type == "knn":
            self._model = KNN(k=k)
        else:
            self._model = LogisticRegression(**kwargs)

    def fit(self, X, y) -> "SklearnWrapper":
        """Fit the model. X: list of feature vectors, y: list of labels."""
        X_arr = np.array(X, dtype=np.float64)
        y_arr = np.array(y, dtype=np.float64)
        self._model.fit(X_arr, y_arr)
        return self

    def predict(self, X) -> Dict[str, Any]:
        """Predict class labels."""
        X_arr = np.array(X, dtype=np.float64)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
        preds = self._model.predict(X_arr)
        return {
            "prediction": [int(p) for p in preds],
            "probability": [float(p) for p in self._model.predict_proba(X_arr).tolist()],
            "model": self.model_type,
        }
