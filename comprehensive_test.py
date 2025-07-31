#!/usr/bin/env python3
"""
Comprehensive test script for Video Downloader API
"""
import requests
import json
import time

BASE_URL = "http://localhost:8888"


def test_health_check():
    """Test health check endpoint"""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"✅ Health check: {response.status_code} - {response.json()}")
    return response.status_code == 200


def test_root_endpoint():
    """Test root endpoint"""
    print("🔍 Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"✅ Root endpoint: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_download_workflow():
    """Test complete download workflow"""
    print("🔍 Testing video download workflow...")

    # Step 1: Initiate download
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Me at the zoo (first YouTube video)
    download_request = {"url": test_url, "quality": "480p"}

    print(f"📥 Initiating download for: {test_url}")
    response = requests.post(
        f"{BASE_URL}/download",
        json=download_request,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        print(f"❌ Download initiation failed: {response.status_code}")
        print(f"Error: {response.text}")
        return False

    result = response.json()
    task_id = result["task_id"]
    print(f"✅ Download initiated - Task ID: {task_id}")
    print(f"Message: {result['message']}")

    # Step 2: Poll for completion
    print("⏳ Polling for completion...")
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        status_response = requests.get(f"{BASE_URL}/status/{task_id}")
        if status_response.status_code != 200:
            print(f"❌ Status check failed: {status_response.status_code}")
            return False

        status_data = status_response.json()
        print(
            f"Status check {attempt + 1}: {status_data['status']} - {status_data['message']}"
        )

        if status_data["status"] == "completed":
            print("🎉 Download completed!")
            print("\n📋 Video Information:")
            print(f"  Title: {status_data.get('title')}")
            print(f"  Duration: {status_data.get('duration')} seconds")
            print(f"  Format: {status_data.get('format')}")
            print(f"  Thumbnail: {status_data.get('thumbnail')}")
            print(f"  Video URL: {status_data.get('url')[:100]}...")
            print(f"  Filename: {status_data.get('filename')}")

            # Step 3: Test file download
            print("\n📁 Testing file download...")
            download_response = requests.get(
                f"{BASE_URL}/download/{task_id}", stream=True
            )
            if download_response.status_code == 200:
                content_length = download_response.headers.get(
                    "content-length", "unknown"
                )
                content_type = download_response.headers.get("content-type", "unknown")
                print(
                    f"✅ File download ready - Size: {content_length} bytes, Type: {content_type}"
                )
            else:
                print(f"❌ File download failed: {download_response.status_code}")

            return True

        elif status_data["status"] == "failed":
            print(f"❌ Download failed: {status_data['message']}")
            return False

        attempt += 1
        if attempt < max_attempts:
            time.sleep(10)  # Wait 10 seconds between checks

    print("⏰ Download timeout")
    return False


def main():
    """Run comprehensive tests"""
    print("🚀 Starting Comprehensive Video Downloader API Tests")
    print("=" * 60)

    tests = [
        ("Health Check", test_health_check),
        ("Root Endpoint", test_root_endpoint),
        ("Download Workflow", test_download_workflow),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n🏁 Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The API is working perfectly!")
    else:
        print("⚠️  Some tests failed. Please check the logs above.")


if __name__ == "__main__":
    main()
