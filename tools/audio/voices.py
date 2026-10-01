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
    # ---- Mumbai / Dharavi -------------------------------------------------------------------
    ("mumbai", "male", "बाजू हटो! साइड दो!", "Baaju hato! Side do!"),
    ("mumbai", "male", "क्या रे, किधर जा रहा है?", "Kya re, kidhar ja raha hai?"),
    ("mumbai", "male", "अरे भिडू, सुन ना!", "Arre bhidu, sun na!"),
    ("mumbai", "male", "ताज़ी सब्ज़ी! आज का बेस्ट भाव!", "Taazi sabzi! Aaj ka best bhaav!"),
    ("mumbai", "male", "टमाटर, भिंडी, मिर्ची, ले लो!", "Tamatar, bhindi, mirchi, le lo!"),
    ("mumbai", "male", "गणपति बाप्पा मोरया!", "Ganpati Bappa Morya!"),
    ("mumbai", "male", "मंगल मूर्ति मोरया!", "Mangal Murti Morya!"),
    ("mumbai", "male", "चल ना यार, लेट हो रहा है।", "Chal na yaar, late ho raha hai."),
    ("mumbai", "male", "भाई, ये मुंबई है। यहाँ सब फास्ट है।", "Bhai, yeh Mumbai hai. Yahaan sab fast hai."),
    ("mumbai", "male", "पाव भाजी खाएगा क्या?", "Pav bhaaji khaayega kya?"),
    ("mumbai", "female", "अरे बाबा, बारिश आ रही है!", "Arre baba, baarish aa rahi hai!"),
    ("mumbai", "female", "भैया, पानी की लाइन कब आएगी?", "Bhaiya, paani ki line kab aayegi?"),
    ("mumbai", "female", "सब्ज़ी कितने की दी?", "Sabzi kitne ki di?"),
    ("mumbai", "female", "छाता ले लो, बहुत तेज़ है!", "Chhaata le lo, bahut tez hai!"),
    ("kids_ball", "kid", "भैया, बॉल वापस दो ना!", "Bhaiya, ball wapas do na!"),
    ("kids_ball", "kid", "अंकल, बॉल फेंको!", "Uncle, ball phenko!"),
    ("kids_ball", "kid", "ओ भाई, बॉल इधर! इधर!", "O bhai, ball idhar! Idhar!"),
    ("kids_cheer", "kid", "येएए! थैंक यू भैया!", "Yayyy! Thank you bhaiya!"),
    ("kids_cheer", "kid", "क्या थ्रो था! येएए!", "Kya throw tha! Yayyy!"),
    ("kids_play", "kid", "आउट है! आउट!", "Out hai! Out!"),
    ("kids_play", "kid", "चौका! चौका!", "Chauka! Chauka!"),
    ("kids_play", "kid", "अब मेरी बैटिंग है!", "Ab meri batting hai!"),
    ("player_chai", "player", "बॉस, एक कटिंग चाय देना! वो फेमस वाली।", "Boss, ek cutting chai dena! Woh famous waali."),
    ("chai_vendor", "male", "ये लो भाई, गरम गरम कटिंग। दस रुपये।", "Ye lo bhai, garam garam cutting. Das rupaye."),
    ("chai_call", "male", "चाय! गरम चाय! कटिंग चाय!", "Chai! Garam chai! Cutting chai!"),
    ("chai_call", "male", "आओ भाई, बढ़िया चाय पियो!", "Aao bhai, badhiya chai piyo!"),
]

# speaker variants (voice, pitch, rate)
VARIANTS = {
    "male": [("hi-IN-MadhurNeural", "-12Hz", "+6%"), ("hi-IN-MadhurNeural", "+6Hz", "+12%"), ("hi-IN-MadhurNeural", "-25Hz", "-4%")],
    "female": [("hi-IN-SwaraNeural", "+0Hz", "+8%"), ("hi-IN-SwaraNeural", "-14Hz", "+2%")],
    "kid": [("hi-IN-SwaraNeural", "+55Hz", "+14%"), ("hi-IN-MadhurNeural", "+85Hz", "+16%"), ("hi-IN-SwaraNeural", "+35Hz", "+10%")],
    "player": [("hi-IN-MadhurNeural", "-6Hz", "+4%")],
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
