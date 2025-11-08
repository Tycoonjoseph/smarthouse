#!/usr/bin/env python3
"""
voice_switch.py

Requirements:
  pip install vosk sounddevice python-kasa

Usage:
  python voice_switch.py

Notes:
 - Replace PLUG_IP with your Kasa plug's IP address.
 - Use small Vosk model path on disk (MODEL_PATH).
 - Speak simple commands: "turn on the light", "turn off the light", "toggle light"
"""

import asyncio
import json
import queue
import sys
from kasa import SmartPlug
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# === CONFIG ===
MODEL_PATH = "model\vosk-model-small-en-us-0.15"  # update to your model path
SAMPLE_RATE = 16000
CHANNELS = 1
PLUG_IP = "192.168.0.1"   # <- REPLACE with your plug's IP
DEVICE_NAME = "livingroom" # logical name used in prints

# Keywords mapping (lowercase)
CMD_ON = ("turn on", "switch on", "on")
CMD_OFF = ("turn off", "switch off", "off")
CMD_TOGGLE = ("toggle", "switch")

# === END CONFIG ===

q = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status, file=sys.stderr)
    q.put(bytes(indata))

async def kasa_turn_on(ip):
    try:
        plug = SmartPlug(ip)
        await plug.update()
        await plug.turn_on()
        print(f"[KASA] Turned ON {ip}")
    except Exception as e:
        print("[KASA] Error turning on:", e)

async def kasa_turn_off(ip):
    try:
        plug = SmartPlug(ip)
        await plug.update()
        await plug.turn_off()
        print(f"[KASA] Turned OFF {ip}")
    except Exception as e:
        print("[KASA] Error turning off:", e)

async def kasa_toggle(ip):
    try:
        plug = SmartPlug(ip)
        await plug.update()
        if plug.is_on:
            await plug.turn_off()
            print(f"[KASA] Toggled OFF {ip}")
        else:
            await plug.turn_on()
            print(f"[KASA] Toggled ON {ip}")
    except Exception as e:
        print("[KASA] Error toggling:", e)

def contains_keyword(text, keywords):
    for kw in keywords:
        if kw in text:
            return True
    return False

async def voice_loop(model_path):
    if not Model(model_path):
        print("Model not found or cannot be loaded. Check MODEL_PATH.")
        return

    model = Model(model_path)
    rec = KaldiRecognizer(model, SAMPLE_RATE)
    rec.SetWords(False)

    # Start audio stream
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize = 8000, dtype='int16',
                           channels=CHANNELS, callback=audio_callback):
        print("Listening... Say: 'turn on the light' or 'turn off the light' etc.")
        sys.stdout.flush()

        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                res = rec.Result()
                j = json.loads(res)
                text = j.get("text", "").lower().strip()
                if not text:
                    continue
                print("Recognized:", text)

                # Simple command parsing
                # You can expand for multiple devices / names
                if contains_keyword(text, CMD_ON):
                    await kasa_turn_on(PLUG_IP)
                elif contains_keyword(text, CMD_OFF):
                    await kasa_turn_off(PLUG_IP)
                elif contains_keyword(text, CMD_TOGGLE):
                    await kasa_toggle(PLUG_IP)
                else:
                    # Optionally handle "turn on [device]" patterns
                    print("No known command in:", text)
            else:
                # partial = rec.PartialResult()
                # could print partial if you want
                pass

def main():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(voice_loop(MODEL_PATH))
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
