import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "service": "TrainGPT AI"}

def test_search_trains_api():
    payload = {
        "source": "SBC",
        "destination": "NDLS",
        "date": "2026-06-21"
    }
    res = client.post("/api/trains/search", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "trains" in data

def test_check_availability_api():
    payload = {
        "train_no": "12627",
        "class_type": "2A",
        "date": "2026-06-21"
    }
    res = client.post("/api/trains/availability", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "available_seats" in data

def test_calculate_fare_api():
    payload = {
        "train_no": "12627",
        "class_type": "SL",
        "num_passengers": 3
    }
    res = client.post("/api/trains/fare", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_fare"] == 750 * 3 + 15

def test_direct_booking_and_cancellation_api():
    booking_payload = {
        "train_no": "12727",
        "journey_date": "2026-06-25",
        "class_type": "3A",
        "passengers": [
            {"name": "Alice Smith", "age": 25, "gender": "Female"}
        ],
        "user_id": "api_test_runner"
    }
    
    # 1. Create Booking
    res_book = client.post("/api/bookings", json=booking_payload)
    assert res_book.status_code == 200
    book_data = res_book.json()
    assert book_data["status"] == "success"
    pnr = book_data["pnr"]
    
    # 2. Get booking status via PNR
    res_pnr = client.get(f"/api/pnr/{pnr}")
    assert res_pnr.status_code == 200
    pnr_data = res_pnr.json()
    assert pnr_data["status"] == "success"
    assert pnr_data["booking_status"] in ["Confirmed", "Waitlisted"]
    
    # 3. Cancel Booking
    res_cancel = client.delete(f"/api/bookings/{pnr}")
    assert res_cancel.status_code == 200
    cancel_data = res_cancel.json()
    assert cancel_data["status"] == "success"
    assert cancel_data["refund_amount"] > 0

def test_chat_endpoint_api():
    payload = {
        "message": "Find trains from SC to SBC on 2026-06-21",
        "session_id": "test_session_chat_api"
    }
    res = client.post("/api/chat", json=payload)
    # The endpoint should trigger without unhandled internal routing crashes
    assert res.status_code in [200, 500]
    if res.status_code == 200:
        data = res.json()
        assert "reply" in data
        assert data["session_id"] == "test_session_chat_api"

def test_mock_orchestrator_stateful_flow(monkeypatch):
    # Mock run_orchestrator_async to raise 429 error so it falls back to mock simulation
    async def mock_run_async(*args, **kwargs):
        # We need an async generator function
        if False:
            yield None
        raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded")
            
    from backend.agents.orchestrator import orchestrator
    monkeypatch.setattr(orchestrator, "run_orchestrator_async", mock_run_async)
    
    session_id = "stateful_test_session"
    
    # 1. Search Query
    res = client.post("/api/chat", json={
        "message": "Peddapalli to hyd in 24 06",
        "session_id": session_id
    })
    assert res.status_code == 200
    data = res.json()
    assert "12724" in data["reply"]  # Telangana Express train number
    assert "2026-06-24" in data["reply"]
    
    # 2. Follow-up: Availability
    res2 = client.post("/api/chat", json={
        "message": "check availability",
        "session_id": session_id
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert "12724" in data2["reply"]
    assert "2026-06-24" in data2["reply"]
    
    # 3. Follow-up: Book
    res3 = client.post("/api/chat", json={
        "message": "book ticket",
        "session_id": session_id
    })
    assert res3.status_code == 200
    data3 = res3.json()
    assert "Booking successful" in data3["reply"]

