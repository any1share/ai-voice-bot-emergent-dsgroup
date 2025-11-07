import requests
import sys
import json
from datetime import datetime

class VoiceBotAPITester:
    def __init__(self, base_url="https://order-voice-agent.preview.emergentagat.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_agent_id = None

    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        
        result = {
            "test": test_name,
            "status": "PASSED" if passed else "FAILED",
            "details": details
        }
        self.test_results.append(result)
        
        status_icon = "✅" if passed else "❌"
        print(f"\n{status_icon} {test_name}")
        if details:
            print(f"   {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            
            if success:
                self.log_result(name, True, f"Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.log_result(name, False, f"Expected {expected_status}, got {response.status_code}. Response: {response.text[:200]}")
                return False, {}

        except requests.exceptions.Timeout:
            self.log_result(name, False, "Request timeout")
            return False, {}
        except requests.exceptions.ConnectionError:
            self.log_result(name, False, "Connection error - backend may be down")
            return False, {}
        except Exception as e:
            self.log_result(name, False, f"Error: {str(e)}")
            return False, {}

    def test_get_agents(self):
        """Test GET /api/agents endpoint"""
        success, response = self.run_test(
            "GET /api/agents - Fetch all agents",
            "GET",
            "agents",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} agent(s)")
            if len(response) > 0:
                # Check if default Order Taking Agent exists
                order_agent = next((a for a in response if a.get('name') == 'Order Taking Agent'), None)
                if order_agent:
                    print(f"   ✓ Default 'Order Taking Agent' found")
                    print(f"   ✓ Language: {order_agent.get('language', 'N/A')}")
                    print(f"   ✓ Description: {order_agent.get('description', 'N/A')[:50]}...")
                    self.created_agent_id = order_agent.get('id')
                else:
                    print(f"   ⚠ Default 'Order Taking Agent' not found")
        
        return success

    def test_get_specific_agent(self):
        """Test GET /api/agents/{agent_id} endpoint"""
        if not self.created_agent_id:
            self.log_result("GET /api/agents/{agent_id} - Get specific agent", False, "No agent ID available")
            return False
        
        success, response = self.run_test(
            "GET /api/agents/{agent_id} - Get specific agent",
            "GET",
            f"agents/{self.created_agent_id}",
            200
        )
        
        if success:
            print(f"   Agent Name: {response.get('name', 'N/A')}")
            print(f"   Language: {response.get('language', 'N/A')}")
        
        return success

    def test_create_agent(self):
        """Test POST /api/agents endpoint"""
        test_agent_data = {
            "name": "Test Agent",
            "description": "Test agent for automated testing",
            "system_prompt": "You are a test agent.",
            "language": "english"
        }
        
        success, response = self.run_test(
            "POST /api/agents - Create new agent",
            "POST",
            "agents",
            200,
            data=test_agent_data
        )
        
        if success and response.get('id'):
            self.created_agent_id = response['id']
            print(f"   Created agent ID: {self.created_agent_id}")
        
        return success

    def test_update_agent(self):
        """Test PUT /api/agents/{agent_id} endpoint"""
        if not self.created_agent_id:
            self.log_result("PUT /api/agents/{agent_id} - Update agent", False, "No agent ID available")
            return False
        
        update_data = {
            "description": "Updated test agent description"
        }
        
        success, response = self.run_test(
            "PUT /api/agents/{agent_id} - Update agent",
            "PUT",
            f"agents/{self.created_agent_id}",
            200,
            data=update_data
        )
        
        return success

    def test_chat_endpoint(self):
        """Test POST /api/chat endpoint with Gemini"""
        if not self.created_agent_id:
            self.log_result("POST /api/chat - Chat with agent", False, "No agent ID available")
            return False
        
        chat_data = {
            "agent_id": self.created_agent_id,
            "message": "नमस्ते, मुझे एक पिज्जा ऑर्डर करना है"
        }
        
        print(f"\n🔍 Testing POST /api/chat - Chat with agent (Gemini 2.0 Flash)")
        print(f"   Sending Hindi message: {chat_data['message']}")
        print(f"   This may take a few seconds for LLM response...")
        
        success, response = self.run_test(
            "POST /api/chat - Chat with agent (Gemini)",
            "POST",
            "chat",
            200,
            data=chat_data
        )
        
        if success:
            chat_response = response.get('response', '')
            session_id = response.get('session_id', '')
            print(f"   Response received: {chat_response[:100]}...")
            print(f"   Session ID: {session_id}")
            
            # Check if response is in Hindi or contains Hindi characters
            if any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in chat_response):
                print(f"   ✓ Response contains Hindi characters")
        
        return success

    def test_delete_agent(self):
        """Test DELETE /api/agents/{agent_id} endpoint"""
        if not self.created_agent_id:
            self.log_result("DELETE /api/agents/{agent_id} - Delete agent", False, "No agent ID available")
            return False
        
        success, response = self.run_test(
            "DELETE /api/agents/{agent_id} - Delete agent",
            "DELETE",
            f"agents/{self.created_agent_id}",
            200
        )
        
        return success

    def test_realtime_session(self):
        """Test POST /api/realtime/session endpoint"""
        success, response = self.run_test(
            "POST /api/realtime/session - Get WebRTC session token",
            "POST",
            "realtime/session",
            200,
            data={}
        )
        
        if success:
            if response.get('client_secret', {}).get('value'):
                print(f"   ✓ Session token received")
            else:
                print(f"   ⚠ Session token not found in response")
        
        return success

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print("="*60)
        
        if self.tests_run - self.tests_passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result['status'] == 'FAILED':
                    print(f"  - {result['test']}: {result['details']}")

def main():
    print("="*60)
    print("🚀 VOICE BOT API TESTING")
    print("="*60)
    print(f"Backend URL: https://order-voice-agent.preview.emergentagent.com/api")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    tester = VoiceBotAPITester()

    # Run tests in sequence
    print("\n📋 TESTING AGENT MANAGEMENT ENDPOINTS")
    print("-" * 60)
    
    # Test getting agents (should have default Order Taking Agent)
    tester.test_get_agents()
    
    # Test getting specific agent
    tester.test_get_specific_agent()
    
    # Test creating a new agent
    tester.test_create_agent()
    
    # Test updating agent
    tester.test_update_agent()
    
    # Test chat endpoint with Gemini
    print("\n📋 TESTING CHAT ENDPOINT (GEMINI 2.0 FLASH)")
    print("-" * 60)
    tester.test_chat_endpoint()
    
    # Test realtime session endpoint
    print("\n📋 TESTING VOICE/REALTIME ENDPOINTS")
    print("-" * 60)
    tester.test_realtime_session()
    
    # Test deleting agent
    print("\n📋 TESTING DELETE ENDPOINT")
    print("-" * 60)
    tester.test_delete_agent()

    # Print summary
    tester.print_summary()

    # Return exit code
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
