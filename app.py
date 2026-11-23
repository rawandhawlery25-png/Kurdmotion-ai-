
import streamlit as st
import tempfile
import subprocess
import requests
import imageio_ffmpeg
import re
from pathlib import Path
from PIL import Image, ImageOps
from gradio_client import Client, handle_file

SPACE_ID = "zerogpu-aoti/wan2-2-fp8da-aoti-faster"
TTS_URL = "https://www.kurdishtts.com/api/tts-proxy"

st.set_page_config(page_title="KurdMotion AI", page_icon="🎬")
st.title("🎬 KurdMotion AI")
st.write("وێنەکەت بکە بە ڤیدیۆی جووڵەدار و گفتوگۆی کوردی")

@st.cache_resource
def get_client():
    return Client(SPACE_ID)

@st.cache_data(ttl=3600)
def get_voices():
    allowed = {"sorani_85", "sorani_214"}
    response = requests.get(
        "https://www.kurdishtts.com/api/get-speakers?model_version=v3",
        timeout=30
    )
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict):
        data = data.get("speakers", [])

    voices = {}
    for voice in data:
        if voice.get("id") in allowed:
            gender = voice.get("gender", "")
            name = voice.get("name", voice["id"])
            voices[voice["id"]] = f"{name} — {gender}"

    return voices

def make_speech(text, speaker_id, api_key, output_path):
    response = requests.post(
        TTS_URL,
        headers={"x-api-key": api_key},
        json={
            "text": text,
            "speaker_id": speaker_id,
            "model_version": "v3",
            "dialect": "sorani",
            "format": "wav"
        },
        timeout=180
    )
    response.raise_for_status()
    Path(output_path).write_bytes(response.content)

def run_ffmpeg(args):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, "-y"] + args,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1500:])

image = st.file_uploader(
    "📷 وێنە هەڵبژێرە",
    type=["png", "jpg", "jpeg"]
)

ratio = st.selectbox(
    "📐 قەبارەی ڤیدیۆ",
    ["9:16 — ستوونی", "16:9 — ئاسۆیی"]
)

prompt = st.text_area(
    "وەسفی جووڵە بنووسە",
    placeholder="بۆ نموونە: کچەکە بە هێواشی دەڕوات."
)

duration = st.selectbox("ماوەی ڤیدیۆ", [3.5, 5.0])

st.divider()
st.subheader("🗣️ گفتوگۆی کوردی")

dialogue_one = st.text_area(
    "گفتوگۆی کەسی یەکەم",
    placeholder="سڵاو، چۆنی؟",
    max_chars=500
)

dialogue_two = st.text_area(
    "گفتوگۆی کەسی دووەم",
    placeholder="باشم، سوپاس.",
    max_chars=500
)

try:
    voices = get_voices()
except Exception:
    voices = {}

if voices:
    voice_ids = list(voices.keys())

    voice_one = st.selectbox(
        "دەنگی کەسی یەکەم",
        voice_ids,
        format_func=lambda x: voices[x],
        key="voice_one"
    )
    voice_two = st.selectbox(
        "دەنگی کەسی دووەم",
        voice_ids,
        format_func=lambda x: voices[x],
        key="voice_two"
    )
else:
    voice_one = "sorani_85"
    voice_two = "sorani_214"
    st.warning("لیستی دەنگەکان ئێستا بار نەبوو.")

st.caption("هەر خانەیەکی گفتوگۆ تا ٥٠٠ پیت وەردەگرێت.")

if image:
    original = Image.open(image).convert("RGB")

    if ratio.startswith("9:16"):
        target_size = (480, 832)
    else:
        target_size = (832, 480)

    preview = ImageOps.fit(original, target_size)
    st.image(preview, caption="وێنەی ئامادەکراو بۆ ڤیدیۆ")

if st.button(
    "🎬 دروستکردنی ڤیدیۆ",
    type="primary",
    disabled=image is None
):
    api_key = st.secrets.get("KURDISH_TTS_API_KEY", "")

    has_dialogue = bool(
        dialogue_one.strip() or dialogue_two.strip()
    )

    if has_dialogue and not api_key:
        st.error(
            "بۆ دروستکردنی دەنگ، کلیلی TTS دەبێت "
            "لە Streamlit Secrets دابنرێت."
        )
        st.stop()

    try:
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)

            image_path = folder / "input.png"
            video_path = folder / "silent_video.mp4"
            final_path = folder / "KurdMotion_AI.mp4"

            preview.save(image_path, format="PNG")

            motion_prompt = prompt.strip() or (
                "Make this image come alive, "
                "cinematic motion, smooth animation"
            )

            with st.spinner("ڤیدیۆکە دروست دەکرێت..."):
                client = get_client()

                job = client.submit(
                    input_image=handle_file(str(image_path)),
                    prompt=motion_prompt,
                    steps=4,
                    negative_prompt=(
                        "blurry, distorted, low quality, extra limbs"
                    ),
                    duration_seconds=float(duration),
                    guidance_scale=1,
                    guidance_scale_2=1,
                    seed=42,
                    randomize_seed=True,
                    api_name="/generate_video",
                )

                result = job.result()
                generated_path = (
                    result[0]
                    if isinstance(result, (tuple, list))
                    else result
                )

                if not generated_path or not Path(generated_path).exists():
                    raise RuntimeError("ڤیدیۆ دروست نەبوو.")

                video_path.write_bytes(
                    Path(generated_path).read_bytes()
                )

            audio_path = None

            if has_dialogue:
                st.info("دەنگی گفتوگۆ دروست دەکرێت...")

                audio_files = []

                if dialogue_one.strip():
                    p = folder / "voice_one.wav"
                    make_speech(
                        dialogue_one.strip(),
                        voice_one,
                        api_key,
                        p
                    )
                    audio_files.append(p)

                if dialogue_two.strip():
                    p = folder / "voice_two.wav"
                    make_speech(
                        dialogue_two.strip(),
                        voice_two,
                        api_key,
                        p
                    )
                    audio_files.append(p)

                if len(audio_files) == 1:
                    audio_path = audio_files[0]
                else:
                    list_path = folder / "audio_list.txt"
                    list_path.write_text(
                        "".join(
                            f"file '{p.as_posix()}'\n"
                            for p in audio_files
                        ),
                        encoding="utf-8"
                    )

                    audio_path = folder / "combined.wav"

                    run_ffmpeg([
                        "-f", "concat",
                        "-safe", "0",
                        "-i", str(list_path),
                        "-c", "copy",
                        str(audio_path)
                    ])

                st.info("دەنگ بە ڤیدیۆوە دەبەسترێتەوە...")

                run_ffmpeg([
                    "-i", str(video_path),
                    "-i", str(audio_path),
                    "-filter_complex",
                    "[0:v]tpad=stop_mode=clone:stop_duration=60[v]",
                    "-map", "[v]",
                    "-map", "1:a",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-shortest",
                    str(final_path)
                ])

            else:
                final_path.write_bytes(video_path.read_bytes())

            video_bytes = final_path.read_bytes()

            st.success("ڤیدیۆکەت ئامادەیە! 🎉")
            st.video(video_bytes)

            st.download_button(
                "⬇️ داگرتنی ڤیدیۆ (MP4)",
                data=video_bytes,
                file_name="KurdMotion_AI.mp4",
                mime="video/mp4"
            )

    except Exception as error:
        st.error("هەڵەیەک ڕوویدا. تکایە دووبارە هەوڵ بدە.")
        st.caption(str(error))

st.caption(
    "KurdMotion AI — Wan 2.2 و خزمەتگوزاری دەنگی کوردی"
)
