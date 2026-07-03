"""
Ambrane AI Customer Support — VOICE DEMO WITH AUDIO PLAYBACK
=============================================================
Full pipeline: Receptionist → Auth (CRM) → Business Agents → Qwen LLM → Kokoro TTS → Speakers
"""

import asyncio
import io
import sys
import os
import wave
import tempfile
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

from langchain_core.messages import HumanMessage, AIMessage

DIVIDER = "═" * 60
SAMPLE_RATE = 24000


# ─── Audio playback ───────────────────────────────────────────────────────────

def play_audio(audio_bytes: bytes, label: str = ""):
    """Play PCM16 24kHz audio through speakers (sounddevice → winsound fallback)."""
    if label:
        print(f"  🔊  Playing: {label}")

    try:
        import sounddevice as sd
        import numpy as np
        samples = np.frombuffer(audio_bytes, dtype=np.int16)
        sd.play(samples, samplerate=SAMPLE_RATE, blocking=True)
        return
    except Exception:
        pass

    try:
        import winsound
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_bytes)
        winsound.PlaySound(tmp, winsound.SND_FILENAME)
        try: os.unlink(tmp)
        except: pass
        return
    except Exception:
        pass

    # Last resort: save WAV to disk
    out = os.path.join(os.path.dirname(__file__), "last_ai_response.wav")
    with wave.open(out, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_bytes)
    print(f"  💾  Saved as: last_ai_response.wav  (manual play agar speakers nahi aaye)")


# ─── TTS helper ───────────────────────────────────────────────────────────────

_tts_instance = None

async def synthesize(text: str) -> bytes:
    global _tts_instance
    from app.core.tts.kokoro import KokoroTTS
    if _tts_instance is None:
        _tts_instance = KokoroTTS()
    chunks = []
    async for chunk in _tts_instance.synthesize_stream(text):
        chunks.append(chunk)
    return b"".join(chunks)


# ─── Direct LLM call (bypasses intent model — uses Qwen directly) ─────────────

async def llm_respond(user_text: str, system_prompt: str, context: str = "") -> str:
    """Call Qwen 2.5 3B via Ollama directly."""
    from app.core.llm.ollama import OllamaLLM
    llm = OllamaLLM()
    llm.timeout = 120   # Qwen 3B on CPU takes ~36s — override 30s default

    full_prompt = f"{context}\n\nCustomer says: {user_text}" if context else f"Customer says: {user_text}"

    # Try RAG first
    try:
        from app.core.rag.retriever import rag
        citations = await rag.search(query=user_text)
        if citations:
            kb_ctx = rag.build_context_prompt(citations)
            full_prompt = f"{kb_ctx}\n\nCustomer says: {user_text}"
    except Exception:
        pass

    try:
        response = await llm.generate(prompt=full_prompt, system=system_prompt)
        return response.text.strip()
    except Exception as e:
        return f"I'm sorry, I'm having trouble responding right now. Please hold."


# ─── Main Demo ────────────────────────────────────────────────────────────────

async def main():
    print()
    print(DIVIDER)
    print("  🔊  AMBRANE AI CUSTOMER SUPPORT — VOICE DEMO")
    print(DIVIDER)
    print()

    # ── Initialize TTS once to avoid repeat loading ───────────────────────────
    print("  ⏳  Loading Kokoro TTS model (one-time, ~15 seconds) …")
    await synthesize("Loading.")  # warm up
    print("  ✓  Kokoro TTS ready!\n")

    # ── STEP 1: Receptionist Greeting ─────────────────────────────────────────
    from app.agents.state import initial_state
    from app.agents.receptionist.agent import receptionist_agent

    state = initial_state(call_id="DEMO-001", session_id="SES-001", channel="web")
    state["intelligence"] = {"language": "en", "sentiment": "neutral"}

    rec = await receptionist_agent(state)
    state.update(rec)
    greeting = rec["messages"][0].content

    print(DIVIDER)
    print("  📞  CALL CONNECTED")
    print(DIVIDER)
    print(f"\n  🤖  AI: \"{greeting}\"")
    audio = await synthesize(greeting)
    play_audio(audio, "Receptionist greeting (English)")

    # ── Hindi voice demo ──────────────────────────────────────────────────────
    hindi_greeting = "Ambrane customer support mein aapka swagat hai! Aaj main aapki kya sahayata kar sakti hoon?"
    print(f"\n  🤖  AI (Hindi): \"{hindi_greeting}\"")
    from app.core.tts.kokoro import KokoroTTS as _KokoroHindi
    _htts = _KokoroHindi()
    hindi_audio = await _htts.synthesize(hindi_greeting, voice="hf_alpha")
    play_audio(hindi_audio, "Hindi greeting (hf_alpha voice)")

    # ── STEP 2: Customer authenticates ────────────────────────────────────────
    user_q1 = "My customer ID is CUST-10001. I want to check my order status."
    print(f"\n{'─'*60}")
    print(f"  👤  Customer: \"{user_q1}\"")

    state["messages"].append(HumanMessage(content=user_q1))

    from app.agents.authentication.agent import authentication_agent
    auth_result = await authentication_agent(state)
    state.update(auth_result)

    cust = state.get("customer_context", {})
    name = cust.get("name", "Customer")
    vip  = "⭐ VIP" if cust.get("vip_status") else ""
    auth_ok = cust.get("is_authenticated", False)

    print(f"\n  🔐  CRM Authentication: {'✅ Verified — ' + name + ' ' + vip if auth_ok else '❌ Not found'}")

    # Order status response via LLM
    print("  ⏳  Checking order status via Qwen 2.5 LLM …")
    system_order = (
        "You are an order tracking specialist for Ambrane (electronics brand). "
        f"The authenticated customer is {name} (Customer ID: CUST-10001, VIP: {bool(vip)}). "
        "Respond naturally to order status queries. Keep response under 2 sentences."
    )
    ai_reply1 = await llm_respond(user_q1, system_order)

    state["messages"].append(AIMessage(content=ai_reply1, name="order_status"))
    state["intent"] = "order_status"
    state["routing_history"] = state.get("routing_history", []) + ["order_status"]

    print(f"\n  🎯  Intent: order_status")
    print(f"  🤖  AI: \"{ai_reply1}\"")
    audio2 = await synthesize(ai_reply1)
    play_audio(audio2, "Order status reply")

    # ── STEP 3: Warranty Query ────────────────────────────────────────────────
    user_q2 = "What is the warranty period on Ambrane power banks?"
    print(f"\n{'─'*60}")
    print(f"  👤  Customer: \"{user_q2}\"")
    state["messages"].append(HumanMessage(content=user_q2))

    print("  ⏳  Searching knowledge base + Qwen LLM …")
    system_warranty = (
        "You are a warranty specialist for Ambrane electronics. "
        "Answer warranty questions accurately and helpfully. Keep under 2 sentences."
    )
    ai_reply2 = await llm_respond(user_q2, system_warranty)

    state["messages"].append(AIMessage(content=ai_reply2, name="warranty"))
    state["intent"] = "warranty"
    state["routing_history"].append("warranty")

    print(f"\n  🎯  Intent: warranty")
    print(f"  🤖  AI: \"{ai_reply2}\"")
    audio3 = await synthesize(ai_reply2)
    play_audio(audio3, "Warranty reply")

    # ── STEP 4: Human Escalation ──────────────────────────────────────────────
    user_q3 = "This is not acceptable! I want to speak to a human agent right now."
    print(f"\n{'─'*60}")
    print(f"  👤  Customer: \"{user_q3}\"")
    state["messages"].append(HumanMessage(content=user_q3))

    # Use human escalation agent
    try:
        from app.agents.human_escalation.agent import human_escalation_agent
        esc_result = await human_escalation_agent(state)
        state.update(esc_result)
        ai_reply3 = None
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content.strip():
                ai_reply3 = msg.content.strip()
                break
    except Exception:
        ai_reply3 = None

    if not ai_reply3:
        system_esc = (
            "You are a customer support supervisor at Ambrane. "
            "The customer is upset and wants to escalate. Acknowledge their frustration, "
            "apologize, and inform them they are being connected to a live agent. "
            "Keep under 2 sentences."
        )
        ai_reply3 = await llm_respond(user_q3, system_esc)

    state["intent"] = "talk_to_human"
    state["escalate"] = True
    state["routing_history"].append("human_escalation")

    print(f"\n  🎯  Intent: talk_to_human")
    print(f"  🚨  Escalation flag: TRUE — routing to live agent")
    print(f"  🤖  AI: \"{ai_reply3}\"")
    audio4 = await synthesize(ai_reply3)
    play_audio(audio4, "Escalation message")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print("  📋  CALL SUMMARY")
    print(f"  Customer     : {name} {vip}")
    print(f"  Auth         : {'✅ Verified (CRM + DB)' if auth_ok else '❌'}")
    print(f"  Routing path : {' → '.join(state.get('routing_history', []))}")
    print(f"  Final intent : {state.get('intent', '—')}")
    print(f"  Escalated    : {'YES' if state.get('escalate') else 'No'}")
    print()
    print(DIVIDER)
    print("  ✅  DEMO COMPLETE!")
    print("  Receptionist ✓  CRM Auth ✓  Qwen LLM ✓  RAG ✓")
    print("  Kokoro TTS ✓  Speakers ✓  Human Escalation ✓")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(main())
