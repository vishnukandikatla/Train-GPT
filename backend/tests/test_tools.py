import pytest
import os
import asyncio
from backend.services.railway_service import RailwayService
from backend.tools.search_tool import search_train, recommend_train
from backend.tools.availability_tool import check_availability
from backend.tools.fare_tool import get_fare
from backend.tools.booking_tool import book_ticket
from backend.tools.pnr_tool import check_pnr
from backend.tools.cancellation_tool import cancel_ticket
from backend.database.mongodb import init_db

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Initialize the database (or mock database fallback)
    import asyncio
    asyncio.run(init_db())

def test_search_train_tool():
    # Test searching between SBC and NDLS
    res = search_train(source="SBC", destination="NDLS", date="2026-06-21")
    assert res["status"] == "success"
    assert len(res["trains"]) > 0
    assert res["trains"][0]["train_no"] == "12627"

def test_recommend_train_tool():
    # Test recommendations
    res = recommend_train(source="SBC", destination="NDLS", date="2026-06-21")
    assert res["status"] == "success"
    assert len(res["recommendations"]) > 0

def test_check_availability_tool():
    # Test seat counts query
    res = check_availability(train_no="12627", class_type="3A", date="2026-06-21")
    assert res["status"] == "success"
    assert "available_seats" in res
    assert "seat_status" in res

def test_get_fare_tool():
    # Test fare calculation for 2 passengers
    res = get_fare(train_no="12627", class_type="SL", num_passengers=2)
    assert res["status"] == "success"
    assert res["total_fare"] == 750 * 2 + 15  # SL is non-ac, no GST: 1500 + 15 = 1515
    assert res["num_passengers"] == 2

@pytest.mark.asyncio
async def test_booking_and_cancellation_workflow():
    # Test full booking and cancellation pipeline
    passengers = [{"name": "Test Passenger", "age": 30, "gender": "Male"}]
    
    # 1. Book ticket
    book_res = await book_ticket(
        train_no="12627",
        journey_date="2026-06-21",
        class_type="3A",
        passengers=passengers,
        user_id="test_runner"
    )
    assert book_res["status"] == "success"
    pnr = book_res["pnr"]
    assert len(pnr) == 10
    
    # 2. Check PNR status
    pnr_res = await check_pnr(pnr)
    assert pnr_res["status"] == "success"
    assert pnr_res["booking_status"] in ["Confirmed", "Waitlisted"]
    assert len(pnr_res["passengers"]) == 1
    
    # 3. Cancel ticket
    cancel_res = await cancel_ticket(pnr)
    assert cancel_res["status"] == "success"
    assert "refund_amount" in cancel_res
    
    # 4. Check PNR again to verify cancelled state
    pnr_cancelled = await check_pnr(pnr)
    assert pnr_cancelled["status"] == "success"
    assert pnr_cancelled["booking_status"] == "Cancelled"

def test_railway_api_key_integration():
    # Verify RAILWAY_API_KEY configuration
    key = os.getenv("RAILWAY_API_KEY")
    assert key is not None, "RAILWAY_API_KEY is not configured in the environment"
    assert len(key) > 0, "RAILWAY_API_KEY is empty"
    
    # Test that the search falls back successfully to mock data even if the API key fails/is unsubscribed
    res = search_train(source="SBC", destination="NDLS", date="2026-06-21")
    assert res["status"] == "success"
    assert len(res["trains"]) > 0
    assert res["trains"][0]["train_no"] == "12627"
