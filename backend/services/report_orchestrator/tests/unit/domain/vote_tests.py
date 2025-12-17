"""
Unit Tests for Vote Domain Models

Tests for Vote, AgentVote, VoteDirection, and VoteSummary.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class TestVoteDirection:
    """Tests for VoteDirection enum."""
    
    def test_direction_values(self):
        """Test direction enum values."""
        from app.core.trading.domain.vote import VoteDirection
        
        assert VoteDirection.LONG.value == "long"
        assert VoteDirection.SHORT.value == "short"
        assert VoteDirection.HOLD.value == "hold"
        assert VoteDirection.CLOSE.value == "close"
    
    def test_normalize_long(self):
        """Test normalizing long variations."""
        from app.core.trading.domain.vote import VoteDirection
        
        assert VoteDirection.normalize("long") == VoteDirection.LONG
        assert VoteDirection.normalize("LONG") == VoteDirection.LONG
        assert VoteDirection.normalize("Long") == VoteDirection.LONG
        assert VoteDirection.normalize("做多") == VoteDirection.LONG
        assert VoteDirection.normalize("buy") == VoteDirection.LONG
    
    def test_normalize_short(self):
        """Test normalizing short variations."""
        from app.core.trading.domain.vote import VoteDirection
        
        assert VoteDirection.normalize("short") == VoteDirection.SHORT
        assert VoteDirection.normalize("SHORT") == VoteDirection.SHORT
        assert VoteDirection.normalize("做空") == VoteDirection.SHORT
        assert VoteDirection.normalize("sell") == VoteDirection.SHORT
    
    def test_normalize_hold(self):
        """Test normalizing hold variations."""
        from app.core.trading.domain.vote import VoteDirection
        
        assert VoteDirection.normalize("hold") == VoteDirection.HOLD
        assert VoteDirection.normalize("观望") == VoteDirection.HOLD
        assert VoteDirection.normalize("wait") == VoteDirection.HOLD
    
    def test_normalize_invalid(self):
        """Test normalizing invalid direction."""
        from app.core.trading.domain.vote import VoteDirection
        
        assert VoteDirection.normalize("invalid") == VoteDirection.HOLD
        assert VoteDirection.normalize("") == VoteDirection.HOLD
        assert VoteDirection.normalize(None) == VoteDirection.HOLD


class TestVote:
    """Tests for Vote dataclass."""
    
    def test_vote_creation(self):
        """Test creating a vote."""
        from app.core.trading.domain.vote import Vote, VoteDirection
        
        vote = Vote(
            direction=VoteDirection.LONG,
            confidence=75,
            leverage=3,
            reasoning="Bullish pattern"
        )
        
        assert vote.direction == VoteDirection.LONG
        assert vote.confidence == 75
        assert vote.leverage == 3
        assert vote.reasoning == "Bullish pattern"
    
    def test_vote_defaults(self):
        """Test vote default values."""
        from app.core.trading.domain.vote import Vote, VoteDirection
        
        vote = Vote(direction=VoteDirection.LONG)
        
        assert vote.confidence == 50
        assert vote.leverage == 1
        assert vote.reasoning == ""


class TestVoteSummary:
    """Tests for VoteSummary."""
    
    def test_empty_summary(self):
        """Test summary with no votes."""
        from app.core.trading.domain.vote import VoteSummary
        
        summary = VoteSummary([])
        
        assert summary.long_count == 0
        assert summary.short_count == 0
        assert summary.hold_count == 0
        assert summary.consensus_direction.value == "hold"
    
    def test_unanimous_long(self):
        """Test unanimous long consensus."""
        from app.core.trading.domain.vote import Vote, AgentVote, VoteDirection, VoteSummary
        
        votes = [
            AgentVote(
                agent_id=f"agent_{i}",
                agent_name=f"Agent {i}",
                vote=Vote(direction=VoteDirection.LONG, confidence=70)
            )
            for i in range(4)
        ]
        
        summary = VoteSummary(votes)
        
        assert summary.long_count == 4
        assert summary.short_count == 0
        assert summary.consensus_direction == VoteDirection.LONG
        assert summary.consensus_strength == 1.0
    
    def test_mixed_votes(self):
        """Test mixed vote consensus."""
        from app.core.trading.domain.vote import Vote, AgentVote, VoteDirection, VoteSummary
        
        votes = [
            AgentVote(agent_id="1", agent_name="A1", vote=Vote(direction=VoteDirection.LONG, confidence=80)),
            AgentVote(agent_id="2", agent_name="A2", vote=Vote(direction=VoteDirection.LONG, confidence=70)),
            AgentVote(agent_id="3", agent_name="A3", vote=Vote(direction=VoteDirection.SHORT, confidence=60)),
            AgentVote(agent_id="4", agent_name="A4", vote=Vote(direction=VoteDirection.HOLD, confidence=50)),
        ]
        
        summary = VoteSummary(votes)
        
        assert summary.long_count == 2
        assert summary.short_count == 1
        assert summary.hold_count == 1
        assert summary.consensus_direction == VoteDirection.LONG
        assert summary.consensus_strength == 0.5  # 2/4
