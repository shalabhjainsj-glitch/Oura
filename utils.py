import streamlit as st
import requests
import base64
import io
from PIL import Image

def upload_image_to_imgbb(file_bytes):
    try:
        imgbb_key = st.secrets.get("IMGBB_API_KEY")
        if not imgbb_key:
            st.error("🚨 ImgBB की चाबी तिजोरी (Secrets) में नहीं मिली!")
            return None
            
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": imgbb_key,
            "image": base64.b64encode(file_bytes).decode('utf-8')
        }
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            return res.json()["data"]["url"]
        else:
            st.error("फोटो अपलोड फेल हो गई।")
            return None
    except Exception as e:
        st.error(f"एरर: {e}")
        return None

def compress_image(image_bytes):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        max_width = 800
        if pil_img.width > max_width:
            ratio = max_width / float(pil_img.width)
            new_height = int((float(pil_img.height) * float(ratio)))
            pil_img = pil_img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        compressed_io = io.BytesIO()
        pil_img.save(compressed_io, format='JPEG', quality=75)
        return compressed_io.getvalue(), pil_img
    except Exception as e:
        return image_bytes, None

def t(en_text, hi_text):
    return en_text if st.session_state.lang == 'en' else hi_text

def safe_int(val, default=1):
    try:
        if val is None or str(val).strip() == "": return default
        return int(float(val))
    except: return default

def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "": return default
        return float(val)
    except: return default
