import os
import re
import io
import zipfile
import tempfile
import subprocess
from pathlib import Path

import streamlit as st
import yt_dlp
from faster_whisper import WhisperModel

st.set_page_config(page_title="ClipForge AI", page_icon="🎬", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family: Inter, sans-serif;}
.stApp {background: radial-gradient(circle at 10% 0%, #18243d 0, #090d18 42%, #080b12 100%); color:#f4f7fb;}
.block-container {max-width:1150px; padding-top:2.2rem;}
.hero {padding:30px 32px; border:1px solid #26334b; border-radius:24px; background:linear-gradient(120deg,rgba(37,55,87,.95),rgba(15,22,38,.95)); margin-bottom:22px;}
.hero h1 {font-size:2.65rem; letter-spacing:-.06em; margin:0; color:#fff;}
.hero p {color:#aebbd0; font-size:1.05rem; margin:.55rem 0 0;}
.panel {padding:22px; border:1px solid #26334b; border-radius:18px; background:rgba(16,23,38,.78);}
.small {color:#91a1b9; font-size:.9rem;}
div.stButton>button, div.stDownloadButton>button {border-radius:12px; font-weight:700; min-height:3rem;}
</style>
<div class="hero">
  <div style="font-size:13px;color:#91b5ff;font-weight:800;letter-spacing:.18em">AI VIDEO WORKFLOW</div>
  <h1>🎬 ClipForge AI</h1>
  <p>Turn long videos into short, vertical clips ready for Reels, Shorts and TikTok.</p>
</div>
""", unsafe_allow_html=True)

@st.cache_resource
def load_model():
    return WhisperModel("base", device="cpu", compute_type="int8")

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-2500:] or "Command failed")
    return p.stdout

def download_video(url, folder):
    opts = {"format":"bestvideo[height<=1080]+bestaudio/best[height<=1080]", "outtmpl":str(Path(folder)/"source.%(ext)s"), "merge_output_format":"mp4", "quiet":True, "no_warnings":True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        mp4 = str(Path(folder)/"source.mp4")
        return mp4 if os.path.exists(mp4) else filename, info

def make_clips(video, segments, folder, max_clips, min_len, max_len):
    outputs=[]
    for i, seg in enumerate(segments[:max_clips], 1):
        start=float(seg["start"]); end=float(seg["end"])
        duration=max(1.0,min(max_len,end-start))
        if duration < min_len: continue
        out=str(Path(folder)/f"clip_{i:02d}.mp4")
        vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        run(["ffmpeg","-y","-ss",str(start),"-i",video,"-t",str(duration),"-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","128k","-movflags","+faststart",out])
        if os.path.exists(out): outputs.append(out)
    return outputs

with st.container():
    left, right = st.columns([1.35, .8], gap="large")
    with left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Build your clips")
        source_mode=st.radio("Video source", ["Upload a video from your phone", "Use a video URL"], horizontal=True)
        uploaded=st.file_uploader("Choose video file", type=["mp4","mov","mkv","webm","avi"]) if source_mode.startswith("Upload") else None
        url=st.text_input("Video URL", placeholder="Paste a direct/public video link") if source_mode.startswith("Use") else ""
        a,b=st.columns(2)
        with a: count=st.slider("Number of clips",1,10,5)
        with b: language=st.selectbox("Transcript language",["Auto detect","English","French","Arabic","Spanish","German"])
        c,d=st.columns(2)
        with c: min_len=st.slider("Minimum clip length (sec)",10,30,15)
        with d: max_len=st.slider("Maximum clip length (sec)",20,90,45)
        generate=st.button("✨ Generate viral clips", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("What you get")
        st.markdown("- **AI transcription** with Whisper\n- **Suggested moments** from transcript segments\n- **Vertical 9:16 exports** in MP4\n- **Preview and ZIP download**")
        st.markdown('<p class="small">Tip: YouTube may block automated downloads. Upload the video file from your phone for the most reliable results.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

if generate:
    if not uploaded and not url.strip(): st.error("Please upload a video or paste a URL first.")
    else:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                status=st.status("Preparing your video…", expanded=True)
                if uploaded:
                    suffix=Path(uploaded.name).suffix or ".mp4"
                    video=str(Path(tmp)/("uploaded_video"+suffix))
                    with open(video,"wb") as out: out.write(uploaded.getbuffer())
                    video_title=uploaded.name
                else:
                    video, info=download_video(url.strip(),tmp)
                    video_title=info.get("title","video")
                status.write(f"Video ready: {video_title}")
                status.write("Transcribing audio with Whisper…")
                model=load_model()
                lang_map={"Auto detect":None,"English":"en","French":"fr","Arabic":"ar","Spanish":"es","German":"de"}
                segments, meta=model.transcribe(video, language=lang_map[language], vad_filter=True)
                rows=list(segments)
                if not rows: raise RuntimeError("No speech detected in this video.")
                # Rank transcript moments by speech density and useful duration.
                ranked=[]
                for s in rows:
                    text=s.text.strip()
                    dur=max(1.0,s.end-s.start)
                    score=min(len(text)/dur,22)+min(dur/8,2)
                    ranked.append({"start":max(0,s.start-1),"end":s.end+2,"text":text,"score":score})
                ranked.sort(key=lambda x:x["score"], reverse=True)
                chosen=[]
                for item in ranked:
                    if any(abs(item["start"]-x["start"])<max_len for x in chosen): continue
                    item["end"]=min(item["end"],item["start"]+max_len)
                    if item["end"]-item["start"]>=min_len: chosen.append(item)
                    if len(chosen)>=count: break
                if not chosen: raise RuntimeError("Could not find enough speech sections. Try shorter minimum length.")
                chosen.sort(key=lambda x:x["start"])
                status.write(f"Creating {len(chosen)} vertical clips…")
                clips=make_clips(video,chosen,tmp,count,min_len,max_len)
                status.update(label="Your clips are ready", state="complete", expanded=False)
                st.success(f"Created {len(clips)} clips from: {video_title}")
                zipbuf=io.BytesIO()
                with zipfile.ZipFile(zipbuf,"w",zipfile.ZIP_DEFLATED) as z:
                    for clip in clips: z.write(clip,arcname=Path(clip).name)
                st.download_button("⬇️ Download all clips (ZIP)",zipbuf.getvalue(),file_name="ClipForge_AI_Clips.zip",mime="application/zip",use_container_width=True)
                for clip in clips:
                    with st.expander(Path(clip).name): st.video(clip)
        except Exception as e:
            st.error(f"Could not generate clips: {e}")

st.markdown("<p style='text-align:center;color:#74839a;margin-top:3rem'>CLIPFORGE AI · Create more from every video</p>",unsafe_allow_html=True)
