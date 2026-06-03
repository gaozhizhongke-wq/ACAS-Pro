# -*- coding: utf-8 -*-
"""Locust performance tests for ACAS Pro API."""
from locust import HttpUser, task, between
import random


class ACASProUser(HttpUser):
    """Simulated user interacting with ACAS Pro."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    host = "http://localhost:5000"
    
    def on_start(self):
        """Login and get token."""
        # Register a test user (if not exists)
        self.client.post("/api/auth/register", json={
            "account": f"test_user_{self.user_id}",
            "password": "Test123!@#",
            "nickname": "Test User"
        }, catch_response=True)
        
        # Login
        response = self.client.post("/api/auth/login", json={
            "account": f"test_user_{self.user_id}",
            "password": "Test123!@#"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}
    
    @task(10)
    def get_health(self):
        """Health check - most frequent."""
        self.client.get("/api/health")
    
    @task(5)
    def get_dashboard_stats(self):
        """Dashboard stats."""
        self.client.get("/api/dashboard/stats", headers=self.headers)
    
    @task(3)
    def get_products(self):
        """List products."""
        self.client.get("/api/products", headers=self.headers)
    
    @task(2)
    def get_accounts(self):
        """List accounts."""
        self.client.get("/api/accounts", headers=self.headers)
    
    @task(2)
    def get_forecast(self):
        """Forecast data."""
        self.client.get("/api/forecast/daily", headers=self.headers)
    
    @task(1)
    def llm_chat(self):
        """LLM chat - least frequent (expensive)."""
        self.client.post("/api/llm/chat", 
            headers=self.headers,
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 50
            },
            catch_response=True  # Don't fail if LLM not configured
        )
    
    @task(1)
    def get_user_profile(self):
        """Get current user profile."""
        self.client.get("/api/auth/me", headers=self.headers)


class ReadOnlyUser(HttpUser):
    """User who only reads public data."""
    
    wait_time = between(0.5, 2)
    host = "http://localhost:5000"
    
    @task(10)
    def get_health(self):
        self.client.get("/api/health")
    
    @task(5)
    def get_stats(self):
        self.client.get("/api/stats")
    
    @task(3)
    def get_activity(self):
        self.client.get("/api/activity")
