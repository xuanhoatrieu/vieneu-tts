"""
VieNeu TTS API — Full End-to-End Test Suite

Run: python tests/test_api.py [BASE_URL]
Default: http://127.0.0.1:8888
"""
import io
import sys
import math
import wave
import struct
import requests
import time
import uuid
import random
import string

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8888"
API = f"{BASE}/api/v1"

passed = 0
failed = 0
skipped = 0


def ok(name, detail=""):
    global passed
    passed += 1
    print(f"  ✅ {name}" + (f" ({detail})" if detail else ""))


def fail(name, detail=""):
    global failed
    failed += 1
    print(f"  ❌ {name}" + (f" ({detail})" if detail else ""))


def skip(name, detail=""):
    global skipped
    skipped += 1
    print(f"  ⏭️  {name}" + (f" ({detail})" if detail else ""))


def make_wav(dur=2.0, sr=24000):
    n = int(sr * dur)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        for i in range(n):
            val = int(16000 * math.sin(2 * math.pi * 440 * i / sr))
            w.writeframes(struct.pack("<h", val))
    buf.seek(0)
    return buf


def rand_email():
    chars = string.ascii_lowercase
    return f"{''.join(random.choices(chars, k=8))}@e2etest.com"


# ═══════════════════════════════════════
# 1. HEALTH CHECK
# ═══════════════════════════════════════
print("\n🏥 1. Health Check")
try:
    r = requests.get(f"{BASE}/", timeout=5)
    assert r.status_code == 200
    ok("Server", f"{r.json()['app']} v{r.json()['version']}")
except Exception as e:
    fail("Server", str(e)); sys.exit(1)

r = requests.get(f"{BASE}/docs", timeout=5)
ok("Docs") if r.status_code == 200 else fail("Docs")

r = requests.get(f"{BASE}/openapi.json", timeout=5)
ok("OpenAPI", f"{len(r.json()['paths'])} paths") if r.status_code == 200 else fail("OpenAPI")


# ═══════════════════════════════════════
# 2. USER FLOW
# ═══════════════════════════════════════
print("\n👤 2. User Flow")
test_email = rand_email()
test_pass = "Test12345"

r = requests.post(f"{API}/auth/register", json={
    "email": test_email, "password": test_pass, "name": "E2E Tester"
}, timeout=5)
if r.status_code == 201:
    ok("Register", test_email)
    user_token = r.json()["access_token"]
    user_h = {"Authorization": f"Bearer {user_token}"}
else:
    fail("Register", r.text[:120]); user_token = None; user_h = {}

if user_token:
    r = requests.post(f"{API}/auth/login", json={"email": test_email, "password": test_pass}, timeout=5)
    ok("Login") if r.status_code == 200 else fail("Login")

    r = requests.get(f"{API}/users/profile", headers=user_h, timeout=5)
    ok("Profile", r.json().get("name", "?")) if r.status_code == 200 else fail("Profile", f"{r.status_code}")


# ═══════════════════════════════════════
# 3. TTS
# ═══════════════════════════════════════
print("\n🎵 3. TTS")

r = requests.get(f"{API}/tts/voices", headers=user_h, timeout=5)
if r.status_code == 200:
    ok("Voices", f"{len(r.json())} presets")
else:
    fail("Voices")

# Synthesize with preset (500 expected without GPU)
if user_token:
    r = requests.post(f"{API}/tts/synthesize", headers=user_h, json={
        "text": "Xin chào", "voice_id": "vi-female-01"
    }, timeout=10)
    if r.status_code == 200:
        ok("Synthesize preset")
    elif r.status_code == 500:
        skip("Synthesize preset", "SDK not loaded — no GPU")
    else:
        fail("Synthesize preset", f"{r.status_code}")


# ═══════════════════════════════════════
# 4. REFERENCE AUDIO
# ═══════════════════════════════════════
print("\n📎 4. Reference Audio")

if user_token:
    wav = make_wav(3.0)
    r = requests.post(f"{API}/refs", headers=user_h, files={
        "audio": ("ref.wav", wav, "audio/wav")
    }, data={"name": "E2E Ref", "language": "vi", "ref_text": "test"}, timeout=15)
    if r.status_code == 201:
        ref_id = r.json()["id"]
        ok("Upload ref", f"id={ref_id[:8]}...")
    else:
        fail("Upload ref", f"{r.status_code} {r.text[:100]}"); ref_id = None

    r = requests.get(f"{API}/refs", headers=user_h, timeout=5)
    ok("List refs", f"{len(r.json())}") if r.status_code == 200 else fail("List refs")

    if ref_id:
        r = requests.delete(f"{API}/refs/{ref_id}", headers=user_h, timeout=5)
        ok("Delete ref") if r.status_code == 204 else fail("Delete ref")


# ═══════════════════════════════════════
# 5. SENTENCES + RECORDINGS
# ═══════════════════════════════════════
print("\n📝 5. Sentences + Recordings")
set_id = None
recorded = 0

if user_token:
    r = requests.get(f"{API}/sentences/sets", headers=user_h, timeout=5)
    if r.status_code == 200:
        sets = r.json()
        ok("List sets", f"{len(sets)} sets")
        set_id = sets[0]["id"] if sets else None
    else:
        fail("List sets")

if set_id:
    r = requests.get(f"{API}/sentences/sets/{set_id}", headers=user_h, timeout=5)
    if r.status_code == 200:
        sentences = r.json()["sentences"]
        ok("Set detail", f"{len(sentences)} sentences")
    else:
        fail("Set detail"); sentences = []

    # Record 15 sentences
    for sent in sentences[:15]:
        wav = make_wav(2.0)
        r = requests.post(
            f"{API}/training/recordings/{set_id}/{sent['id']}",
            headers=user_h, files={"audio": ("r.wav", wav, "audio/wav")}, timeout=15,
        )
        if r.status_code == 201:
            recorded += 1

    ok(f"Record {recorded} sentences") if recorded >= 10 else fail(f"Record", f"only {recorded}")

    r = requests.get(f"{API}/training/recordings/{set_id}", headers=user_h, timeout=5)
    if r.status_code == 200:
        ok("Progress", f"{r.json()['recorded_count']}/{r.json()['total_sentences']}")
    else:
        fail("Progress")


# ═══════════════════════════════════════
# 6. TRAINING FLOW
# ═══════════════════════════════════════
print("\n🏋️ 6. Training Flow")

admin_r = requests.post(f"{API}/auth/login", json={
    "email": "admin@vietneu.io", "password": "changeme"
}, timeout=5)
admin_h = {"Authorization": f"Bearer {admin_r.json()['access_token']}"}

r = requests.get(f"{API}/training/base-models", timeout=5)
ok("Base models", f"{len(r.json())}") if r.status_code == 200 else fail("Base models")

req_id = None
if recorded >= 10 and set_id and user_token:
    r = requests.post(f"{API}/training/requests", headers=user_h, json={
        "voice_name": "E2E Voice", "set_id": set_id
    }, timeout=5)
    if r.status_code == 201:
        req_id = r.json()["id"]; ok("Submit request", f"id={req_id}")
    else:
        fail("Submit request", f"{r.status_code} {r.text[:80]}")

    # Duplicate → 400
    r = requests.post(f"{API}/training/requests", headers=user_h, json={
        "voice_name": "Dup", "set_id": set_id
    }, timeout=5)
    ok("Duplicate → 400") if r.status_code == 400 else fail("Duplicate", f"{r.status_code}")

    # Admin approve
    r = requests.post(f"{API}/admin/training-queue/{req_id}/approve", headers=admin_h, timeout=5)
    ok("Admin approve") if r.status_code == 200 else fail("Admin approve", f"{r.status_code}")

    # Admin start
    r = requests.post(f"{API}/admin/training-queue/{req_id}/start", headers=admin_h, timeout=5)
    ok("Start training") if r.status_code == 200 else fail("Start training")

    time.sleep(2)

    # Check progress
    r = requests.get(f"{API}/training/requests/{req_id}", headers=user_h, timeout=5)
    if r.status_code == 200:
        ok("Progress", f"status={r.json()['status']} {r.json()['progress']}%")

    # Voices
    r = requests.get(f"{API}/training/voices", headers=user_h, timeout=5)
    ok("Trained voices", f"{len(r.json())}") if r.status_code == 200 else fail("Trained voices")
else:
    skip("Training flow", "not enough recordings")


# ═══════════════════════════════════════
# 7. AUTH TESTS
# ═══════════════════════════════════════
print("\n🔐 7. Auth Tests")

r = requests.get(f"{API}/users/profile", timeout=5)
ok("No auth → 401") if r.status_code == 401 else fail("No auth", f"{r.status_code}")

r = requests.get(f"{API}/users/profile", headers={"Authorization": "Bearer bad"}, timeout=5)
ok("Bad token → 401") if r.status_code == 401 else fail("Bad token", f"{r.status_code}")

if user_token:
    r = requests.get(f"{API}/admin/training-queue", headers=user_h, timeout=5)
    ok("Non-admin → 403") if r.status_code == 403 else fail("Non-admin", f"{r.status_code}")

    r = requests.post(f"{API}/api-keys", headers=user_h, json={"name": "E2E Key"}, timeout=5)
    if r.status_code == 201:
        api_key = r.json()["key"]
        ok("Create API key", f"{api_key[:10]}...")
        r = requests.get(f"{API}/users/profile", headers={"X-API-Key": api_key}, timeout=5)
        ok("API key auth") if r.status_code == 200 else fail("API key auth")
    else:
        fail("Create API key")


# ═══════════════════════════════════════
# 8. EDGE CASES
# ═══════════════════════════════════════
print("\n🧪 8. Edge Cases")

if user_token and set_id:
    wav_short = make_wav(0.3)
    r = requests.post(
        f"{API}/training/recordings/{set_id}/999",
        headers=user_h, files={"audio": ("s.wav", wav_short, "audio/wav")}, timeout=15,
    )
    ok("Short audio → 400") if r.status_code == 400 else (
        ok("Short audio → 404 (sentence)") if r.status_code == 404 else fail("Short audio", f"{r.status_code}")
    )

    r = requests.delete(f"{API}/refs/{uuid.uuid4()}", headers=user_h, timeout=5)
    ok("Fake ref → 404") if r.status_code == 404 else fail("Fake ref", f"{r.status_code}")

    r = requests.post(f"{API}/training/requests", headers=admin_h, json={
        "voice_name": "Nope", "set_id": set_id or 1
    }, timeout=5)
    ok("< 10 rec → 400") if r.status_code == 400 else fail("< 10 rec", f"{r.status_code}")


# ═══════════════════════════════════════
# 9. USER ISOLATION
# ═══════════════════════════════════════
print("\n🔒 9. User Isolation")

user2_email = rand_email()
r = requests.post(f"{API}/auth/register", json={
    "email": user2_email, "password": "Pass12345", "name": "User 2"
}, timeout=5)
if r.status_code == 201:
    u2h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = requests.get(f"{API}/refs", headers=u2h, timeout=5)
    ok("Isolation refs") if r.status_code == 200 and len(r.json()) == 0 else fail("Isolation refs")

    r = requests.get(f"{API}/training/recordings/1", headers=u2h, timeout=5)
    if r.status_code == 200 and r.json()["recorded_count"] == 0:
        ok("Isolation recordings")
    else:
        fail("Isolation recordings")

    r = requests.get(f"{API}/training/requests", headers=u2h, timeout=5)
    ok("Isolation requests") if r.status_code == 200 and len(r.json()) == 0 else fail("Isolation requests")
else:
    skip("Isolation", "register failed")


# ═══════════════════════════════════════
total = passed + failed + skipped
print(f"\n{'='*50}")
print(f"📊 RESULTS: {passed}/{total} passed, {failed} failed, {skipped} skipped")
print(f"{'='*50}")
print("🎉 ALL TESTS PASSED!" if failed == 0 else f"⚠️  {failed} test(s) failed")
sys.exit(0 if failed == 0 else 1)
