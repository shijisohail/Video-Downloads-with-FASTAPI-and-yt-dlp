#!/usr/bin/env python3
"""
Comprehensive test script for Video Downloader API
Tests all endpoints with the remote server at http://3.19.120.236:8888/
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# Server configuration
BASE_URL = "http://3.19.120.236:8888"

# Test configurations
TEST_VIDEOS = {
    "youtube_short": {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "description": "YouTube - Rick Astley - Never Gonna Give You Up",
        "quality": "720p",
        "download_type": "single"
    },
    "youtube_playlist": {
        "url": "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMfz74RrUUUBYy0BG9",
        "description": "YouTube Playlist (small)",
        "quality": "480p",
        "download_type": "playlist"
    }
}

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
        
    def print_section(self, title: str):
        """Print a formatted section header"""
        print(f"\n{'='*60}")
        print(f" {title}")
        print('='*60)
    
    def print_test(self, test_name: str):
        """Print a formatted test header"""
        print(f"\n--- {test_name} ---")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request and return formatted response"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"🔄 {method.upper()} {url}")
            if 'json' in kwargs:
                print(f"📤 Request Body: {json.dumps(kwargs['json'], indent=2)}")
            
            response = self.session.request(method, url, **kwargs)
            
            print(f"📊 Status Code: {response.status_code}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                print(f"📥 Response: {json.dumps(response_data, indent=2)}")
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "data": response_data,
                    "headers": dict(response.headers)
                }
            except json.JSONDecodeError:
                print(f"📥 Response (text): {response.text}")
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "data": response.text,
                    "headers": dict(response.headers)
                }
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": None,
                "data": None
            }
    
    def test_root_endpoint(self):
        """Test GET / - API information"""
        self.print_test("Root Endpoint - GET /")
        return self.make_request("GET", "/")
    
    def test_health_endpoint(self):
        """Test GET /health - Health check"""
        self.print_test("Health Check - GET /health")
        return self.make_request("GET", "/health")
    
    def test_download_initiation(self, video_config: Dict[str, str]):
        """Test POST /download - Initiate download"""
        self.print_test(f"Download Initiation - {video_config['description']}")
        
        payload = {
            "url": video_config["url"],
            "quality": video_config["quality"],
            "download_type": video_config["download_type"]
        }
        
        return self.make_request("POST", "/download", json=payload)
    
    def test_status_check(self, task_id: str, description: str = ""):
        """Test GET /status/{task_id} - Check download status"""
        self.print_test(f"Status Check{' - ' + description if description else ''}")
        return self.make_request("GET", f"/status/{task_id}")
    
    def test_file_download(self, task_id: str, description: str = ""):
        """Test GET /download/{task_id} - Download file"""
        self.print_test(f"File Download{' - ' + description if description else ''}")
        
        # For file downloads, we don't want to actually download the entire file
        # Just check if the endpoint responds correctly
        try:
            url = f"{self.base_url}/download/{task_id}"
            print(f"🔄 HEAD {url}")
            
            response = self.session.head(url, timeout=10)
            print(f"📊 Status Code: {response.status_code}")
            print(f"📥 Headers: {json.dumps(dict(response.headers), indent=2)}")
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": None
            }
    
    def test_invalid_endpoints(self):
        """Test various invalid endpoints for error handling"""
        self.print_section("Error Handling Tests")
        
        # Test invalid task ID for status
        self.print_test("Invalid Task ID - Status Check")
        invalid_task_result = self.make_request("GET", "/status/invalid-task-id")
        
        # Test invalid task ID for download
        self.print_test("Invalid Task ID - File Download")
        invalid_download_result = self.make_request("GET", "/download/invalid-task-id")
        
        # Test invalid URL for download initiation
        self.print_test("Invalid URL - Download Initiation")
        invalid_url_result = self.make_request("POST", "/download", json={
            "url": "not-a-valid-url",
            "quality": "720p",
            "download_type": "single"
        })
        
        # Test unsupported platform
        self.print_test("Unsupported Platform - Download Initiation")
        unsupported_platform_result = self.make_request("POST", "/download", json={
            "url": "https://example.com/video",
            "quality": "720p", 
            "download_type": "single"
        })
        
        return {
            "invalid_task_status": invalid_task_result,
            "invalid_task_download": invalid_download_result,
            "invalid_url": invalid_url_result,
            "unsupported_platform": unsupported_platform_result
        }
    
    def wait_for_completion(self, task_id: str, max_wait_time: int = 300, description: str = ""):
        """Wait for download to complete and check status periodically"""
        print(f"\n⏳ Waiting for download completion{' - ' + description if description else ''}...")
        print(f"🔄 Task ID: {task_id}")
        print(f"⏰ Max wait time: {max_wait_time} seconds")
        
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        while time.time() - start_time < max_wait_time:
            status_result = self.test_status_check(task_id, f"Polling ({int(time.time() - start_time)}s)")
            
            if not status_result["success"]:
                print("❌ Failed to get status")
                return False
            
            status = status_result["data"].get("status")
            print(f"📊 Current status: {status}")
            
            if status == "completed":
                print("✅ Download completed!")
                return True
            elif status == "failed":
                print("❌ Download failed!")
                return False
            
            print(f"⏳ Still processing... waiting {check_interval} seconds")
            time.sleep(check_interval)
        
        print(f"⏰ Timeout reached ({max_wait_time}s)")
        return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print("🚀 Starting comprehensive API test suite")
        print(f"🌐 Base URL: {self.base_url}")
        
        results = {}
        
        # Test basic endpoints
        self.print_section("Basic Endpoint Tests")
        results["root"] = self.test_root_endpoint()
        results["health"] = self.test_health_endpoint()
        
        # Test error handling
        results["error_handling"] = self.test_invalid_endpoints()
        
        # Test download workflow
        self.print_section("Download Workflow Tests")
        
        for test_name, video_config in TEST_VIDEOS.items():
            self.print_section(f"Testing: {video_config['description']}")
            
            # Step 1: Initiate download
            download_result = self.test_download_initiation(video_config)
            results[f"{test_name}_initiate"] = download_result
            
            if download_result["success"] and "task_id" in download_result["data"]:
                task_id = download_result["data"]["task_id"]
                
                # Step 2: Check initial status
                initial_status = self.test_status_check(task_id, "Initial Status")
                results[f"{test_name}_initial_status"] = initial_status
                
                # Step 3: Wait for completion (shorter timeout for tests)
                if self.wait_for_completion(task_id, max_wait_time=120, description=video_config['description']):
                    # Step 4: Check final status
                    final_status = self.test_status_check(task_id, "Final Status")
                    results[f"{test_name}_final_status"] = final_status
                    
                    # Step 5: Test file download
                    download_file_result = self.test_file_download(task_id, video_config['description'])
                    results[f"{test_name}_file_download"] = download_file_result
                else:
                    print(f"⚠️ Skipping file download test for {test_name} due to timeout or failure")
            else:
                print(f"⚠️ Skipping status and download tests for {test_name} due to initiation failure")
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test summary"""
        self.print_section("Test Summary")
        
        total_tests = 0
        passed_tests = 0
        
        def count_results(data, prefix=""):
            nonlocal total_tests, passed_tests
            
            for key, value in data.items():
                if isinstance(value, dict):
                    if "success" in value:
                        total_tests += 1
                        if value["success"]:
                            passed_tests += 1
                            print(f"✅ {prefix}{key}: PASS")
                        else:
                            print(f"❌ {prefix}{key}: FAIL")
                            if "error" in value:
                                print(f"   Error: {value['error']}")
                            elif "status_code" in value:
                                print(f"   Status Code: {value['status_code']}")
                    else:
                        count_results(value, f"{prefix}{key}.")
        
        count_results(results)
        
        print(f"\n📊 Test Results: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 Overall result: GOOD")
        elif success_rate >= 60:
            print("⚠️ Overall result: FAIR")
        else:
            print("❌ Overall result: NEEDS ATTENTION")

def main():
    """Main function"""
    print("🧪 Video Downloader API Test Suite")
    print(f"🎯 Target Server: {BASE_URL}")
    
    # Test server connectivity first
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Server is reachable")
        else:
            print(f"⚠️ Server returned status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach server: {e}")
        print("🛑 Aborting tests")
        sys.exit(1)
    
    # Initialize tester and run tests
    tester = APITester(BASE_URL)
    results = tester.run_comprehensive_test()
    tester.print_summary(results)

if __name__ == "__main__":
    main()
