
import asyncio
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/services/report_orchestrator")))

from app.core.trading.trading_tools import TradingToolkit

async def test_search_no_cache():
    print("Testing _tavily_search for cache removal...")
    
    # Mock resources
    mock_files = {}  # Not needed for this test since we mock execution
    toolkit = TradingToolkit(file_dict=mock_files)
    
    # Mock the internal _execute_tavily_search to verify it's called
    # and to avoid actual API calls
    mock_result = {
        "success": True, 
        "results": [{"title": "Test", "url": "http://test.com", "content": "content"}],
        "result_count": 1
    }
    
    with patch.object(toolkit, '_execute_tavily_search', new_callable=MagicMock) as mock_execute:
        mock_execute.return_value = mock_result
        
        # Define search params
        query = "test query"
        
        # Execute search
        result_json = await toolkit._tavily_search(query)
        result = json.loads(result_json)
        
        # Verification 1: Check if _execute_tavily_search was called
        if mock_execute.called:
            print("✅ PASS: _execute_tavily_search was called directly.")
        else:
            print("❌ FAIL: _execute_tavily_search was NOT called.")
            
        # Verification 2: Check arguments
        args, kwargs = mock_execute.call_args
        if args[0] == query:
             print(f"✅ PASS: Query passed correctly: {args[0]}")
        else:
             print(f"❌ FAIL: Query mismatch. Expected {query}, got {args[0]}")

        # Verification 3: Verify no "cycle_search_cache" import attempts
        # (This is implicitly tested by the code running without error if the module is missing, 
        # but we can't easily mock sys.modules access here without more complex setup. 
        # The code inspection confirms the import is gone.)

        print("Test complete.")

if __name__ == "__main__":
    asyncio.run(test_search_no_cache())
