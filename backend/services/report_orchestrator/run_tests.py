#!/usr/bin/env python3
"""
Standalone Test Runner

Tests the refactored modules: domain/, mocks/.
Skips parsers/ tests due to import chain issues (requires full app context).
"""

import sys
import os
import json
import unittest
import asyncio

# Add paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'app', 'core', 'trading'))


class TestVoteDirection(unittest.TestCase):
    """Tests for VoteDirection enum."""
    
    def test_direction_values(self):
        """Test direction enum values."""
        from domain.vote import VoteDirection
        
        self.assertEqual(VoteDirection.LONG.value, "long")
        self.assertEqual(VoteDirection.SHORT.value, "short")
        self.assertEqual(VoteDirection.HOLD.value, "hold")
        self.assertEqual(VoteDirection.CLOSE.value, "close")
    
    def test_from_string_long(self):
        """Test from_string for long variations."""
        from domain.vote import VoteDirection
        
        self.assertEqual(VoteDirection.from_string("long"), VoteDirection.LONG)
        self.assertEqual(VoteDirection.from_string("LONG"), VoteDirection.LONG)
        self.assertEqual(VoteDirection.from_string("做多"), VoteDirection.LONG)
        self.assertEqual(VoteDirection.from_string("buy"), VoteDirection.LONG)
        self.assertEqual(VoteDirection.from_string("bullish"), VoteDirection.LONG)
    
    def test_from_string_short(self):
        """Test from_string for short variations."""
        from domain.vote import VoteDirection
        
        self.assertEqual(VoteDirection.from_string("short"), VoteDirection.SHORT)
        self.assertEqual(VoteDirection.from_string("做空"), VoteDirection.SHORT)
        self.assertEqual(VoteDirection.from_string("sell"), VoteDirection.SHORT)
        self.assertEqual(VoteDirection.from_string("bearish"), VoteDirection.SHORT)
    
    def test_from_string_hold(self):
        """Test from_string for hold variations."""
        from domain.vote import VoteDirection
        
        self.assertEqual(VoteDirection.from_string("hold"), VoteDirection.HOLD)
        self.assertEqual(VoteDirection.from_string("观望"), VoteDirection.HOLD)
        self.assertEqual(VoteDirection.from_string("wait"), VoteDirection.HOLD)
    
    def test_from_string_invalid(self):
        """Test from_string with invalid input returns HOLD."""
        from domain.vote import VoteDirection
        
        self.assertEqual(VoteDirection.from_string("invalid"), VoteDirection.HOLD)
        self.assertEqual(VoteDirection.from_string(""), VoteDirection.HOLD)
    
    def test_is_bullish(self):
        """Test is_bullish property."""
        from domain.vote import VoteDirection
        
        self.assertTrue(VoteDirection.LONG.is_bullish)
        self.assertFalse(VoteDirection.SHORT.is_bullish)
        self.assertFalse(VoteDirection.HOLD.is_bullish)
    
    def test_is_bearish(self):
        """Test is_bearish property."""
        from domain.vote import VoteDirection
        
        self.assertTrue(VoteDirection.SHORT.is_bearish)
        self.assertFalse(VoteDirection.LONG.is_bearish)
        self.assertFalse(VoteDirection.HOLD.is_bearish)


class TestVote(unittest.TestCase):
    """Tests for Vote dataclass."""
    
    def test_vote_creation(self):
        """Test creating a vote."""
        from domain.vote import Vote, VoteDirection
        
        vote = Vote(
            direction=VoteDirection.LONG,
            confidence=75,
            leverage=3,
            reasoning="Bullish pattern"
        )
        
        self.assertEqual(vote.direction, VoteDirection.LONG)
        self.assertEqual(vote.confidence, 75)
        self.assertEqual(vote.leverage, 3)
        self.assertEqual(vote.reasoning, "Bullish pattern")
    
    def test_vote_defaults(self):
        """Test vote default values for optional params."""
        from domain.vote import Vote, VoteDirection
        
        vote = Vote(direction=VoteDirection.LONG, confidence=60)
        
        self.assertEqual(vote.leverage, 1)  # Default
        self.assertEqual(vote.take_profit_percent, 5.0)  # Default
        self.assertEqual(vote.stop_loss_percent, 2.0)  # Default
    
    def test_vote_confidence_clamping(self):
        """Test confidence is clamped to 0-100."""
        from domain.vote import Vote, VoteDirection
        
        vote = Vote(direction=VoteDirection.LONG, confidence=150)
        self.assertEqual(vote.confidence, 100)
        
        vote = Vote(direction=VoteDirection.LONG, confidence=-10)
        self.assertEqual(vote.confidence, 0)
    
    def test_vote_leverage_clamping(self):
        """Test leverage is clamped to 1-125."""
        from domain.vote import Vote, VoteDirection
        
        vote = Vote(direction=VoteDirection.LONG, confidence=70, leverage=200)
        self.assertEqual(vote.leverage, 125)
        
        vote = Vote(direction=VoteDirection.LONG, confidence=70, leverage=0)
        self.assertEqual(vote.leverage, 1)


class TestAgentVote(unittest.TestCase):
    """Tests for AgentVote dataclass."""
    
    def test_agent_vote_creation(self):
        """Test creating an agent vote."""
        from domain.vote import Vote, AgentVote, VoteDirection
        
        vote = Vote(direction=VoteDirection.LONG, confidence=75)
        agent_vote = AgentVote(
            agent_id="analyst1",
            agent_name="Technical Analyst",
            vote=vote
        )
        
        self.assertEqual(agent_vote.agent_id, "analyst1")
        self.assertEqual(agent_vote.agent_name, "Technical Analyst")
        self.assertEqual(agent_vote.direction, VoteDirection.LONG)
        self.assertEqual(agent_vote.confidence, 75)
    
    def test_agent_vote_to_dict(self):
        """Test AgentVote serialization."""
        from domain.vote import Vote, AgentVote, VoteDirection
        
        vote = Vote(direction=VoteDirection.SHORT, confidence=80, reasoning="Test")
        agent_vote = AgentVote(agent_id="a1", agent_name="Test", vote=vote)
        
        d = agent_vote.to_dict()
        
        self.assertEqual(d["direction"], "short")
        self.assertEqual(d["confidence"], 80)
        self.assertEqual(d["reasoning"], "Test")


class TestVoteSummary(unittest.TestCase):
    """Tests for VoteSummary."""
    
    def test_empty_summary(self):
        """Test summary with no votes."""
        from domain.vote import VoteSummary
        
        summary = VoteSummary([])
        
        self.assertEqual(summary.total_count, 0)
        self.assertEqual(summary.long_count, 0)
        self.assertEqual(summary.short_count, 0)
        self.assertEqual(summary.consensus_direction.value, "hold")
        self.assertEqual(summary.avg_confidence, 0.0)
    
    def test_unanimous_long(self):
        """Test unanimous long consensus."""
        from domain.vote import Vote, AgentVote, VoteDirection, VoteSummary
        
        votes = [
            AgentVote(
                agent_id=f"agent_{i}",
                agent_name=f"Agent {i}",
                vote=Vote(direction=VoteDirection.LONG, confidence=70)
            )
            for i in range(4)
        ]
        
        summary = VoteSummary(votes)
        
        self.assertEqual(summary.total_count, 4)
        self.assertEqual(summary.long_count, 4)
        self.assertEqual(summary.short_count, 0)
        self.assertEqual(summary.consensus_direction, VoteDirection.LONG)
        self.assertEqual(summary.consensus_strength, 1.0)
    
    def test_mixed_votes(self):
        """Test mixed vote consensus."""
        from domain.vote import Vote, AgentVote, VoteDirection, VoteSummary
        
        votes = [
            AgentVote(agent_id="1", agent_name="A", vote=Vote(direction=VoteDirection.LONG, confidence=70)),
            AgentVote(agent_id="2", agent_name="B", vote=Vote(direction=VoteDirection.LONG, confidence=60)),
            AgentVote(agent_id="3", agent_name="C", vote=Vote(direction=VoteDirection.SHORT, confidence=50)),
        ]
        
        summary = VoteSummary(votes)
        
        self.assertEqual(summary.long_count, 2)
        self.assertEqual(summary.short_count, 1)
        self.assertEqual(summary.consensus_direction, VoteDirection.LONG)
    
    def test_to_string(self):
        """Test human-readable summary."""
        from domain.vote import Vote, AgentVote, VoteDirection, VoteSummary
        
        votes = [
            AgentVote(agent_id="1", agent_name="A", vote=Vote(direction=VoteDirection.LONG, confidence=80)),
        ]
        
        summary = VoteSummary(votes)
        summary_str = summary.to_string()
        
        self.assertIn("Long", summary_str)
        self.assertIn("80", summary_str)


class TestMockLLMGateway(unittest.TestCase):
    """Tests for MockLLMGateway."""
    
    def test_mock_llm_creation(self):
        """Test creating mock LLM."""
        from tests.mocks.mock_llm import MockLLMGateway
        
        gateway = MockLLMGateway()
        self.assertEqual(gateway.get_call_count(), 0)
    
    def test_set_responses(self):
        """Test setting preset responses."""
        from tests.mocks.mock_llm import MockLLMGateway
        
        gateway = MockLLMGateway()
        gateway.set_responses(["Response 1", "Response 2"])
        
        async def test():
            r1 = await gateway.chat([{"role": "user", "content": "test"}])
            r2 = await gateway.chat([{"role": "user", "content": "test"}])
            return r1, r2
        
        r1, r2 = asyncio.run(test())
        
        self.assertEqual(r1.content, "Response 1")
        self.assertEqual(r2.content, "Response 2")
        self.assertEqual(gateway.get_call_count(), 2)
    
    def test_call_history(self):
        """Test call history is recorded."""
        from tests.mocks.mock_llm import MockLLMGateway
        
        gateway = MockLLMGateway()
        
        async def test():
            await gateway.chat([{"role": "user", "content": "hello"}])
            return gateway.get_last_call()
        
        last_call = asyncio.run(test())
        
        self.assertEqual(last_call["messages"][0]["content"], "hello")
    
    def test_vote_response_generator(self):
        """Test VoteResponseGenerator."""
        from tests.mocks.mock_llm import VoteResponseGenerator
        
        long_vote = VoteResponseGenerator.long_vote()
        data = json.loads(long_vote)
        
        self.assertEqual(data["direction"], "long")
        self.assertIn("confidence", data)
        self.assertIn("leverage", data)
        
        short_vote = VoteResponseGenerator.short_vote()
        data = json.loads(short_vote)
        self.assertEqual(data["direction"], "short")


class TestMockTrader(unittest.TestCase):
    """Tests for MockTrader."""
    
    def test_mock_trader_creation(self):
        """Test creating mock trader."""
        from tests.mocks.mock_trader import MockTrader
        
        trader = MockTrader(initial_balance=10000.0)
        self.assertEqual(trader.balance, 10000.0)
        self.assertEqual(trader.get_trade_count(), 0)
    
    def test_open_long(self):
        """Test opening long position."""
        from tests.mocks.mock_trader import MockTrader
        
        trader = MockTrader(initial_balance=10000.0)
        result = asyncio.run(trader.open_long(leverage=3, amount_percent=0.2))
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.order_id)
        self.assertGreater(result.size, 0)
        self.assertEqual(trader.get_trade_count(), 1)
    
    def test_open_short(self):
        """Test opening short position."""
        from tests.mocks.mock_trader import MockTrader
        
        trader = MockTrader(initial_balance=10000.0)
        result = asyncio.run(trader.open_short(leverage=5, amount_percent=0.1))
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.take_profit_price)
        self.assertIsNotNone(result.stop_loss_price)
    
    def test_close_position(self):
        """Test closing position."""
        from tests.mocks.mock_trader import MockTrader
        
        async def test():
            trader = MockTrader(initial_balance=10000.0)
            await trader.open_long(leverage=3, amount_percent=0.2)
            return await trader.close_position()
        
        result = asyncio.run(test())
        self.assertTrue(result.success)
    
    def test_get_account(self):
        """Test getting account balance."""
        from tests.mocks.mock_trader import MockTrader
        
        trader = MockTrader(initial_balance=10000.0)
        account = asyncio.run(trader.get_account())
        
        self.assertEqual(account.total_equity, 10000.0)
        self.assertEqual(account.available_balance, 10000.0)
    
    def test_reset(self):
        """Test trader reset."""
        from tests.mocks.mock_trader import MockTrader
        
        async def test():
            trader = MockTrader(initial_balance=10000.0)
            await trader.open_long(leverage=3)
            trader.reset()
            return trader
        
        trader = asyncio.run(test())
        
        self.assertEqual(trader.balance, 10000.0)
        self.assertEqual(trader.get_trade_count(), 0)
        self.assertEqual(len(trader.positions), 0)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Domain tests
    suite.addTests(loader.loadTestsFromTestCase(TestVoteDirection))
    suite.addTests(loader.loadTestsFromTestCase(TestVote))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentVote))
    suite.addTests(loader.loadTestsFromTestCase(TestVoteSummary))
    
    # Mock tests
    suite.addTests(loader.loadTestsFromTestCase(TestMockLLMGateway))
    suite.addTests(loader.loadTestsFromTestCase(TestMockTrader))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    print("=" * 60)
    print("Refactoring Module Tests")
    print("Testing: domain/vote.py, mocks/mock_llm.py, mocks/mock_trader.py")
    print("=" * 60)
    print()
    
    result = run_tests()
    
    print()
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("Status: ✅ ALL TESTS PASSED")
    else:
        print("Status: ❌ TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if result.wasSuccessful() else 1)
