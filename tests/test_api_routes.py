"""API contract tests for FREEDOM-RT routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router


class FakeRecommenderService:
    """Fake service that isolates route tests from Redis, Weaviate, and torch."""

    def __init__(self) -> None:
        self.home_calls = 0
        self.interaction_calls: list[tuple[str, str, str]] = []
        self.recommendation_calls: list[tuple[str, int]] = []
        self.search_calls: list[tuple[str, int]] = []
        self.product_calls = 0

    def get_home_feed(self, limit: int = 20) -> list[dict[str, object]]:
        self.home_calls += 1
        return [_product(article_id="home-1", score=0.11)]

    def record_interaction(
        self,
        session_id: str,
        article_id: str,
        action_type: str,
    ) -> list[float]:
        self.interaction_calls.append((session_id, article_id, action_type))
        return [0.0] * 128

    def get_recommendations(self, session_id: str, limit: int = 20) -> list[dict[str, object]]:
        self.recommendation_calls.append((session_id, limit))
        return [_product(article_id="rec-1", score=0.22)]

    def hybrid_search(self, query: str, limit: int = 20) -> list[dict[str, object]]:
        self.search_calls.append((query, limit))
        return [_product(article_id="search-1", score=0.33)]

    def insert_cold_start_product(self, payload: object) -> str:
        self.product_calls += 1
        return "00000000-0000-0000-0000-000000000001"


def _product(article_id: str, score: float) -> dict[str, object]:
    return {
        "article_id": article_id,
        "image_url": "https://example.com/item.jpg",
        "prod_name": "Test Shirt",
        "detail_desc": "Cotton shirt",
        "product_type_name": "Shirt",
        "colour_group_name": "Black",
        "graphical_appearance_name": "Solid",
        "index_name": "Menswear",
        "score": score,
    }


def _client() -> tuple[TestClient, FakeRecommenderService]:
    app = FastAPI()
    app.include_router(router)
    service = FakeRecommenderService()
    app.state.recommender_service = service
    return TestClient(app), service


def test_get_home_feed() -> None:
    client, service = _client()

    response = client.get("/api/v1/home?limit=10")

    assert response.status_code == 200
    assert response.json()[0]["article_id"] == "home-1"
    assert service.home_calls == 1


def test_post_interaction_updates_preference() -> None:
    client, service = _client()

    response = client.post(
        "/api/v1/interactions",
        json={
            "session_id": "session-1",
            "article_id": "0108775044",
            "action_type": "add_to_cart",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    assert response.json()["vector_dim"] == 128
    assert service.interaction_calls == [("session-1", "0108775044", "add_to_cart")]


def test_get_recommendations() -> None:
    client, service = _client()

    response = client.get("/api/v1/recommendations?session_id=session-1&limit=5")

    assert response.status_code == 200
    assert response.json()[0]["article_id"] == "rec-1"
    assert service.recommendation_calls == [("session-1", 5)]


def test_get_hybrid_search() -> None:
    client, service = _client()

    response = client.get("/api/v1/search?q=black%20shirt&limit=7")

    assert response.status_code == 200
    assert response.json()[0]["article_id"] == "search-1"
    assert service.search_calls == [("black shirt", 7)]


def test_post_cold_start_product() -> None:
    client, service = _client()

    response = client.post(
        "/api/v1/products",
        json={
            "article_id": "0999999001",
            "image_url": "https://example.com/new-item.jpg",
            "prod_name": "New Jacket",
            "detail_desc": "Lightweight jacket",
            "product_type_name": "Jacket",
            "colour_group_name": "Blue",
            "graphical_appearance_name": "Solid",
            "index_name": "Ladieswear",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inserted"
    assert response.json()["article_id"] == "0999999001"
    assert service.product_calls == 1
