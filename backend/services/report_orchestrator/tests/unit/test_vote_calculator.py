"""
Unit Tests for Vote Calculator

Tests cover:
- VC-001 to VC-008: Consensus calculation from agent votes
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# Standalone Vote Calculator Tests (no external dependencies)
# =============================================================================

class TestVoteCalculator:
    """Test vote calculation logic"""
    
    @staticmethod
    def calculate_consensus(votes):
        """
        Simplified vote calculation logic for testing.
        
        Returns the direction with most votes, weighted by confidence.
        If tie, defaults to 'hold'.
        """
        if not votes:
            return {"direction": "hold", "confidence": 0}
        
        # Count weighted votes
        direction_scores = {"long": 0, "short": 0, "hold": 0}
        confidence_sum = {"long": 0, "short": 0, "hold": 0}
        direction_count = {"long": 0, "short": 0, "hold": 0}
        
        for vote in votes:
            direction = vote.get("direction", "hold")
            confidence = vote.get("confidence", 50)
            weight = vote.get("weight", 1.0)
            
            if direction in direction_scores:
                direction_scores[direction] += confidence * weight
                confidence_sum[direction] += confidence
                direction_count[direction] += 1
        
        # Find winner
        winner = max(direction_scores, key=direction_scores.get)
        
        # If tie between long/short, default to hold
        if direction_scores["long"] == direction_scores["short"] and direction_scores["long"] > 0:
            winner = "hold"
        
        # Calculate average confidence for winner
        if direction_count[winner] > 0:
            avg_confidence = confidence_sum[winner] // direction_count[winner]
        else:
            avg_confidence = 0
        
        return {"direction": winner, "confidence": avg_confidence}
    
    def test_unanimous_long(self):
        """VC-001: 5 votes LONG → consensus=long"""
        votes = [
            {"agent": "TA", "direction": "long", "confidence": 70},
            {"agent": "SA", "direction": "long", "confidence": 75},
            {"agent": "ME", "direction": "long", "confidence": 65},
            {"agent": "OA", "direction": "long", "confidence": 80},
            {"agent": "QS", "direction": "long", "confidence": 70},
        ]
        
        result = self.calculate_consensus(votes)
        
        assert result["direction"] == "long"
        assert result["confidence"] > 0
    
    def test_unanimous_short(self):
        """VC-002: 5 votes SHORT → consensus=short"""
        votes = [
            {"agent": "TA", "direction": "short", "confidence": 70},
            {"agent": "SA", "direction": "short", "confidence": 75},
            {"agent": "ME", "direction": "short", "confidence": 65},
            {"agent": "OA", "direction": "short", "confidence": 80},
            {"agent": "QS", "direction": "short", "confidence": 70},
        ]
        
        result = self.calculate_consensus(votes)
        
        assert result["direction"] == "short"
    
    def test_unanimous_hold(self):
        """VC-003: 5 votes HOLD → consensus=hold"""
        votes = [
            {"agent": "TA", "direction": "hold", "confidence": 60},
            {"agent": "SA", "direction": "hold", "confidence": 55},
            {"agent": "ME", "direction": "hold", "confidence": 65},
            {"agent": "OA", "direction": "hold", "confidence": 50},
            {"agent": "QS", "direction": "hold", "confidence": 60},
        ]
        
        result = self.calculate_consensus(votes)
        
        assert result["direction"] == "hold"
    
    def test_majority_long(self):
        """VC-004: 3 LONG, 2 HOLD → consensus=long"""
        votes = [
            {"agent": "TA", "direction": "long", "confidence": 70},
            {"agent": "SA", "direction": "long", "confidence": 75},
            {"agent": "ME", "direction": "long", "confidence": 65},
            {"agent": "OA", "direction": "hold", "confidence": 50},
            {"agent": "QS", "direction": "hold", "confidence": 55},
        ]
        
        result = self.calculate_consensus(votes)
        
        assert result["direction"] == "long"
    
    def test_split_vote_defaults_to_hold(self):
        """VC-005: 2 LONG, 2 SHORT, 1 HOLD → consensus=hold (conservative)"""
        votes = [
            {"agent": "TA", "direction": "long", "confidence": 70},
            {"agent": "SA", "direction": "long", "confidence": 70},
            {"agent": "ME", "direction": "short", "confidence": 70},
            {"agent": "OA", "direction": "short", "confidence": 70},
            {"agent": "QS", "direction": "hold", "confidence": 60},
        ]
        
        result = self.calculate_consensus(votes)
        
        # When long == short in weighted score, should default to hold
        assert result["direction"] == "hold"
    
    def test_weight_adjustment(self):
        """VC-006: Higher weight agents have more influence"""
        votes = [
            {"agent": "TA", "direction": "long", "confidence": 60, "weight": 2.0},  # Higher weight
            {"agent": "SA", "direction": "short", "confidence": 80, "weight": 0.5},  # Lower weight
            {"agent": "ME", "direction": "hold", "confidence": 50, "weight": 1.0},
        ]
        
        result = self.calculate_consensus(votes)
        
        # TA (long): 60 * 2.0 = 120
        # SA (short): 80 * 0.5 = 40
        # ME (hold): 50 * 1.0 = 50
        # Long wins
        assert result["direction"] == "long"
    
    def test_empty_votes(self):
        """VC-007: Empty votes → default HOLD"""
        result = self.calculate_consensus([])
        
        assert result["direction"] == "hold"
        assert result["confidence"] == 0
    
    def test_confidence_weighted(self):
        """VC-008: High confidence votes have more weight"""
        votes = [
            {"agent": "TA", "direction": "long", "confidence": 95},  # Very high
            {"agent": "SA", "direction": "short", "confidence": 40}, # Low
            {"agent": "ME", "direction": "short", "confidence": 40}, # Low
        ]
        
        result = self.calculate_consensus(votes)
        
        # Long: 95 * 1.0 = 95
        # Short: 40 + 40 = 80
        # Long wins due to higher total weighted score
        assert result["direction"] == "long"


# =============================================================================
# Additional Vote Edge Cases
# =============================================================================

class TestVoteEdgeCases:
    """Test edge cases in vote calculation"""
    
    @staticmethod
    def calculate_consensus(votes):
        """Same as above"""
        if not votes:
            return {"direction": "hold", "confidence": 0}
        
        direction_scores = {"long": 0, "short": 0, "hold": 0}
        confidence_sum = {"long": 0, "short": 0, "hold": 0}
        direction_count = {"long": 0, "short": 0, "hold": 0}
        
        for vote in votes:
            direction = vote.get("direction", "hold")
            confidence = vote.get("confidence", 50)
            weight = vote.get("weight", 1.0)
            
            if direction in direction_scores:
                direction_scores[direction] += confidence * weight
                confidence_sum[direction] += confidence
                direction_count[direction] += 1
        
        winner = max(direction_scores, key=direction_scores.get)
        
        if direction_scores["long"] == direction_scores["short"] and direction_scores["long"] > 0:
            winner = "hold"
        
        if direction_count[winner] > 0:
            avg_confidence = confidence_sum[winner] // direction_count[winner]
        else:
            avg_confidence = 0
        
        return {"direction": winner, "confidence": avg_confidence}
    
    def test_single_vote(self):
        """Single vote determines outcome"""
        votes = [{"agent": "TA", "direction": "long", "confidence": 80}]
        
        result = self.calculate_consensus(votes)
        
        assert result["direction"] == "long"
        assert result["confidence"] == 80
    
    def test_zero_confidence_vote(self):
        """Zero confidence vote"""
        votes = [
            {"agent": "TA", "direction": "long", "confidence": 0},
            {"agent": "SA", "direction": "hold", "confidence": 50},
        ]
        
        result = self.calculate_consensus(votes)
        
        # Hold wins with 50 * 1.0 = 50 vs Long with 0 * 1.0 = 0
        assert result["direction"] == "hold"
    
    def test_missing_direction_defaults_hold(self):
        """Missing direction defaults to hold"""
        votes = [
            {"agent": "TA", "confidence": 70},  # No direction
        ]
        
        result = self.calculate_consensus(votes)
        
        assert result["direction"] == "hold"
    
    def test_invalid_direction_ignored(self):
        """Invalid direction is ignored"""
        votes = [
            {"agent": "TA", "direction": "invalid", "confidence": 70},
            {"agent": "SA", "direction": "long", "confidence": 60},
        ]
        
        result = self.calculate_consensus(votes)
        
        # Only "long" is valid, so it wins
        assert result["direction"] == "long"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
