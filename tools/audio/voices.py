#!/usr/bin/env python3
"""Generate the crowd's Hindi voice lines with neural TTS (edge-tts, hi-IN voices), several speaker
variants per gender via pitch/rate, then convert to 48 kHz mono WAV with a light street EQ.
Writes ~/gta-india/assets/audio/voice/*.wav and voice_lines.json (category, gender, roman text)."""
import asyncio
import json
import os
import subprocess

import edge_tts

OUT = os.path.expanduser("~/gta-india/assets/audio/voice")

# (category, gender, devanagari, roman subtitle)
LINES = [
    # ambient chatter / shouts (male)
    ("ambient", "male", "अरे कहाँ गए ओए!", "Arre kahaan gaye oye!"),
    ("ambient", "male", "पागल है क्या?", "Paagal hai kya?"),
    ("ambient", "male", "कहाँ जाना है भैया?", "Kahaan jaana hai bhaiya?"),
    ("ambient", "male", "चाय पियोगे? गरम गरम!", "Chai piyoge? Garam garam!"),
    ("ambient", "male", "अरे सुनो तो भाई!", "Arre suno to bhai!"),
    ("ambient", "male", "भैया, रिक्शा चाहिए?", "Bhaiya, rickshaw chahiye?"),
    ("ambient", "male", "जल्दी चलो, आरती का टाइम हो गया!", "Jaldi chalo, aarti ka time ho gaya!"),
    ("ambient", "male", "अबे ओए, इधर आ!", "Abe oye, idhar aa!"),
    ("ambient", "male", "पाँच रुपये कम करो ना भैया.", "Paanch rupaye kam karo na bhaiya."),
    ("ambient", "male", "हर हर महादेव!", "Har Har Mahadev!"),
    ("ambient", "male", "गंगा मैया की जय!", "Ganga Maiya ki jai!"),
    ("ambient", "male", "अरे यार, आज बहुत भीड़ है.", "Arre yaar, aaj bahut bheed hai."),
    ("ambient", "male", "ओए छोटू, दो कटिंग चाय ला!", "Oye chhotu, do cutting chai la!"),
    ("ambient", "male", "नाव चाहिए? पूरा घाट घुमा देंगे!", "Naav chahiye? Poora ghaat ghuma denge!"),
    ("ambient", "male", "बनारस है भाई, यहाँ सब चलता है.", "Banaras hai bhai, yahaan sab chalta hai."),
    ("ambient", "male", "पान खाओगे? बनारसी पान!", "Paan khaoge? Banarasi paan!"),
    ("ambient", "male", "अरे भाई साहब, मोबाइल रिचार्ज करवा लो!", "Arre bhai sahab, mobile recharge karwa lo!"),
    ("ambient", "male", "कल मैच देखा? क्या मारा यार!", "Kal match dekha? Kya maara yaar!"),
    # ambient (female)
    ("ambient", "female", "अरे सुनो जी, कहाँ जा रहे हो?", "Arre suno ji, kahaan ja rahe ho?"),
    ("ambient", "female", "भैया, फूल लोगे? ताज़ा गेंदा!", "Bhaiya, phool loge? Taaza genda!"),
    ("ambient", "female", "चलो जल्दी, देर हो रही है.", "Chalo jaldi, der ho rahi hai."),
    ("ambient", "female", "हाय राम, कितनी गर्मी है!", "Haaye Ram, kitni garmi hai!"),
    ("ambient", "female", "बेटा, संभल के.", "Beta, sambhal ke."),
    ("ambient", "female", "माला ले लो, बस दस रुपये!", "Maala le lo, bas das rupaye!"),
    ("ambient", "female", "अरे कहाँ गई वो लड़की?", "Arre kahaan gayi woh ladki?"),
    ("ambient", "female", "दीया जलाना है, माचिस है किसी के पास?", "Diya jalaana hai, maachis hai kisi ke paas?"),
    # bump insults
    ("bump", "male", "देखके चल ना!", "Dekhke chal na!"),
    ("bump", "male", "अंधा है क्या?", "Andha hai kya?"),
    ("bump", "male", "अबे ओए! देख के!", "Abe oye! Dekh ke!"),
    ("bump", "male", "धक्का क्यों मार रहा है?", "Dhakka kyun maar raha hai?"),
    ("bump", "male", "पागल है क्या? दिखता नहीं?", "Paagal hai kya? Dikhta nahin?"),
    ("bump", "male", "आँखें घर पे छोड़ आया क्या?", "Aankhen ghar pe chhod aaya kya?"),
    ("bump", "male", "अरे! ध्यान कहाँ है तेरा?", "Arre! Dhyaan kahaan hai tera?"),
    ("bump", "male", "चल हट! बड़ा आया!", "Chal hat! Bada aaya!"),
    ("bump", "female", "देखके चलो ना!", "Dekhke chalo na!"),
    ("bump", "female", "अंधे हो क्या?", "Andhe ho kya?"),
    ("bump", "female", "हाय राम! धक्का क्यों दिया?", "Haaye Ram! Dhakka kyun diya?"),
    ("bump", "female", "तमीज़ नहीं है क्या?", "Tameez nahin hai kya?"),
    ("bump", "female", "अरे बाबा, संभल के!", "Arre baba, sambhal ke!"),
    # reckless riding near people
    ("bike", "male", "अबे, गाड़ी धीरे चला!", "Abe, gaadi dheere chala!"),
    ("bike", "male", "मरवाएगा क्या?", "Marwayega kya?"),
    ("bike", "male", "हॉर्न बजा ना भाई!", "Horn baja na bhai!"),
    ("bike", "female", "धीरे चलाओ! बच्चे हैं यहाँ!", "Dheere chalao! Bachche hain yahaan!"),
    # reactions to the player jumping in the Ganga
    ("swim", "male", "अरे वो देखो, गंगा में कूद गया!", "Arre woh dekho, Ganga mein kood gaya!"),
    ("swim", "male", "पागल है, खाना ले के तैर रहा है!", "Paagal hai, khaana le ke tair raha hai!"),
    ("swim", "female", "हाय राम, डूब जाएगा!", "Haaye Ram, doob jaayega!"),
    # for the delivery guy
    ("ambient", "male", "ओए डिलीवरी वाले! मेरा खाना कब आएगा?", "Oye delivery waale! Mera khaana kab aayega?"),
]

# speaker variants (voice, pitch, rate)
VARIANTS = {
    "male": [("hi-IN-MadhurNeural", "-12Hz", "+6%"), ("hi-IN-MadhurNeural", "+6Hz", "+12%"), ("hi-IN-MadhurNeural", "-25Hz", "-4%")],
    "female": [("hi-IN-SwaraNeural", "+0Hz", "+8%"), ("hi-IN-SwaraNeural", "-14Hz", "+2%")],
}


async def synth(text, voice, pitch, rate, path):
    c = edge_tts.Communicate(text, voice, pitch=pitch, rate=rate)
    await c.save(path)


async def main():
    os.makedirs(OUT, exist_ok=True)
    meta = []
    for i, (cat, gender, dev, roman) in enumerate(LINES):
        for v, (voice, pitch, rate) in enumerate(VARIANTS[gender][:2 if cat == "ambient" else 3]):
            name = f"V_{cat}_{gender}_{i:02d}_{v}"
            mp3 = os.path.join(OUT, name + ".mp3")
            wav = os.path.join(OUT, name + ".wav")
            if not os.path.exists(wav):
                await synth(dev, voice, pitch, rate, mp3)
                # outdoor street voice: band-limit a little, slight compression, normalise
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "48000",
                                "-af", "highpass=f=120,lowpass=f=7500,acompressor=threshold=-18dB:ratio=3,loudnorm=I=-16",
                                wav], check=True)
                os.remove(mp3)
            meta.append({"name": name, "category": cat, "gender": gender, "text": roman})
    json.dump(meta, open(os.path.join(OUT, "voice_lines.json"), "w"), indent=1, ensure_ascii=False)
    print("voice lines", len(meta))


asyncio.run(main())
