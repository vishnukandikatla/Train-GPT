import pytest
import os
import requests
from unittest.mock import MagicMock
from backend.services.railway_provider import RailwayProvider
from backend.services.railway_service import RailwayService
from backend.database.mongodb import init_db

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    import asyncio
    asyncio.run(init_db())

def test_live_search(monkeypatch):
    """
    Test live train search:
    - Case A: Success from primary provider.
    - Case B: Failover from primary (429) to secondary (200).
    - Case C: Complete failure/timeout on all providers, falling back to mock search.
    """
    # Case A: Success from primary host (irctc1.p.rapidapi.com)
    def mock_get_success(url, headers, params, timeout):
        host = headers.get("x-rapidapi-host")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "train_number": "12724",
                    "train_name": "Telangana Express",
                    "from_station": "PDPL",
                    "to_station": "SC",
                    "from_std": "09:00",
                    "to_std": "14:00",
                    "duration": "05h 00m",
                    "run_days": ["Daily"]
                }
            ]
        }
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_success)
    monkeypatch.setenv("RAILWAY_API_KEY", "test-key-123")
    
    results = RailwayProvider.search_trains(source="PDPL", destination="SC", date="2026-06-24")
    assert len(results) > 0
    assert results[0]["train_no"] == "12724"
    assert results[0]["data_source"] == "live"

    # Case B: Rate-limit 429 on primary host, success on secondary host (indian-railway-irctc.p.rapidapi.com)
    def mock_get_failover(url, headers, params, timeout):
        host = headers.get("x-rapidapi-host")
        mock_response = MagicMock()
        if "irctc1" in host:
            mock_response.status_code = 429
        else:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "trains": [
                    {
                        "trainNo": "12724",
                        "trainName": "Telangana Exp",
                        "source": "PDPL",
                        "destination": "SC",
                        "departureTime": "09:00",
                        "arrivalTime": "14:00",
                        "travel_time": "05h 00m",
                        "runs_on": ["Daily"]
                    }
                ]
            }
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_failover)
    results = RailwayProvider.search_trains(source="PDPL", destination="SC", date="2026-06-24")
    assert len(results) > 0
    assert results[0]["train_no"] == "12724"
    assert results[0]["data_source"] == "live"

    # Case C: All providers fail/timeout, falling back to mock search
    def mock_get_all_fail(url, headers, params, timeout):
        raise requests.Timeout("Connection timed out")

    monkeypatch.setattr(requests, "get", mock_get_all_fail)
    results = RailwayProvider.search_trains(source="PDPL", destination="SC", date="2026-06-24")
    assert len(results) > 0
    # Mock fallback returns trains matching PDPL to SC
    assert results[0]["data_source"] == "mock"


def test_live_availability(monkeypatch):
    """
    Test seat availability:
    - Case A: Success from primary provider.
    - Case B: Failover from primary (429) to secondary (200).
    - Case C: Complete failure, falling back to mock availability.
    """
    # Case A: Success on primary host (indian-railway-seat-availability.p.rapidapi.com)
    def mock_get_success(url, headers, params, timeout):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "available_seats": 25,
            "seat_status": "AVAILABLE"
        }
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_success)
    monkeypatch.setenv("RAILWAY_API_KEY", "test-key-123")
    
    res = RailwayProvider.check_availability(train_no="12724", class_type="SL", date="2026-06-24")
    assert res["status"] == "success"
    assert res["available_seats"] == 25
    assert res["seat_status"] == "AVAILABLE"
    assert res["data_source"] == "live"

    # Case B: Rate-limit 429 on primary host, success on secondary host (rail-info-api-indial.p.rapidapi.com)
    def mock_get_failover(url, headers, params, timeout):
        host = headers.get("x-rapidapi-host")
        mock_response = MagicMock()
        if "seat-availability" in host:
            mock_response.status_code = 429
        else:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "available": 15,
                "status": "AVAILABLE"
            }
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_failover)
    res = RailwayProvider.check_availability(train_no="12724", class_type="SL", date="2026-06-24")
    assert res["status"] == "success"
    assert res["available_seats"] == 15
    assert res["data_source"] == "live"

    # Case C: All providers fail, falling back to mock availability
    def mock_get_all_fail(url, headers, params, timeout):
        mock_response = MagicMock()
        mock_response.status_code = 500
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_all_fail)
    res = RailwayProvider.check_availability(train_no="12724", class_type="SL", date="2026-06-24")
    assert res["status"] == "success"
    assert res["data_source"] == "mock"


def test_live_pnr(monkeypatch):
    """
    Test live PNR status:
    - Case A: Success from PNR provider.
    - Case B: Complete API failure, falling back to mock/database records.
    """
    # Case A: Success on primary host (irctc-indian-railway-pnr-status.p.rapidapi.com)
    def mock_get_success(url, headers, params, timeout):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "train_no": "12724",
                "train_name": "Telangana Express",
                "source": "PDPL",
                "destination": "HYB",
                "journey_date": "2026-06-24",
                "class_type": "SL",
                "booking_status": "Confirmed",
                "passengers": [
                    {
                        "name": "Rajesh",
                        "age": 28,
                        "gender": "Male",
                        "seat_no": "S1/14"
                    }
                ]
            }
        }
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_success)
    monkeypatch.setenv("RAILWAY_API_KEY", "test-key-123")

    res = RailwayProvider.get_pnr_status("1234567890")
    assert res["status"] == "success"
    assert res["train_no"] == "12724"
    assert res["booking_status"] == "Confirmed"
    assert len(res["passengers"]) == 1
    assert res["passengers"][0]["name"] == "Rajesh"
    assert res["data_source"] == "live"

    # Case B: All PNR API providers fail/rate-limit. Should return failure dict from RailwayProvider.get_pnr_status.
    def mock_get_fail(url, headers, params, timeout):
        mock_response = MagicMock()
        mock_response.status_code = 429
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_fail)
    res = RailwayProvider.get_pnr_status("1234567890")
    assert res["status"] == "error"
    assert "failed" in res["message"]


@pytest.mark.asyncio
async def test_live_pnr_service_fallback(monkeypatch):
    """
    Test PNR service fallback in RailwayService.check_pnr:
    If live APIs fail, it must fall back to local MongoDB bookings.
    """
    # Mock PNR API failure
    def mock_get_fail(url, headers, params, timeout):
        mock_response = MagicMock()
        mock_response.status_code = 500
        return mock_response
    monkeypatch.setattr(requests, "get", mock_get_fail)
    monkeypatch.setenv("RAILWAY_API_KEY", "test-key-123")

    # Create a local booking first
    passengers = [{"name": "Sneha", "age": 26, "gender": "Female"}]
    book_res = await RailwayService.book_ticket(
        user_id="test_runner",
        train_no="12724",
        journey_date="2026-06-24",
        class_type="SL",
        passengers=passengers
    )
    assert book_res["status"] == "success"
    pnr = book_res["pnr"]

    # Now verify that check_pnr returns the booked details from MongoDB (data_source: mock)
    res = await RailwayService.check_pnr(pnr)
    assert res["status"] == "success"
    assert res["pnr"] == pnr
    assert res["train_no"] == "12724"
    assert res["data_source"] == "mock"
    assert res["passengers"][0]["name"] == "Sneha"


def test_live_running_status(monkeypatch):
    """
    Test live train running status:
    - Case A: Success from primary provider.
    - Case B: Failure/429 on provider, falling back to mock running status.
    """
    # Case A: Success on primary host (train-running-api.p.rapidapi.com)
    def mock_get_success(url, headers, params, timeout):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current_station": "PDPL",
            "delay": 12,
            "status": "Running late by 12 mins"
        }
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_success)
    monkeypatch.setenv("RAILWAY_API_KEY", "test-key-123")

    res = RailwayProvider.get_running_status("12724")
    assert res["status"] == "success"
    assert res["current_station"] == "PDPL"
    assert res["delay_minutes"] == 12
    assert res["data_source"] == "live"

    # Case B: Failure on provider, falling back to mock
    def mock_get_fail(url, headers, params, timeout):
        mock_response = MagicMock()
        mock_response.status_code = 429
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get_fail)
    res = RailwayProvider.get_running_status("12724")
    assert res["status"] == "success"
    assert res["data_source"] == "mock"
    assert "Mock Data" in res["message"]
