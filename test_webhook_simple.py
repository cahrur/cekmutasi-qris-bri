"""
Test webhook sederhana untuk production
"""
import asyncio
from app.httpclient import WebhookClient
from app.models import Mutasi


async def test_webhook_production():
    """Test webhook untuk production"""
    
    print("=== TEST WEBHOOK PRODUCTION ===")
    
    # Generate waktu sekarang
    from datetime import datetime
    import pytz
    
    # Waktu sekarang dalam timezone Jakarta
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(jakarta_tz)
    timestamp = now.isoformat()
    
    # ID unik berdasarkan timestamp
    test_id = f"TEST_{now.strftime('%Y%m%d_%H%M%S')}"
    
    print(f"Timestamp: {timestamp}")
    print(f"Test ID: {test_id}")
    
    # Buat sample mutation
    mutation = Mutasi(
        id_ext=test_id,
        tgl=timestamp,
        deskripsi=f"TEST PRODUCTION - TRANSFER MASUK - {now.strftime('%H:%M:%S')}",
        nominal=10994.0,
        saldo_akhir=1000000.0,
        arah="CR",  # Credit
        no_referensi=test_id,
        raw=["TEST", "10,994", "1,000,000", "CR", test_id]
    )
    
    # Tampilkan payload
    payload = mutation.to_webhook_payload()
    print("\nWebhook payload:")
    for key, value in payload.items():
        print(f"  {key}: {value}")
    
    # Test kirim webhook
    print("\nMengirim webhook...")
    try:
        webhook_client = WebhookClient()
        async with webhook_client as client:
            result = await client.post_mutation(mutation)
            
            if result:
                print("✅ Webhook berhasil dikirim!")
                print("✅ Status: SUCCESS")
                return True
            else:
                print("❌ Webhook gagal dikirim!")
                print("❌ Status: FAILED")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_webhook_production())
    
    print(f"\n{'='*40}")
    print("HASIL TEST:")
    if success:
        print("🎉 Webhook berfungsi dengan baik!")
    else:
        print("⚠️ Webhook bermasalah - cek IP whitelist")
    print(f"{'='*40}")
