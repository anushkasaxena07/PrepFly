import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.gemini import get_api_key_pool, ResilientInterviewAIModel
from langchain_core.messages import HumanMessage

class TestBackupAPIFailover(unittest.TestCase):
    def test_api_key_pool_assembly(self):
        keys = get_api_key_pool()
        self.assertIsInstance(keys, list)
        self.assertGreaterEqual(len(keys), 1)
        print("\n--- AI API Key Pool Verification ---")
        print(f"Total Configured API Keys: {len(keys)}")
        print(f"Primary Key Sample      : '{keys[0][:10]}...'")
        print("------------------------------------\n")

    def test_key_failover_mechanism(self):
        # Create resilient model with an invalid primary key first, followed by valid key
        valid_key = os.getenv("GEMINI_API_KEY", "AIzaSyBYSdXjmLnimrFY7ujWfRDIwyk_8cm9Ywo")
        
        # Override get_api_key_pool for this test to inject an invalid primary key
        import services.gemini as gemini_mod
        original_pool = gemini_mod.get_api_key_pool
        gemini_mod.get_api_key_pool = lambda: ["INVALID_PRIMARY_KEY_12345", valid_key]
        
        try:
            model = ResilientInterviewAIModel(model_candidates=["gemini-2.0-flash"])
            res = model.invoke([HumanMessage(content="Respond with 'FAILOVER SUCCESSFUL'")])
            self.assertIsNotNone(res)
            self.assertIn("FAILOVER SUCCESSFUL", res.content.upper())
            print(f"Failover Test Output: '{res.content.strip()}'")
        finally:
            gemini_mod.get_api_key_pool = original_pool

if __name__ == '__main__':
    unittest.main()
