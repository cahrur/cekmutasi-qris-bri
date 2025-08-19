"""
Data models for QRIS mutation scraper
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import hashlib
import json


@dataclass
class Mutasi:
    """Model for QRIS mutation data"""
    id_ext: str
    tgl: str  # ISO 8601 datetime in RFC3339 format
    deskripsi: str
    nominal: float
    saldo_akhir: Optional[float]
    arah: str  # "CR" for credit, "DB" for debit
    no_referensi: Optional[str]
    raw: List[str]  # raw table columns for debugging
    
    @classmethod
    def create_id_ext(cls, no_referensi: Optional[str], tanggal: str, 
                     deskripsi: str, nominal: float, arah: str) -> str:
        """Generate id_ext from reference number or hash of key fields"""
        if no_referensi and no_referensi.strip():
            return no_referensi.strip()
        
        # Create hash from key fields
        data = f"{tanggal}|{deskripsi}|{nominal}|{arah}"
        hash_obj = hashlib.sha256(data.encode('utf-8'))
        return hash_obj.hexdigest()[:32]
    
    def to_webhook_payload(self) -> Dict[str, str]:
        """Convert to webhook payload format sesuai dokumentasi mesinotomatis"""
        # Parse datetime for date and time fields
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(self.tgl.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M:%S')
        except:
            # Fallback if datetime parsing fails
            import datetime
            now = datetime.datetime.now()
            date_str = now.strftime('%Y-%m-%d')
            time_str = now.strftime('%H:%M:%S')
        
        # Convert direction: CR=K (Kredit), DB=D (Debit) - sesuai dokumentasi
        transaction_type = "K" if self.arah == "CR" else "D"
        
        # Format amount as string without decimals for integer values
        amount_str = f"{int(self.nominal)}" if self.nominal == int(self.nominal) else f"{self.nominal}"
        
        # Format balance as string
        balance_str = ""
        if self.saldo_akhir is not None:
            balance_str = f"{int(self.saldo_akhir)}" if self.saldo_akhir == int(self.saldo_akhir) else f"{self.saldo_akhir}"
        
        # Format sesuai dokumentasi mesinotomatis $_POST fields
        return {
            "target": "mutation",
            "bank": "QRIS", 
            "account": "-",
            "date": date_str,
            "time": time_str,
            "description": self.deskripsi,
            "type": transaction_type,
            "amount": amount_str,
            "balance": balance_str
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
