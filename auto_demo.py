"""
Ambrane AI — Enterprise Call Flow Demo
=======================================
Connects to the WebSocket, demonstrates the full LangGraph pipeline.
"""
import asyncio
import websockets
import json

DIVIDER = "=" * 70

async def recv_with_timeout(ws, timeout=15):
    """Receive a message with timeout."""
    try:
        return await asyncio.wait_for(ws.recv(), timeout=timeout)
    except asyncio.TimeoutError:
        return None

async def drain_events(ws, count=10, timeout=10):
    """Read up to `count` events, printing each one."""
    for _ in range(count):
        raw = await recv_with_timeout(ws, timeout=timeout)
        if raw is None:
            break
        if isinstance(raw, bytes):
            print(f"  [tts_audio] received {len(raw)} bytes of audio")
            continue
        evt = json.loads(raw)
        t = evt.get("type", "?")

        if t == "llm_token":
            print(f"\n  🤖 AI: {evt['text']}")
        elif t == "agent_selected":
            print(f"  📌 [agent_selected] → {evt['agent']}")
        elif t == "language_detected":
            print(f"  🌐 [language_detected] → {evt['language']}")
        elif t == "intent_detected":
            print(f"  🎯 [intent_detected] → {evt['intent']}  (confidence: {evt.get('confidence', '?')})")
        elif t == "customer_authenticated":
            print(f"  ✅ [customer_authenticated] → {evt['customer_id']}")
        elif t == "tool_result":
            print(f"  🔧 [tool_result] → {evt.get('tool', '?')}: {evt.get('result', '')}")
        elif t == "human_escalation":
            print(f"  🚨 [HUMAN ESCALATION] → {evt.get('reason', '')}")
        elif t == "call_summary":
            print(f"  📋 [call_summary] → {evt['summary']}")
        elif t == "error":
            print(f"  ❌ [error] → {evt.get('message', '')}")
        else:
            print(f"  📨 [{t}] → {json.dumps(evt)[:120]}")

async def send_and_listen(ws, user_text, label="User"):
    """Send a text_input and drain response events."""
    print(f"\n  👤 {label}: {user_text}")
    await ws.send(json.dumps({"type": "text_input", "text": user_text}))
    await drain_events(ws, count=15, timeout=20)

async def run_demo():
    uri = "ws://localhost:8000/ws/call/demo-call-001?channel=phone"

    print()
    print(DIVIDER)
    print("  AMBRANE AI — Enterprise Call Flow Demo")
    print(DIVIDER)
    print("  Connecting to ws://localhost:8000 ...")

    try:
        async with websockets.connect(uri, origin="http://localhost:8000", open_timeout=10) as ws:
            print("  ✅ WebSocket connected!\n")

            # Phase 1: Receive greeting + pre-call events
            print(f"{DIVIDER}")
            print("  PHASE 1: Pre-Call Setup + Receptionist Greeting")
            print(f"{DIVIDER}")
            await drain_events(ws, count=8, timeout=20)

            # Phase 2: Order tracking query
            print(f"\n{DIVIDER}")
            print("  PHASE 2: Order Tracking Query (Shopify + RAG + Qwen)")
            print(f"{DIVIDER}")
            await send_and_listen(ws, "My order #AMB-12345 is not delivered yet. Where is it?")

            # Phase 3: Complaint → should escalate
            print(f"\n{DIVIDER}")
            print("  PHASE 3: Complaint → Human Escalation Trigger")
            print(f"{DIVIDER}")
            await send_and_listen(ws, "This is the worst service ever! I am extremely angry and want to complain!")

            print(f"\n{DIVIDER}")
            print("  DEMO COMPLETE ✅")
            print(f"{DIVIDER}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"  ❌ Server rejected connection: HTTP {e.status_code}")
        print("     Make sure uvicorn is running and CORS allows localhost:8000")
    except ConnectionRefusedError:
        print("  ❌ Connection refused — is the backend running on port 8000?")
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(run_demo())

