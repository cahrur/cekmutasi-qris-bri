"""
Parser for Indonesian number and date formats
"""
import re
from datetime import datetime
from typing import Optional, Union
from .logger import LoggerMixin

try:
    import pytz
except ImportError:
    pytz = None

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None


class IndonesianParser(LoggerMixin):
    """Parser for Indonesian number and date formats"""
    
    def __init__(self, timezone: str = 'Asia/Jakarta'):
        super().__init__()
        if pytz is None:
            raise ImportError("pytz is required but not installed. Run: pip install pytz")
        self.timezone = pytz.timezone(timezone)
        
        # Indonesian month names mapping
        self.month_names = {
            'januari': 1, 'jan': 1,
            'februari': 2, 'feb': 2,
            'maret': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'mei': 5,
            'juni': 6, 'jun': 6,
            'juli': 7, 'jul': 7,
            'agustus': 8, 'ags': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'oktober': 10, 'okt': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'desember': 12, 'des': 12, 'dec': 12
        }
    
    def parse_number(self, value: Optional[str]) -> float:
        """
        Parse Indonesian number format to float
        Examples:
        - "1.234.567,89" -> 1234567.89
        - "1,234,567.89" -> 1234567.89  (handle both formats)
        - "12.345" -> 12345.0
        - "-" -> 0.0
        - "" -> 0.0
        """
        if not value or value.strip() in ['-', '', 'N/A', 'n/a']:
            return 0.0
        
        # Clean the value
        cleaned = value.strip().replace(' ', '')
        
        try:
            # Handle negative numbers
            is_negative = cleaned.startswith('-') or cleaned.startswith('(')
            if is_negative:
                cleaned = cleaned.lstrip('-').strip('()')
            
            # Detect Indonesian format (dot as thousand separator, comma as decimal)
            # vs International format (comma as thousand separator, dot as decimal)
            
            # Count dots and commas
            dot_count = cleaned.count('.')
            comma_count = cleaned.count(',')
            
            # Find last occurrence positions
            last_dot = cleaned.rfind('.')
            last_comma = cleaned.rfind(',')
            
            if comma_count == 0 and dot_count == 0:
                # Simple integer
                result = float(cleaned)
            elif comma_count > 0 and dot_count == 0:
                # Only commas - could be thousands or decimal
                if comma_count == 1 and len(cleaned.split(',')[1]) <= 2:
                    # Likely decimal separator
                    result = float(cleaned.replace(',', '.'))
                else:
                    # Likely thousand separators
                    result = float(cleaned.replace(',', ''))
            elif dot_count > 0 and comma_count == 0:
                # Only dots - could be thousands or decimal
                if dot_count == 1 and len(cleaned.split('.')[1]) <= 2:
                    # Likely decimal separator
                    result = float(cleaned)
                else:
                    # Likely thousand separators
                    result = float(cleaned.replace('.', ''))
            else:
                # Both dots and commas present
                if last_comma > last_dot:
                    # Indonesian format: 1.234.567,89
                    # Remove all dots, replace comma with dot
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                    result = float(cleaned)
                else:
                    # International format: 1,234,567.89
                    # Remove all commas
                    result = float(cleaned.replace(',', ''))
            
            return -result if is_negative else result
            
        except (ValueError, AttributeError) as e:
            self.log_warning(f"Failed to parse number", value=value, error=str(e))
            return 0.0
    
    def parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse Indonesian date format to ISO 8601 (RFC3339)
        Examples:
        - "31/12/2023 15:30" -> "2023-12-31T15:30:00+07:00"
        - "31-12-2023 15:30:45" -> "2023-12-31T15:30:45+07:00"
        - "31 Des 2023 15:30" -> "2023-12-31T15:30:00+07:00"
        """
        if not date_str or not date_str.strip():
            return None
        
        cleaned = date_str.strip()
        
        try:
            # Try to replace Indonesian month names
            cleaned_lower = cleaned.lower()
            for indo_month, month_num in self.month_names.items():
                if indo_month in cleaned_lower:
                    cleaned = re.sub(
                        rf'\b{re.escape(indo_month)}\b', 
                        str(month_num).zfill(2), 
                        cleaned, 
                        flags=re.IGNORECASE
                    )
                    break
            
            # Common Indonesian date patterns
            patterns = [
                # dd/mm/yyyy hh:mm:ss
                r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})',
                # dd/mm/yyyy hh:mm
                r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\s+(\d{1,2}):(\d{2})',
                # dd/mm/yyyy
                r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
                # dd mm yyyy hh:mm:ss (space separated)
                r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})',
                # dd mm yyyy hh:mm
                r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})\s+(\d{1,2}):(\d{2})',
                # dd mm yyyy
                r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})',
            ]
            
            parsed_dt = None
            
            # Try custom patterns first
            for pattern in patterns:
                match = re.match(pattern, cleaned)
                if match:
                    groups = match.groups()
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    
                    # Default time values
                    hour = int(groups[3]) if len(groups) > 3 else 0
                    minute = int(groups[4]) if len(groups) > 4 else 0
                    second = int(groups[5]) if len(groups) > 5 else 0
                    
                    try:
                        parsed_dt = datetime(year, month, day, hour, minute, second)
                        break
                    except ValueError:
                        continue
            
            # If custom patterns failed, try dateutil parser
            if parsed_dt is None and date_parser is not None:
                # Prepare for dateutil parser
                # Convert dd/mm/yyyy to mm/dd/yyyy format for dateutil
                date_for_parser = re.sub(
                    r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',
                    r'\2/\1/\3',
                    cleaned
                )
                parsed_dt = date_parser.parse(date_for_parser, dayfirst=True)
            
            # Localize to Indonesian timezone
            if parsed_dt and parsed_dt.tzinfo is None:
                parsed_dt = self.timezone.localize(parsed_dt)
            elif parsed_dt:
                parsed_dt = parsed_dt.astimezone(self.timezone)
            
            # Return RFC3339 format
            return parsed_dt.isoformat() if parsed_dt else None
            
        except Exception as e:
            self.log_warning(f"Failed to parse date", date_str=date_str, error=str(e))
            return None
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by removing extra whitespace and cleaning"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        normalized = ' '.join(text.strip().split())
        return normalized
    
    def detect_direction(self, debit: float, kredit: float) -> str:
        """Detect transaction direction based on debit/credit values"""
        if kredit > 0:
            return "CR"  # Credit
        elif debit > 0:
            return "DB"  # Debit
        else:
            return "CR"  # Default to credit if both are zero
