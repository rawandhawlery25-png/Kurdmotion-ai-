import streamlit as st

st.set_page_config(page_title="KurdMotion AI", page_icon="🎬")

st.title("🎬 KurdMotion AI")
st.write("وێنەکەت بکە بە ڤیدیۆ")

image = st.file_uploader(
    "وێنە هەڵبژێرە",
    type=["png", "jpg", "jpeg"]
)

prompt = st.text_area(
    "وەسفی جوڵە بنووسە",
    placeholder="ئەگەر بەتاڵی بهێڵیت، دواتر AI وەسفی گونجاو هەڵدەبژێرێت."
)

duration = st.selectbox("ماوەی ڤیدیۆ", ["5 چرکە", "10 چرکە"])
ratio = st.selectbox("قەبارە", ["9:16", "16:9", "1:1"])

if image:
    st.image(image, caption="وێنەی هەڵبژێردراو", use_container_width=True)

st.info("ئەمە ڕووکاری سەرەتاییە؛ بەشی دروستکردنی ڤیدیۆی ڕاستەقینەی AI هێشتا پێویستی بە زیادکردنی خزمەتگوزاری AI هەیە.")
