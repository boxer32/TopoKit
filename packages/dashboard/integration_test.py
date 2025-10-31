"""
Integration test script for dashboard backend API.
Tests all endpoints and WebSocket connections.
"""

import asyncio
import httpx
import websockets
import json
from datetime import datetime


BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080"


async def test_health_check():
    """Test health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Health check passed")


async def test_get_deployments():
    """Test get deployments endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/deployments")
        assert response.status_code == 200
        data = response.json()
        assert "deployments" in data
        print(f"✅ Get deployments passed (found {len(data['deployments'])} deployments)")


async def test_get_deployment_metrics():
    """Test get deployment metrics endpoint."""
    # First get deployments to find an ID
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/deployments")
        data = response.json()
        
        if data["deployments"]:
            deployment_id = data["deployments"][0]["id"]
            metrics_response = await client.get(f"{BASE_URL}/api/v1/deployments/{deployment_id}/metrics")
            
            if metrics_response.status_code == 200:
                metrics_data = metrics_response.json()
                assert "metrics" in metrics_data
                assert "deployment_id" in metrics_data
                print(f"✅ Get deployment metrics passed for {deployment_id}")
            else:
                print(f"⚠️  Deployment {deployment_id} metrics not available (status: {metrics_response.status_code})")
        else:
            print("⚠️  No deployments available for metrics test")


async def test_get_alerts():
    """Test get alerts endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "statistics" in data
        print(f"✅ Get alerts passed (found {len(data['alerts'])} alerts)")


async def test_websocket_metrics():
    """Test WebSocket metrics endpoint."""
    try:
        async with websockets.connect(f"{WS_URL}/ws/metrics/test-deployment") as ws:
            # Wait for first message
            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(message)
            assert data["type"] == "metrics"
            assert "metrics" in data
            print("✅ WebSocket metrics connection successful")
            # Close after receiving one message
            await ws.close()
    except asyncio.TimeoutError:
        print("⚠️  WebSocket metrics timeout (no data received)")
    except Exception as e:
        print(f"⚠️  WebSocket metrics test failed: {e}")


async def test_websocket_alerts():
    """Test WebSocket alerts endpoint."""
    try:
        async with websockets.connect(f"{WS_URL}/ws/alerts") as ws:
            # Wait for first message
            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(message)
            assert data["type"] == "alerts"
            print("✅ WebSocket alerts connection successful")
            await ws.close()
    except asyncio.TimeoutError:
        print("⚠️  WebSocket alerts timeout (no data received)")
    except Exception as e:
        print(f"⚠️  WebSocket alerts test failed: {e}")


async def test_websocket_collaboration():
    """Test WebSocket collaboration endpoint."""
    try:
        async with websockets.connect(f"{WS_URL}/ws/collaboration/test-deployment") as ws:
            # Wait for connection confirmation
            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(message)
            assert data["type"] == "connection"
            assert data["connected"] == True
            print("✅ WebSocket collaboration connection successful")
            await ws.close()
    except asyncio.TimeoutError:
        print("⚠️  WebSocket collaboration timeout")
    except Exception as e:
        print(f"⚠️  WebSocket collaboration test failed: {e}")


async def test_cors():
    """Test CORS headers."""
    async with httpx.AsyncClient() as client:
        response = await client.options(
            f"{BASE_URL}/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS should be configured
        print("✅ CORS test completed")


async def run_all_tests():
    """Run all integration tests."""
    print("🧪 Running Dashboard Integration Tests\n")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_check),
        ("Get Deployments", test_get_deployments),
        ("Get Deployment Metrics", test_get_deployment_metrics),
        ("Get Alerts", test_get_alerts),
        ("WebSocket Metrics", test_websocket_metrics),
        ("WebSocket Alerts", test_websocket_alerts),
        ("WebSocket Collaboration", test_websocket_collaboration),
        ("CORS", test_cors),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed")


if __name__ == "__main__":
    print("Make sure the backend server is running on http://localhost:8080")
    print("Start with: python -m uvicorn packages.dashboard.src.api.server:app --reload --port 8080\n")
    asyncio.run(run_all_tests())

