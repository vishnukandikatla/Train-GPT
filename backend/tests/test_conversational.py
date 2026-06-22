import pytest
import os
import re
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.mongodb import init_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    import asyncio
    from backend.database.mongodb import get_db, init_db
    async def _setup():
        await init_db()
        db = get_db()
        if type(db).__name__ == "MockDatabase":
            db.state["conversations"] = []
            db.state["session_contexts"] = []
            db.save()
        else:
            await db.conversations.delete_many({})
            await db.session_contexts.delete_many({})
    asyncio.run(_setup())

def test_route_date_availability_flow():
    """
    Checks: route -> date -> availability checks context propagation.
    """
    session_id = "conv_test_session_1"
    
    # 1. Provide route
    res = client.post("/api/chat", json={
        "message": "Peddapalli to Hyderabad",
        "session_id": session_id
    })
    assert res.status_code == 200
    reply = res.json()["reply"]
    # Should recommend Telangana Express and ask for travel date
    assert "Telangana Express" in reply
    assert "date" in reply.lower()
    
    # 2. Provide date
    res = client.post("/api/chat", json={
        "message": "24-06-2026",
        "session_id": session_id
    })
    assert res.status_code == 200
    reply = res.json()["reply"]
    # Should check trains for date and ask for travel class
    assert "24 June" in reply or "2026-06-24" in reply
    assert "Sleeper" in reply or "class" in reply.lower()
    
    # 3. Check seat availability for class type
    res = client.post("/api/chat", json={
        "message": "SL",
        "session_id": session_id
    })
    assert res.status_code == 200
    reply = res.json()["reply"]
    # Should check availability for train 12724, class SL on 2026-06-24 and ask if want to book
    assert "12724" in reply
    assert "seats" in reply.lower()
    assert "book" in reply.lower()


def test_route_train_booking_flow():
    """
    Checks: route -> select train / book -> passenger details -> booking.
    """
    session_id = "conv_test_session_2"
    
    # 1. Search route and date together
    res = client.post("/api/chat", json={
        "message": "Peddapalli to Hyderabad on 2026-06-24",
        "session_id": session_id
    })
    assert res.status_code == 200
    reply = res.json()["reply"]
    assert "12724" in reply
    
    # 2. Command "book first one" or "book it"
    res = client.post("/api/chat", json={
        "message": "book first one",
        "session_id": session_id
    })
    assert res.status_code == 200
    reply = res.json()["reply"]
    # Should ask for passenger details
    assert "passenger" in reply.lower()
    
    # 3. Provide passenger details
    res = client.post("/api/chat", json={
        "message": "Rajesh 28 Male",
        "session_id": session_id
    })
    assert res.status_code == 200
    reply = res.json()["reply"]
    # Should return successful booking confirmation
    assert "successful" in reply.lower() or "confirmed" in reply.lower()
    assert "pnr" in reply.lower()


def test_booking_pnr_status_flow():
    """
    Checks: booking -> PNR status track.
    """
    session_id = "conv_test_session_3"
    
    # 1. Search and Book
    client.post("/api/chat", json={
        "message": "Peddapalli to Hyderabad on 2026-06-24",
        "session_id": session_id
    })
    client.post("/api/chat", json={
        "message": "SL",
        "session_id": session_id
    })
    client.post("/api/chat", json={
        "message": "book ticket",
        "session_id": session_id
    })
    res_book = client.post("/api/chat", json={
        "message": "Rajesh 28 Male",
        "session_id": session_id
    })
    reply_book = res_book.json()["reply"]
    pnr_match = re.search(r"\b(\d{10})\b", reply_book)
    assert pnr_match is not None, "PNR not found in booking reply"
    pnr = pnr_match.group(1)
    
    # 2. Check PNR status
    res_pnr = client.post("/api/chat", json={
        "message": "check my pnr status",
        "session_id": session_id
    })
    assert res_pnr.status_code == 200
    reply_pnr = res_pnr.json()["reply"]
    assert pnr in reply_pnr
    assert "confirmed" in reply_pnr.lower() or "status" in reply_pnr.lower()
    assert "Rajesh" in reply_pnr


def test_deep_memory_stress_test():
    """
    Performs 15-turn conversational memory stress test:
    Checks that the assistant remembers train, class, date, route, passengers, and PNR across turns,
    and never says coordinator leakage messages.
    """
    session_id = "memory_stress_test_session"
    
    # Turn 1: Route query
    res = client.post("/api/chat", json={"message": "Peddapalli to Hyderabad", "session_id": session_id})
    assert "Telangana Express" in res.json()["reply"]
    assert "coordinator" not in res.json()["reply"].lower()
    
    # Turn 2: Date query
    res = client.post("/api/chat", json={"message": "24-06-2026", "session_id": session_id})
    assert "24 June" in res.json()["reply"] or "2026-06-24" in res.json()["reply"]
    
    # Turn 3: Search train list explicitly
    res = client.post("/api/chat", json={"message": "show trains", "session_id": session_id})
    assert "12724" in res.json()["reply"]
    
    # Turn 4: Seat availability query
    res = client.post("/api/chat", json={"message": "check availability", "session_id": session_id})
    # Asks for travel class
    assert "class" in res.json()["reply"].lower() or "sleeper" in res.json()["reply"].lower()
    
    # Turn 5: Provide travel class
    res = client.post("/api/chat", json={"message": "SL", "session_id": session_id})
    # Displays seats available and asks if wants to book
    assert "seats" in res.json()["reply"].lower()
    
    # Turn 6: Fare inquiry
    res = client.post("/api/chat", json={"message": "what is the fare", "session_id": session_id})
    # Returns fare details
    assert "fare" in res.json()["reply"].lower() or "price" in res.json()["reply"].lower()
    
    # Turn 7: Start Booking flow
    res = client.post("/api/chat", json={"message": "book ticket", "session_id": session_id})
    # Asks for passenger details
    assert "passenger" in res.json()["reply"].lower()
    
    # Turn 8: Provide first passenger
    res = client.post("/api/chat", json={"message": "Rajesh 28 Male", "session_id": session_id})
    assert "booking successful" in res.json()["reply"].lower() or "confirmed" in res.json()["reply"].lower()
    pnr_match = re.search(r"\b(\d{10})\b", res.json()["reply"])
    assert pnr_match is not None
    pnr = pnr_match.group(1)
    
    # Turn 9: Add another passenger
    res = client.post("/api/chat", json={"message": "add another passenger Sneha 26 Female", "session_id": session_id})
    assert "Sneha" in res.json()["reply"]
    # Check that a PNR is still available
    pnr_match2 = re.search(r"\b(\d{10})\b", res.json()["reply"])
    assert pnr_match2 is not None
    pnr = pnr_match2.group(1)
    
    # Turn 10: Query chosen train
    res = client.post("/api/chat", json={"message": "what train did I choose", "session_id": session_id})
    assert "12724" in res.json()["reply"]
    
    # Turn 11: Query travel date
    res = client.post("/api/chat", json={"message": "what date am I travelling", "session_id": session_id})
    assert "24 June" in res.json()["reply"] or "2026-06-24" in res.json()["reply"]
    
    # Turn 12: Query travel class
    res = client.post("/api/chat", json={"message": "what class am I travelling in", "session_id": session_id})
    assert "SL" in res.json()["reply"] or "Sleeper" in res.json()["reply"]
    
    # Turn 13: Query passenger count
    res = client.post("/api/chat", json={"message": "how many passengers are booked", "session_id": session_id})
    assert "2" in res.json()["reply"]
    assert "Rajesh" in res.json()["reply"]
    assert "Sneha" in res.json()["reply"]
    
    # Turn 14: Query PNR
    res = client.post("/api/chat", json={"message": "what is my pnr", "session_id": session_id})
    assert pnr in res.json()["reply"]
    
    # Turn 15: Check PNR status
    res = client.post("/api/chat", json={"message": "check my pnr status", "session_id": session_id})
    assert pnr in res.json()["reply"]
    assert "Rajesh" in res.json()["reply"]
    assert "Sneha" in res.json()["reply"]
