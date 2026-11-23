
import streamlit as st
import tempfile
import subprocess
import requests
import re
import imageio_ffmpeg

from pathlib import Path
from PIL import Image, ImageOps
from gradio_client import Client, handle_file

# =====================================
# KURDMOTION AI 2.0
# =====================================

SPACE_ID = "zerogpu-aoti/wan2-2-fp8da-aoti-faster"
TTS_URL = "https://www.kurdishtts.com/api/tts-proxy"
SPEAKERS_URL = "https://www.kurdishtts.com/api/get-speakers?model_version=v3"

st.set_page_config(
    page_title="KurdMotion AI",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 KurdMotion AI 2.0")
st.write("وێنەکەت بکە بە ڤیدیۆی جووڵەدار و گفتوگۆی کوردی")

# =====================================
# VIDEO ENGINE
# =====================================

@st.cache_resource
def get_client():
    return Client(SPACE_ID)


# =====================================
# VOICE ENGINE
# =====================================

@st.cache_data(ttl=3600)
def get_voices():
    allowed = {"sorani_85", "sorani_214"}

    response = requests.get(SPEAKERS_URL, timeout=30)
    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict):
        data = data.get("speakers", [])

    voices = {}

    for voice in data:
        if voice.get("id") in allowed:
            name = voice.get("name", voice["id"])
            gender = voice.get("gender", "")

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


# =====================================
# PROMPT DIALOGUE READER
# =====================================

def extract_dialogue(prompt):
    pattern = r'["“](.*?)["”]|«(.*?)»'

    matches = re.findall(
        pattern,
        prompt,
        re.DOTALL
    )

    dialogues = []

    for first, second in matches:
        spoken = (first or second).strip()

        if spoken:
            dialogues.append(spoken)

    return dialogues


# =====================================
# EMOTION SYSTEM
# =====================================

EMOTIONS = {
    "ئاسایی": "natural calm facial expression and natural body movement",
    "خۆشی": "happy expression, natural smile and joyful body language",
    "تووڕەیی": "angry facial expression, serious eyes and strong body language",
    "خەم": "sad facial expression, gentle movements and emotional eyes",
    "شڵەژان": "nervous facial expression, worried eyes and slightly restless movements",
    "خۆشەویستی": "warm affectionate expression, gentle eyes and soft movements",
    "سەرسوڕمان": "surprised facial expression and natural surprised reaction"
}


# =====================================
# FFMPEG
# =====================================

def run_ffmpeg(args):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    result = subprocess.run(
        [ffmpeg, "-y"] + args,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])


# =====================================
# USER INTERFACE
# =====================================

st.subheader("📷 وێنە")

image = st.file_uploader(
    "وێنە هەڵبژێرە",
    type=["png", "jpg", "jpeg"]
)

st.subheader("✍️ پرۆمپت و کردار")

prompt = st.text_area(
    "پرۆمپتی خۆت بنووسە",
    height=160,
    placeholder=(
        'The girl looks at the boy and says in Sorani Kurdish: '
        '"سڵاو، چۆنی؟"'
    )
)

emotion = st.selectbox(
    "🎭 هەستی کاراکتەر",
    list(EMOTIONS.keys())
)

ratio = st.selectbox(
    "📐 قەبارەی ڤیدیۆ",
    ["9:16 — ستوونی", "16:9 — ئاسۆیی"]
)

duration = st.selectbox(
    "⏱️ ماوەی ڤیدیۆ",
    [3.5, 5.0]
)

# =====================================
# DIALOGUE SETTINGS
# =====================================

st.divider()
st.subheader("🗣️ گفتوگۆی کوردی")

st.caption(
    'دەتوانیت قسە لە پرۆمپتدا بنووسیت بە شێوەی "سڵاو، چۆنی؟" '
    "یان لەم دوو خانەیە بەکاری بهێنیت."
)

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
except Exception as error:
    voices = {}
    st.warning(f"لیستی دەنگەکان بار نەبوو: {error}")

if voices:
    voice_ids = list(voices.keys())

    voice_one = st.selectbox(
        "🎙️ دەنگی کەسی یەکەم",
        voice_ids,
        format_func=lambda x: voices[x]
    )

    voice_two = st.selectbox(
        "🎙️ دەنگی کەسی دووەم",
        voice_ids,
        index=min(1, len(voice_ids) - 1),
        format_func=lambda x: voices[x]
    )

else:
    voice_one = "sorani_85"
    voice_two = "sorani_214"

st.divider()


# =====================================
# IMAGE PREVIEW
# =====================================

preview = None

if image:
    original = Image.open(image).convert("RGB")

    if ratio.startswith("9:16"):
        target_size = (480, 832)
    else:
        target_size = (832, 480)

    preview = ImageOps.fit(original, target_size)

    st.image(
        preview,
        caption="وێنەی ئامادەکراو بۆ ڤیدیۆ"
    )


# =====================================
# GENERATE VIDEO
# =====================================

if st.button(
    "🎬 دروستکردنی ڤیدیۆ",
    type="primary",
    disabled=image is None
):

    # Read prompt dialogue
    prompt_dialogues = extract_dialogue(prompt)

    # Prepare all speech
    speech_items = []

    for spoken in prompt_dialogues:
        speech_items.append((spoken, voice_one))

    if dialogue_one.strip():
        speech_items.append(
            (dialogue_one.strip(), voice_one)
        )

    if dialogue_two.strip():
        speech_items.append(
            (dialogue_two.strip(), voice_two)
        )

    has_dialogue = bool(speech_items)

    # Read API key
    try:
        api_key = st.secrets.get(
            "KURDISH_TTS_API_KEY",
            ""
        )
    except Exception:
        api_key = ""

    if has_dialogue and not api_key:
        st.error(
            "KURDISH_TTS_API_KEY لە Streamlit Secrets دانەنراوە."
        )
        st.stop()

    try:
        with tempfile.TemporaryDirectory() as temp_folder:

            folder = Path(temp_folder)

            image_path = folder / "input.png"
            video_path = folder / "silent_video.mp4"
            final_path = folder / "KurdMotion_AI.mp4"

            preview.save(image_path, format="PNG")

            # Add emotion instructions
            motion_prompt = (
                prompt.strip()
                or "Make this image come alive naturally."
            )

            motion_prompt += (
                ". " + EMOTIONS[emotion]
                + ". Natural human movement, "
                "preserve the character's identity."
            )

            # ---------------------------------
            # STEP 1: VIDEO GENERATION
            # ---------------------------------

            with st.spinner("🎬 ڤیدیۆ دروست دەکرێت..."):

                client = get_client()

                job = client.submit(
                    input_image=handle_file(str(image_path)),
                    prompt=motion_prompt,
                    steps=4,
                    negative_prompt=(
                        "blurry, distorted, low quality, "
                        "extra limbs, deformed face"
                    ),
                    duration_seconds=float(duration),
                    guidance_scale=1,
                    guidance_scale_2=1,
                    seed=42,
                    randomize_seed=True,
                    api_name="/generate_video"
                )

                result = job.result()

                generated_path = (
                    result[0]
                    if isinstance(result, (tuple, list))
                    else result
                )

                if not generated_path or not Path(generated_path).exists():
                    raise RuntimeError(
                        "ڤیدیۆ دروست نەبوو."
                    )

                video_path.write_bytes(
                    Path(generated_path).read_bytes()
                )

            # ---------------------------------
            # STEP 2: SPEECH GENERATION
            # ---------------------------------

            if has_dialogue:

                st.info("🎙️ دەنگی کوردی دروست دەکرێت...")

                audio_files = []

                for index, (spoken_text, speaker) in enumerate(speech_items):

                    audio_file = folder / f"voice_{index+1}.wav"

                    make_speech(
                        spoken_text,
                        speaker,
                        api_key,
                        audio_file
                    )

                    audio_files.append(audio_file)

                # ---------------------------------
                # STEP 3: JOIN AUDIO FILES
                # ---------------------------------

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
                        "-c:a", "pcm_s16le",
                        str(audio_path)
                    ])

                # ---------------------------------
                # STEP 4: MERGE AUDIO AND VIDEO
                # ---------------------------------

                st.info("🎧 دەنگ بە ڤیدیۆوە دەبەسترێتەوە...")

                run_ffmpeg([
                    "-i", str(video_path),
                    "-i", str(audio_path),
                    "-filter_complex",
                    "[0:v]tpad=stop_mode=clone:stop_duration=120[v]",
                    "-map", "[v]",
                    "-map", "1:a",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-shortest",
                    "-movflags", "+faststart",
                    str(final_path)
                ])

            else:

                final_path.write_bytes(
                    video_path.read_bytes()
                )

            # ---------------------------------
            # STEP 5: SHOW FINAL VIDEO
            # ---------------------------------

            video_bytes = final_path.read_bytes()

            st.success("🎉 ڤیدیۆکەت ئامادەیە!")

            st.video(video_bytes)

            st.download_button(
                "⬇️ داگرتنی ڤیدیۆ (MP4)",
                data=video_bytes,
                file_name="KurdMotion_AI.mp4",
                mime="video/mp4"
            )

    except Exception as error:

        st.error("هەڵەیەک ڕوویدا.")

        st.code(str(error))


st.caption(
    "KurdMotion AI 2.0 — Video, Kurdish TTS and Emotion Prompts"
)
