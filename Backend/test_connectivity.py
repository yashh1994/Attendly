import requests
import json

# Test server connectivity
base_url = "http://localhost:5000"

print("🔍 Testing server connectivity...")

try:
    # Test health endpoint
    response = requests.get(f"{base_url}/health", timeout=5)
    print(f"✅ Health check: {response.status_code} - {response.text[:100]}")
except Exception as e:
    print(f"❌ Health check failed: {e}")

try:
    # Test if server is running at all
    response = requests.get(base_url, timeout=5)
    print(f"✅ Server root: {response.status_code}")
except Exception as e:
    print(f"❌ Server not responding: {e}")

# Test the specific route we're having issues with
print("\n🔍 Testing face-data routes...")

try:
    # This should give 401 without authentication, not 404
    response = requests.post(f"{base_url}/api/face-data/register-student", 
                           json={"test": "data"}, 
                           timeout=5)
    print(f"✅ Face data route exists: {response.status_code} - {response.text[:100]}")
except Exception as e:
    print(f"❌ Face data route test failed: {e}")

print("\n🔍 All registered routes (if server is running):")
try:
    response = requests.get(f"{base_url}/routes", timeout=5)
    if response.status_code == 200:
        print(response.text)
    else:
        print("No /routes endpoint available")
except:
    print("Cannot fetch routes")