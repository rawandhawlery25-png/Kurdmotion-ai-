
import streamlit as st
import tempfile
from pathlib import Path
from gradio_client import Client, handle_file

SPACE_ID = "zerogpu-aoti/wan2-2-fp8da-aoti-faster"

st.set_page_config(page_title="KurdMotion AI", page_icon="🎬")
st.title("🎬 KurdMotion AI")
st.write("وێنەکەت بکە بە ڤیدیۆی جووڵەدار")

@st.cache_resource
def get_client():
    return Client(SPACE_ID)

image = st.file_uploader("وێنە هەڵبژێرە", type=["png", "jpg", "jpeg"])

prompt = st.text_area(
    "وەسفی جووڵە بنووسە",
    placeholder="بۆ نموونە: کچەکە بە هێواشی دەڕوات."
)

duration = st.selectbox("ماوەی ڤیدیۆ", [3.5, 5.0], index=0)

if image:
    st.image(image, caption="وێنەی هەڵبژێردراو", use_container_width=True)

if st.button("🎬 دروستکردنی ڤیدیۆ", type="primary", disabled=image is None):
    default_prompt = "make this image come alive, cinematic motion, smooth animation"
    motion_prompt = prompt.strip() or default_prompt

    suffix = Path(image.name).suffix.lower() or ".png"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_image:
            temp_image.write(image.getvalue())
            image_path = temp_image.name

        with st.spinner("تکایە چاوەڕێ بکە؛ ڤیدیۆکە دروست دەکرێت..."):
            client = get_client()
            job = client.submit(
                input_image=handle_file(image_path),
                prompt=motion_prompt,
                steps=4,
                negative_prompt="blurry, distorted, low quality, extra limbs",
                duration_seconds=float(duration),
                guidance_scale=1,
                guidance_scale_2=1,
                seed=42,
                randomize_seed=True,
                api_name="/generate_video",
            )
            result = job.result()

        video_path = result[0] if isinstance(result, (tuple, list)) else result
        if not video_path or not Path(video_path).exists():
            st.error("ڤیدیۆکە بە سەرکەوتوویی نەگەڕایەوە. تکایە دووبارە هەوڵ بدە.")
        else:
            st.success("ڤیدیۆکەت ئامادەیە!")
            st.video(video_path)
            st.download_button(
                "⬇️ داگرتنی ڤیدیۆ (MP4)",
                data=Path(video_path).read_bytes(),
                file_name="KurdMotion_AI.mp4",
                mime="video/mp4",
            )
    except Exception as error:
        st.error("خزمەتگوزاری AI ئێستا بەردەست نییە یان چاوەڕوانی زۆرە.")
        st.caption(f"هەڵە: {error}")
    finally:
        try:
            Path(image_path).unlink(missing_ok=True)
        except Exception:
            pass

st.caption("تێبینی: دروستکردنی ڤیدیۆ بە خزمەتگوزاری دەرەکی Wan 2.2 ئەنجام دەدرێت. خزمەتگوزارییەکە ڕەنگە چاوەڕوانی و سنووری بەکارهێنانی هەبێت.")
