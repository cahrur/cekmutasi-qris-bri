"""
Unit tests for Indonesian parser module
"""
import pytest
from datetime import datetime
import pytz
from app.parser import IndonesianParser


class TestIndonesianParser:
    """Test cases for IndonesianParser"""
    
    def setup_method(self):
        """Setup test parser"""
        self.parser = IndonesianParser('Asia/Jakarta')
    
    def test_parse_number_indonesian_format(self):
        """Test parsing Indonesian number format with dots and commas"""
        # Indonesian format: dots for thousands, comma for decimal
        assert self.parser.parse_number("1.234.567,89") == 1234567.89
        assert self.parser.parse_number("12.345,50") == 12345.50
        assert self.parser.parse_number("1.000,00") == 1000.00
        
    def test_parse_number_international_format(self):
        """Test parsing international number format"""
        # International format: commas for thousands, dot for decimal
        assert self.parser.parse_number("1,234,567.89") == 1234567.89
        assert self.parser.parse_number("12,345.50") == 12345.50
        assert self.parser.parse_number("1,000.00") == 1000.00
    
    def test_parse_number_simple_formats(self):
        """Test parsing simple number formats"""
        assert self.parser.parse_number("123456") == 123456.0
        assert self.parser.parse_number("123.45") == 123.45
        assert self.parser.parse_number("123,45") == 123.45
        assert self.parser.parse_number("0") == 0.0
    
    def test_parse_number_negative(self):
        """Test parsing negative numbers"""
        assert self.parser.parse_number("-1.234.567,89") == -1234567.89
        assert self.parser.parse_number("-123,45") == -123.45
        assert self.parser.parse_number("(1.234,56)") == -1234.56
    
    def test_parse_number_edge_cases(self):
        """Test edge cases and invalid inputs"""
        assert self.parser.parse_number("") == 0.0
        assert self.parser.parse_number("-") == 0.0
        assert self.parser.parse_number("N/A") == 0.0
        assert self.parser.parse_number("n/a") == 0.0
        assert self.parser.parse_number("   ") == 0.0
        assert self.parser.parse_number(None) == 0.0
    
    def test_parse_date_slash_format(self):
        """Test parsing date with slash separators"""
        # DD/MM/YYYY format
        result = self.parser.parse_date("31/12/2023 15:30:45")
        assert result is not None
        assert "2023-12-31T15:30:45+07:00" in result
        
        # DD/MM/YYYY without time
        result = self.parser.parse_date("25/06/2023")
        assert result is not None
        assert "2023-06-25" in result
        
        # DD/MM/YYYY with time HH:MM
        result = self.parser.parse_date("15/03/2023 09:30")
        assert result is not None
        assert "2023-03-15T09:30:00+07:00" in result
    
    def test_parse_date_dash_format(self):
        """Test parsing date with dash separators"""
        result = self.parser.parse_date("31-12-2023 15:30:45")
        assert result is not None
        assert "2023-12-31T15:30:45+07:00" in result
        
        result = self.parser.parse_date("25-06-2023")
        assert result is not None
        assert "2023-06-25" in result
    
    def test_parse_date_indonesian_months(self):
        """Test parsing dates with Indonesian month names"""
        result = self.parser.parse_date("31 Des 2023 15:30")
        assert result is not None
        assert "2023-12-31" in result
        
        result = self.parser.parse_date("15 Jan 2023")
        assert result is not None
        assert "2023-01-15" in result
        
        result = self.parser.parse_date("28 Feb 2023 12:00")
        assert result is not None
        assert "2023-02-28" in result
    
    def test_parse_date_space_separated(self):
        """Test parsing space-separated dates"""
        result = self.parser.parse_date("31 12 2023 15:30:45")
        assert result is not None
        assert "2023-12-31T15:30:45+07:00" in result
        
        result = self.parser.parse_date("25 06 2023")
        assert result is not None
        assert "2023-06-25" in result
    
    def test_parse_date_edge_cases(self):
        """Test date parsing edge cases"""
        assert self.parser.parse_date("") is None
        assert self.parser.parse_date("   ") is None
        assert self.parser.parse_date(None) is None
        assert self.parser.parse_date("invalid date") is None
        assert self.parser.parse_date("32/13/2023") is None  # Invalid date
    
    def test_normalize_text(self):
        """Test text normalization"""
        assert self.parser.normalize_text("  hello   world  ") == "hello world"
        assert self.parser.normalize_text("") == ""
        assert self.parser.normalize_text("   ") == ""
        assert self.parser.normalize_text("single") == "single"
        assert self.parser.normalize_text("multiple\n\tspaces") == "multiple spaces"
    
    def test_detect_direction(self):
        """Test transaction direction detection"""
        assert self.parser.detect_direction(0, 100) == "CR"  # Credit
        assert self.parser.detect_direction(100, 0) == "DB"  # Debit
        assert self.parser.detect_direction(0, 0) == "CR"    # Default to credit
        assert self.parser.detect_direction(50, 0) == "DB"   # Debit
        assert self.parser.detect_direction(0, 75.5) == "CR" # Credit
    
    @pytest.mark.parametrize("date_str,expected_year,expected_month,expected_day", [
        ("01/01/2023", 2023, 1, 1),
        ("15/06/2023", 2023, 6, 15),
        ("31/12/2023", 2023, 12, 31),
        ("29/02/2024", 2024, 2, 29),  # Leap year
    ])
    def test_parse_date_parametrized(self, date_str, expected_year, expected_month, expected_day):
        """Parametrized test for date parsing"""
        result = self.parser.parse_date(date_str)
        assert result is not None
        
        # Parse the ISO date back to check components
        parsed_dt = datetime.fromisoformat(result.replace('Z', '+00:00'))
        assert parsed_dt.year == expected_year
        assert parsed_dt.month == expected_month
        assert parsed_dt.day == expected_day
    
    @pytest.mark.parametrize("number_str,expected", [
        ("1.234,50", 1234.50),
        ("1,234.50", 1234.50),
        ("12.345.678,90", 12345678.90),
        ("12,345,678.90", 12345678.90),
        ("100", 100.0),
        ("100,00", 100.0),
        ("100.00", 100.0),
        ("-500,25", -500.25),
        ("(750.00)", -750.0),
    ])
    def test_parse_number_parametrized(self, number_str, expected):
        """Parametrized test for number parsing"""
        result = self.parser.parse_number(number_str)
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__])
