import streamlit as st
import pandas as pd

st.title("اختبار تشغيل Streamlit")
st.write("إذا ظهر هذا النص، فالتطبيق يعمل!")

uploaded_file = st.file_uploader("اختر ملف", type="txt")
if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    st.write(f"تم رفع ملف بحجم: {len(content)} حرف")
