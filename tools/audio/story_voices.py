#!/usr/bin/env python3
"""Voice the story dialogue (tools/story/saraswati_lines.py) with edge-tts hi-IN voices.
Writes ~/gta-india/assets/audio/story/S_Story_<scene>_<nn>.wav (48 kHz mono, light EQ)."""
import asyncio
import os
import subprocess
import sys

import edge_tts

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "story"))
from saraswati_lines import SCENES, VOICES  # noqa: E402

OUT = os.path.expanduser("~/gta-india/assets/audio/story")


async def main():
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for scene, lines in SCENES.items():
        for i, (speaker, _l, _roman, dev, _g, _s) in enumerate(lines):
            name = f"S_Story_{scene}_{i:02d}"
            wav = os.path.join(OUT, name + ".wav")
            if os.path.exists(wav) and "--force" not in sys.argv:
                continue
            voice, pitch, rate = VOICES[speaker]
            mp3 = os.path.join(OUT, name + ".mp3")
            await edge_tts.Communicate(dev, voice, pitch=pitch, rate=rate).save(mp3)
            # close-mic dialogue: gentle high-pass, a touch of compression, broadcast loudness;
            # Shankar's thoughts (vo) get a soft room tail
            af = "highpass=f=90,acompressor=threshold=-20dB:ratio=2.5,loudnorm=I=-15"
            if speaker == "vo":
                af = "highpass=f=110,aecho=0.8:0.5:40:0.18," + af
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "48000", "-af", af, wav], check=True)
            os.remove(mp3)
            n += 1
    print("story lines voiced", n)


asyncio.run(main())
