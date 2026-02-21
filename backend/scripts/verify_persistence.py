import requests
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

def test_list_sessions():
    print("Testing GET /sessions...")
    try:
        res = requests.get(f"{BASE_URL}/sessions")
        if res.status_code != 200:
            print(f"FAILED: Status {res.status_code}")
            print(res.text)
            return False
        
        sessions = res.json()
        print(f"Success! Found {len(sessions)} sessions.")
        for s in sessions[:3]:
            print(f" - {s['session_id']} ({s['status']}) Score: {s.get('overall_score')}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def test_create_and_retrieve():
    print("\nTesting Session Creation & Persistence...")
    try:
        # Create
        payload = {
            "job_spec": "Software Engineer. Python, FastAPI, React.",
            "cv_text": "Experienced Python developer with 5 years in backend dev.",
            "provider": "mock",
            "start_round": 1
        }
        res = requests.post(f"{BASE_URL}/sessions/start", json=payload)
        if res.status_code != 200:
            print(f"FAILED to start session: {res.text}")
            return False
        
        data = res.json()
        session_id = data["session_id"]
        print(f"Created session: {session_id}")
        
        # Verify it appears in list
        res_list = requests.get(f"{BASE_URL}/sessions")
        sessions = res_list.json()
        if not any(s['session_id'] == session_id for s in sessions):
            print("FAILED: New session not found in list!")
            return False
        
        print("Success: Session persisted and listed.")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    print("Waiting for server...")
    time.sleep(5) 
    
    if test_list_sessions():
        if test_create_and_retrieve():
            print("\nALL PERSISTENCE TESTS PASSED")
            sys.exit(0)
    
    sys.exit(1)
