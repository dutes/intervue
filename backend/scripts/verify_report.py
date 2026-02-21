import json
from server.core import reports

def test_report_generation():
    # Dummy session data
    session_data = {
        "session_id": "test_session_123",
        "provider": "mock", # Use mock to avoid API costs during quick test, or 'openai' if you want real test
        "job_spec": "Senior Python Developer",
        "persona": {
            "name": "Jane Doe",
            "role": "CTO",
            "tone": "Direct",
            "key_concerns": ["Scalability"]
        },
        "questions": [
            {"question_id": "q1", "text": "How do you handle memory leaks?", "round": "Technical", "persona": "Jane Doe"}
        ],
        "answers": [
            {"answer_text": "I use profilers and check for reference cycles."}
        ],
        "scores": [
            {
                "question_id": "q1",
                "persona": "positive",
                "scorecard": {"competency_scores": {"Technical": 4}},
                "overall_score": 90
            },
            {
                "question_id": "q1",
                "persona": "neutral",
                "scorecard": {"competency_scores": {"Technical": 3}},
                "overall_score": 75
            },
             {
                "question_id": "q1",
                "persona": "hostile",
                "scorecard": {"competency_scores": {"Technical": 2}},
                "overall_score": 50
            }
        ]
    }

    print("Generating report...")
    try:
        report, paths = reports.build_report(session_data)
        print("Report Generated Successfully!")
        print(json.dumps(report, indent=2))
        print("Paths:", paths)
    except Exception as e:
        print(f"Failed to generate report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_report_generation()
