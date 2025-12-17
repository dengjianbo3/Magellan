"""
Unit Tests for Vote Parser

Tests for VoteParser and related parsing functionality.
Run with: pytest tests/unit/parsers/vote_parser_tests.py
"""

import pytest
import json
import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class TestVoteParser:
    """Tests for VoteParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        from app.core.trading.parsers.vote_parser import VoteParser
        return VoteParser()
    
    # ==================== JSON Parsing Tests ====================
    
    def test_parse_direct_json(self, parser):
        """Test parsing valid JSON directly."""
        from app.core.trading.domain.vote import VoteDirection
        
        json_str = json.dumps({
            "direction": "long",
            "confidence": 75,
            "leverage": 3,
            "take_profit_percent": 5.0,
            "stop_loss_percent": 2.0,
            "reasoning": "Bullish signals"
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote is not None
        assert result.vote.direction == VoteDirection.LONG
        assert result.vote.confidence == 75
        assert result.vote.leverage == 3
        assert result.method == "direct_json"
    
    def test_parse_short_vote(self, parser):
        """Test parsing short vote."""
        from app.core.trading.domain.vote import VoteDirection
        
        json_str = json.dumps({
            "direction": "short",
            "confidence": 80,
            "leverage": 5,
            "reasoning": "Bearish breakdown"
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote.direction == VoteDirection.SHORT
        assert result.vote.confidence == 80
    
    def test_parse_hold_vote(self, parser):
        """Test parsing hold vote."""
        from app.core.trading.domain.vote import VoteDirection
        
        json_str = json.dumps({
            "direction": "hold",
            "confidence": 50,
            "reasoning": "Market unclear"
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote.direction == VoteDirection.HOLD
    
    # ==================== Markdown Wrapper Tests ====================
    
    def test_parse_json_in_markdown(self, parser):
        """Test parsing JSON wrapped in markdown code block."""
        from app.core.trading.domain.vote import VoteDirection
        
        response = '''Based on my analysis:

```json
{
    "direction": "long",
    "confidence": 70,
    "leverage": 2,
    "reasoning": "RSI oversold"
}
```

This is my recommendation.'''
        
        result = parser.parse(response)
        
        assert result.success
        assert result.vote.direction == VoteDirection.LONG
        assert result.method == "json_in_code_block"
    
    # ==================== Direction Normalization Tests ====================
    
    def test_parse_chinese_long(self, parser):
        """Test parsing Chinese '做多' direction."""
        from app.core.trading.domain.vote import VoteDirection
        
        json_str = json.dumps({
            "direction": "做多",
            "confidence": 70
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote.direction == VoteDirection.LONG
    
    def test_parse_chinese_short(self, parser):
        """Test parsing Chinese '做空' direction."""
        from app.core.trading.domain.vote import VoteDirection
        
        json_str = json.dumps({
            "direction": "做空",
            "confidence": 65
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote.direction == VoteDirection.SHORT
    
    def test_parse_uppercase_direction(self, parser):
        """Test parsing uppercase direction."""
        from app.core.trading.domain.vote import VoteDirection
        
        json_str = json.dumps({
            "direction": "LONG",
            "confidence": 75
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote.direction == VoteDirection.LONG
    
    def test_parse_buy_as_long(self, parser):
        """Test parsing 'buy' as long."""
        from app.core.trading.domain.vote import VoteDirection
        
        json_str = json.dumps({
            "direction": "buy",
            "confidence": 70
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote.direction == VoteDirection.LONG
    
    # ==================== Default Value Tests ====================
    
    def test_default_confidence(self, parser):
        """Test default confidence when not provided."""
        json_str = json.dumps({
            "direction": "long"
        })
        
        result = parser.parse(json_str)
        
        assert result.success
        assert result.vote.confidence == 50  # Default
    
    # ==================== Error Handling Tests ====================
    
    def test_parse_empty_string(self, parser):
        """Test handling of empty string."""
        result = parser.parse("")
        
        assert not result.success
