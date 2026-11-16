import streamlit as st
import subprocess, os, whisper, numpy as np, wave, urllib.parse
st.set_page_config(page_title="Viral Clipper", page_icon="🔥", layout="wide")
st.title("🔥 Viral Clipper")
st.caption("Paste link → Pick length + amount → Get clips → See score → Post")
VIDEO_URL = st.text_input("YouTube Link", placeholder="https://youtu.be/...")
col_a, col_b = st.columns(2)
with col_a:
    NUM_CLIPS = st.slider("Amount of Clips", 1, 10, 5)
with col_b:
    CLIP_LENGTH = st.selectbox("Length of Each Clip", [10, 15, 30, 45, 60], index=0)
    st.caption(f"Total: {NUM_CLIPS} x {CLIP_LENGTH}s = {NUM_CLIPS * CLIP_LENGTH}s")
if st.button("Generate Clips 🚀") and VIDEO_URL:
    with st.spinner(f"Finding {NUM_CLIPS} x {CLIP_LENGTH}s clips..."):
        if not os.path.exists("input.mp4"):
            subprocess.run(["yt-dlp","-f","bestvideo[height<=720]+bestaudio/best[height<=720]","--merge-output-format","mp4","-o","input.mp4",VIDEO_URL], capture_output=True)
        subprocess.run(["ffmpeg","-y","-i","input.mp4","-vn","-ac","1","-ar","16000","full_audio.wav"], capture_output=True)
        w = wave.open("full_audio.wav")
        n = w.getnframes(); rate = w.getframerate()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(float)
        per_sec = np.array([np.mean(np.abs(data[i*rate:(i+1)*rate])) if (i+1)*rate <= len(data) else 0 for i in range(len(data)//rate)])
        GAP = CLIP_LENGTH + 15
        peaks = []
        for idx in np.argsort(per_sec)[::-1]:
            if all(abs(idx - p) > GAP for p in peaks):
                peaks.append(int(idx))
            if len(peaks) == 20: break
        model = whisper.load_model("tiny")
        VIRAL_WORDS = ["oh my god","what","no way","bro","look","watch","wow","holy","damn","insane","crazy","no","wait","oh","ha","lol"]
        scored = []
        for p in peaks:
            start = max(0, p-2)
            subprocess.run(["ffmpeg","-y","-ss",str(start),"-i","input.mp4","-t",str(CLIP_LENGTH),"-vn","-ac","1","-ar","16000","tmp.wav"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            r = model.transcribe("tmp.wav", word_timestamps=False, fp16=False)
            text = r["text"].lower()
            loud = per_sec[p] / (np.max(per_sec) + 1)
            word_s = sum(1 for kw in VIRAL_WORDS if kw in text) * 0.3
            density = min(len(text.split()) / 15, 1) * 0.3
            total = loud + word_s + density
            virality = min(int(total * 50), 100)
            scored.append({"start": start, "score": virality, "loud": int(loud*100), "words": int(word_s*100), "text": text.strip(), "length": CLIP_LENGTH})
        scored = sorted(scored, key=lambda x: x["score"], reverse=True)[:NUM_CLIPS]
        st.session_state["clips"] = scored
        st.session_state["clip_length"] = CLIP_LENGTH
        st.success(f"Found {len(scored)} clips!")
if "clips" in st.session_state:
    CLIP_LENGTH = st.session_state.get("clip_length", 10)
    def fmt_ass(t):
        h = int(t//3600); m = int((t%3600)//60); s = int(t%60); cs = int((t%1)*100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Phone,Arial Black,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,7,3,2,80,80,600,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    model = whisper.load_model("tiny")
    for i, c in enumerate(st.session_state["clips"], 1):
        st.divider()
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(f"Clip #{i} - Virality Score", f"{c['score']}/100")
            st.write(f"**Length:** {c['length']}s | **At:** {c['start']}s")
            if c['score'] >= 80: st.success("🔥 HIGH - Post first")
            elif c['score'] >= 60: st.warning("⚡ GOOD")
            else: st.info("📉 LOW - Filler")
            st.write(f"**Said:** {c['text'][:120]}")
            st.write(f"🔊 {c['loud']} | 💬 {c['words']}")
        name = f"opus_clip_{i}_{c['length']}s.mp4"
        if not os.path.exists(name):
            with st.spinner(f"Making Clip {i} ({c['length']}s)..."):
                subprocess.run(["ffmpeg","-y","-ss",str(c["start"]),"-i","input.mp4","-t",str(c["length"]),"-vn","-ac","1","-ar","16000",f"tmp_{i}.wav"], capture_output=True)
                result = model.transcribe(f"tmp_{i}.wav", word_timestamps=True, fp16=False)
                events = []
                for seg in result["segments"]:
                    words = seg.get("words", [])
                    if not words: continue
                    clean = [{"word": w["word"].strip().upper(), "start": w["start"], "end": w["end"]} for w in words if w["word"].strip()]
                    for j in range(0, len(clean), 3):
                        group = clean[j:j+3]
                        for k, wrd in enumerate(group):
                            parts = []
                            for kk, ww in enumerate(group):
                                if kk == k: parts.append("{\\c&H00FFFF&}" + ww["word"] + "{\\c&H00FFFFFF&}")
                                else: parts.append(ww["word"])
                            txt = " ".join(parts)
                            s = wrd["start"]; e = group[k+1]["start"] if k+1 < len(group) else wrd["end"]
                            if e <= s: e = s + 0.3
                            events.append(f"Dialogue: 0,{fmt_ass(s)},{fmt_ass(e)},Phone,,0,0,0,,{txt}")
                open(f"clip_{i}.ass","w").write(header + "\n".join(events))
                filter_str = f"[0:v]crop=iw:ih*0.88:0:0,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=clip_{i}.ass"
                subprocess.run(["ffmpeg","-y","-ss",str(c["start"]),"-i","input.mp4","-t",str(c["length"]),"-filter_complex",filter_str,"-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-movflags","+faststart",name], capture_output=True)
        with col2:
            st.video(name)
            caption = f"He did NOT expect that 😭 #gta6 #gta #fyp #viral #gaming - Score {c['score']}/100"
            st.text_area(f"Caption Clip {i}", caption, key=f"cap_{i}")
            st.download_button(f"⬇️ Download Clip {i} ({c['length']}s)", data=open(name,"rb").read(), file_name=name, mime="video/mp4", key=f"dl_{i}")
            st.write("**Post Manually:**")
            encoded = urllib.parse.quote(caption)
            b1, b2, b3, b4, b5 = st.columns(5)
            with b1: st.link_button("📘 Facebook", f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(VIDEO_URL)}&quote={encoded}")
            with b2: st.link_button("📸 Instagram", "https://www.instagram.com/reels/create/")
            with b3: st.link_button("🎵 TikTok", "https://www.tiktok.com/upload")
            with b4: st.link_button("▶️ YouTube", "https://www.youtube.com/upload")
            with b5: st.link_button("𝕏 Twitter", f"https://twitter.com/intent/tweet?text={encoded}")
