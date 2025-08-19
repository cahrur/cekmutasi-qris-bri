"""
Test webhook client - test kirim single mutation sesuai env dan format yang benar
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.httpclient import WebhookClient
from app.models import Mutasi
from app.config import config


def test_webhook_config():
    """Test webhook menggunakan config dari env"""
    print(f"Webhook URL dari config: {config.WEBHOOK_URL}")
    assert config.WEBHOOK_URL is not None


@pytest.fixture
def sample_mutation():
    """Sample mutation sesuai format yang benar"""
    return Mutasi(
        id_ext="2009",
        tgl="2025-01-18T10:30:00+07:00", 
        deskripsi="IBIZ KARYA MUDA DIG TO CAHRUR ROZID ESB:IBIZ:0001500F:103537161664",
        nominal=599000.0,
        saldo_akhir=1648.0,
        arah="DB",  # Debit
        no_referensi="2009",
        raw=["IBIZ KARYA MUDA DIG", "599,000", "1,648", "DB", "2009"]
    )


@pytest.mark.asyncio 
async def test_single_mutation_webhook(sample_mutation):
    """Test kirim single mutation dengan format webhook yang benar"""
    
    # Test payload format
    payload = sample_mutation.to_webhook_payload()
    
    print("=== WEBHOOK PAYLOAD TEST ===")
    print(f"Target URL: {config.WEBHOOK_URL}")
    print(f"Payload: {payload}")
    
    # Verify format sesuai dokumentasi mesinotomatis
    # $_POST fields untuk mutation
    
    expected_format = {
        "target": "mutation",
        "bank": "QRIS",
        "account": "-"
    }
    
    for key, expected_value in expected_format.items():
        assert payload[key] == expected_value, f"Field {key}: expected {expected_value}, got {payload[key]}"
    
    # Test specific values dari sample (DB=Debit -> "D")
    assert payload['type'] == "D"  # Debit
    assert payload['amount'] == "599000"
    assert payload['balance'] == "1648"
    assert 'date' in payload
    assert 'time' in payload
    assert 'description' in payload
    
    # Test tidak ada field yang tidak diperlukan
    assert 'key' not in payload  # Tidak ada field key lagi
    assert 'id' not in payload   # Tidak ada field id lagi  
    assert 'note' not in payload # Tidak ada field note lagi
    
    print("✅ Format webhook sudah benar!")


@pytest.mark.asyncio
async def test_webhook_client_post():
    """Test WebhookClient posting ke URL yang benar"""
    
    mutation = Mutasi(
        id_ext="TEST001",
        tgl="2025-01-18T10:30:00+07:00",
        deskripsi="Test mutation",
        nominal=100000.0,
        saldo_akhir=500000.0,
        arah="CR",
        no_referensi="TEST001",
        raw=["Test", "100,000", "500,000", "CR", "TEST001"]
    )
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    
    with patch('app.httpclient.httpx') as mock_httpx:
        mock_httpx.AsyncClient.return_value = mock_client
        mock_httpx.Timeout = MagicMock()
        
        webhook_client = WebhookClient()
        async with webhook_client as client:
            result = await client.post_mutation(mutation)
            
            # Verify berhasil
            assert result is True
            
            # Verify URL yang dipanggil sesuai config
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            actual_url = call_args[0][0]
            
            print(f"URL dipanggil: {actual_url}")
            print(f"Config URL: {config.WEBHOOK_URL}")
            
            assert actual_url == config.WEBHOOK_URL
            
            # Verify payload (kembali menggunakan json)
            payload = call_args[1]['json']
            assert payload['target'] == "mutation"
            assert payload['bank'] == "QRIS" 
            assert payload['account'] == "-"
            
    print("✅ Webhook client test berhasil!")


if __name__ == "__main__":
    # Test format webhook saja
    pytest.main([__file__ + "::test_single_mutation_webhook", "-v", "-s"])
