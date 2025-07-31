#!/usr/bin/env python3
"""
Test script for Video Downloader API
"""
import asyncio
import httpx
import time
import json

BASE_URL = "http://localhost:8000"

async def test_api():
    """Test the video downloader API"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🚀 Testing Video Downloader API")
        print("=" * 50)
        
        # Test 1: Health check
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Health check: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # Test 2: Root endpoint
        print("\n2. Testing root endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"✅ Root endpoint: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Root endpoint failed: {e}")
        
        # Test 3: Initiate download
        print("\n3. Testing video download initiation...")
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
        
        try:
            download_request = {
                "url": test_url
            }
            response = await client.post(
                f"{BASE_URL}/download",
                json=download_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result["task_id"]
                print(f"✅ Download initiated: {response.status_code}")
                print(f"Task ID: {task_id}")
                print(f"Message: {result['message']}")
                
                # Test 4: Status polling
                print("\n4. Polling download status...")
                max_attempts = 30  # Wait up to 5 minutes
                attempt = 0
                
                while attempt < max_attempts:
                    try:
                        status_response = await client.get(f"{BASE_URL}/status/{task_id}")
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"Status check {attempt + 1}: {status_data['status']} - {status_data['message']}")
                            
                            if status_data['status'] == 'completed':
                                print(f"✅ Download completed!")
                                print(f"Download URL: {status_data.get('download_url')}")
                                print(f"Filename: {status_data.get('filename')}")
                                
                                # Test 5: File download
                                print("\n5. Testing file download...")
                                try:
                                    download_response = await client.get(f"{BASE_URL}/download/{task_id}")
                                    if download_response.status_code == 200:
                                        print(f"✅ File download successful: {len(download_response.content)} bytes")
                                        content_type = download_response.headers.get('content-type', 'unknown')
                                        print(f"Content type: {content_type}")
                                    else:
                                        print(f"❌ File download failed: {download_response.status_code}")
                                except Exception as e:
                                    print(f"❌ File download error: {e}")
                                
                                break
                                
                            elif status_data['status'] == 'failed':
                                print(f"❌ Download failed: {status_data['message']}")
                                break
                            
                            attempt += 1
                            if attempt < max_attempts:
                                await asyncio.sleep(10)  # Wait 10 seconds between checks
                        else:
                            print(f"❌ Status check failed: {status_response.status_code}")
                            break
                            
                    except Exception as e:
                        print(f"❌ Status check error: {e}")
                        break
                
                if attempt >= max_attempts:
                    print("⏰ Download timeout - check manually")
                    
            else:
                print(f"❌ Download initiation failed: {response.status_code}")
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Download test failed: {e}")
        
        print("\n🏁 Test completed!")

if __name__ == "__main__":
    print("Make sure the API server is running on http://localhost:8000")
    print("Start it with: python main.py")
    input("Press Enter to continue with tests...")
    
    asyncio.run(test_api())
