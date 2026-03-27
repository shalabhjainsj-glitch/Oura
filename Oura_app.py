import streamlit as st
import streamlit.components.v1 as st_components
import pandas as pd
import urllib.parse
import json
import time
import random
import string
import re
import io
import os
import requests
import base64
from PIL import Image

# --- नया फायरबेस सिस्टम (सिर्फ डेटाबेस के लिए) ---
import firebase_admin
from firebase_admin import credentials, firestore

try:
    import pytesseract
except ImportError:
    pass

GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# --- Firebase को चालू करना ---
if not firebase_admin._apps:
    try:
        firebase_secrets = st.secrets["FIREBASE_JSON"]
        if isinstance(firebase_secrets, str):
            cleaned_str = firebase_secrets.replace('“', '"').replace('”', '"')
            key_dict = json.loads(cleaned_str, strict=False)
        else:
            key_dict = dict(firebase_secrets)
        
        if 'private_key' in key_dict:
            key_dict['private_key'] = key_dict['private_key'].replace('\\n', '\n')
            
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"🚨 Firebase सेटअप में गलती: {e}")

db = firestore.client()

def upload_image_to_imgbb(file_bytes):
    try:
        imgbb_key = st.secrets.get("IMGBB_API_KEY")
        if not imgbb_key:
            st.error("🚨 ImgBB की चाबी तिजोरी (Secrets) में नहीं मिली!")
            return None
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": imgbb_key, "image": base64.b64encode(file_bytes).decode('utf-8')}
        res = requests.post(url, data=payload)
        if res.status_code == 200: return res.json()["data"]["url"]
        else: return None
    except Exception as e: return None

def dummy_delete_image(url): pass

def compress_image(image_bytes):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        if pil_img.mode != 'RGB': pil_img = pil_img.convert('RGB')
        max_width = 800
        if pil_img.width > max_width:
            ratio = max_width / float(pil_img.width)
            new_height = int((float(pil_img.height) * float(ratio)))
            pil_img = pil_img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        compressed_io = io.BytesIO()
        pil_img.save(compressed_io, format='JPEG', quality=75)
        return compressed_io.getvalue(), pil_img
    except Exception as e: return image_bytes, None

def load_config():
    try:
        doc = db.collection('settings').document('config').get()
        if doc.exists: return doc.to_dict()
    except: pass
    return {
        "admin_whatsapp": "919891587437", "phonepe_upi": "", "paytm_upi": "", "gpay_upi": "", "bhim_upi": "", 
        "has_banner": False, "has_logo": False, "free_delivery_tag": True, "sellers": {}, "banner_url": "", "logo_url": ""
    }

def save_config(config):
    db.collection('settings').document('config').set(config)

current_config = load_config()
if "sellers" not in current_config: current_config["sellers"] = {}

app_icon_url = current_config.get("logo_url", "🛍️") if current_config.get("has_logo") else "🛍️"

st.set_page_config(page_title="Oura - Wholesale", page_icon=app_icon_url, layout="wide")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            div[data-testid="stDecoration"] {visibility: hidden; height: 0%; display: none;}
            
            /* --- JioMart स्टाइल: हमेशा दिखने वाली (Fixed) टॉप बास्केट --- */
            div[data-testid="stPopover"] {
                position: fixed !important;
                top: 15px !important;
                right: 15px !important;
                z-index: 999999 !important;
            }

            div[data-testid="stPopover"] > button {
                background: linear-gradient(135deg, #0288d1, #01579b) !important;
                color: white !important;
                border-radius: 50px !important;
                padding: 10px 20px !important;
                border: 2px solid white !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
                transition: transform 0.2s !important;
            }
            
            div[data-testid="stPopover"] > button p {
                font-size: 16px !important;
                margin: 0 !important;
                font-weight: 900 !important;
                color: white !important;
            }
            
            div[data-testid="stPopover"] > button:active {
                transform: scale(0.95) !important;
            }
            
            /* मुख्य कंटेंट को थोड़ा नीचे धकेलना ताकि बास्केट के पीछे न छिपे */
            .block-container {
                padding-top: 80px !important; 
            }
            /* ----------------------------------------------------------- */
            
            .swipe-gallery {
                display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding-bottom: 5px;
                -webkit-overflow-scrolling: touch; scrollbar-width: none;
            }
            .swipe-gallery::-webkit-scrollbar { display: none; }
            .swipe-gallery a { scroll-snap-align: center; flex: 0 0 100%; max-width: 100%; text-decoration: none; }
            .swipe-img { width: 100%; height: 300px; object-fit: contain; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #eee; }
            
            .category-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 10px 0; }
            .category-box { border-radius: 12px; padding: 10px 5px; text-align: center; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; height: 75px; text-decoration: none !important; box-shadow: 0 2px 5px rgba(0,0,0,0.06); line-height: 1.3; overflow: hidden; transition: transform 0.1s; border: 1px solid rgba(0,0,0,0.05); }
            .category-box:active { transform: scale(0.95); }
            
            @keyframes glowing {
              0% { box-shadow: 0 0 5px #25D366; }
              50% { box-shadow: 0 0 20px #25D366, 0 0 30px #25D366; transform: scale(1.05); }
              100% { box-shadow: 0 0 5px #25D366; }
            }
            #oura-wa-btn {
                position: fixed; bottom: 120px; right: 15px; background-color: #25D366; color: white !important; padding: 12px 18px; border-radius: 50px; font-size: 16px; font-weight: bold; text-decoration: none !important; z-index: 9999999; display: flex; align-items: center; gap: 8px; animation: glowing 2s infinite; cursor: grab; border: 2px solid white; user-select: none; touch-action: none;
            }
            #oura-wa-btn:active { cursor: grabbing; }
            
            .seller-btn { background: linear-gradient(135deg, #FF9800, #F57C00); color: white !important; padding: 10px 15px; border-radius: 8px; text-decoration: none !important; font-weight: bold; display: inline-block; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

expected_columns = ["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_Path", "Free_Delivery", "Seller_Name"]

@st.cache_data(ttl=5)
def load_products():
    try:
        docs = db.collection('products').stream()
        data = [doc.to_dict() for doc in docs]
        if data: return pd.DataFrame(data)
    except: pass
    return pd.DataFrame(columns=expected_columns)

products_df = load_products()

if "cat" in st.query_params: st.session_state.selected_category = st.query_params["cat"]
else: st.session_state.selected_category = None

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'seller_logged_in' not in st.session_state: st.session_state.seller_logged_in = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'share_msg' not in st.session_state: st.session_state.share_msg = None
if 'share_img_path' not in st.session_state: st.session_state.share_img_path = None

if st.session_state.seller_logged_in:
    seller_name = st.session_state.seller_logged_in
    valid_sellers = current_config.get("sellers", {}).values()
    if seller_name not in valid_sellers:
        st.session_state.seller_logged_in = None
        st.error("⚠️ आपका सेलर टोकन एडमिन द्वारा ब्लॉक या डिलीट कर दिया गया है!")
        st.rerun()

# =========================================================================
# --- फ्लोटिंग कार्ट (हमेशा टॉप राइट में रहेगी) ---
# =========================================================================
cart_item_count = sum(item['qty'] for item in st.session_state.cart.values()) if st.session_state.cart else 0
with st.popover(f"🛒 बास्केट ({cart_item_count})"):
    st.markdown("### 🛒 आपकी बास्केट")
    if not st.session_state.cart:
        st.info("बास्केट अभी खाली है।")
    else:
        total = 0
        msg = "🧾 *Oura - Kaccha Bill* 🧾\n\n"
        count = 1
        
        for k, item in list(st.session_state.cart.items()):
            subtotal = item['price'] * item['qty']
            total += subtotal
            
            cart_col1, cart_col2, cart_col3 = st.columns([2, 5, 2])
            with cart_col1:
                if item.get('img_link'): st.image(item['img_link'])
                else: st.write("📷")
            with cart_col2:
                st.write(f"**{item['name']}**")
                st.write(f"{item['qty']} x ₹{item['price']} = ₹{subtotal}")
            with cart_col3:
                # पक्का इलाज 3: हटाते ही तुरंत गायब
                if st.button("❌", key=f"top_del_{k}", help="आइटम हटाएँ"):
                    del st.session_state.cart[k]
                    st.toast("🗑️ आइटम हटा दिया गया!")
                    st.rerun() 
                    
            st.markdown("---")
            
            msg += f"{count}. {item['name']} ({item['qty']} x ₹{item['price']}) = ₹{subtotal}\n"
            if item.get('img_link'): msg += f"👉 फोटो: {item['img_link']}\n"
            count += 1
            
        show_fd = current_config.get("free_delivery_tag", True)
        if show_fd: msg += f"\n💰 *कुल बिल:* ₹{total}\n⚠️ *होलसेल (बॉक्स) ऑर्डर पर कोरियर चार्ज एक्स्ट्रा।*\n"
        else: msg += f"\n💰 *कुल बिल:* ₹{total}\n⚠️ *ट्रांसपोर्ट व पैकिंग एक्स्ट्रा।*\n"
            
        st.success(f"**कुल बिल: ₹{total}**")
        
        with st.expander("📍 डिलीवरी की जानकारी (चेकआउट)"):
            cust_name = st.text_input("आपका नाम (Optional)", key="c_name")
            cust_mobile = st.text_input("मोबाईल नंबर (Optional)", key="c_mob")
            cust_address = st.text_area("पूरा पता (Optional)", key="c_add")
            
            final_msg = msg + f"\n\n📍 *डिलीवरी की जानकारी:*\n👤 नाम: {cust_name if cust_name else 'WhatsApp पर बताएंगे'}\n📞 मोबाईल: {cust_mobile if cust_mobile else 'WhatsApp पर बताएंगे'}\n🏠 पता: {cust_address if cust_address else 'WhatsApp पर बताएंगे'}\n"
            
            wa_link = f"https://wa.me/{current_config['admin_whatsapp']}?text={urllib.parse.quote(final_msg)}"
            st.markdown(f'''<a href="{wa_link}" target="_blank" style="display:block; text-align:center; background-color:#25D366; color:white; padding:12px; border-radius:8px; text-decoration:none; font-size:16px; font-weight:bold;">✅ WhatsApp पर ऑर्डर भेजें</a>''', unsafe_allow_html=True)

        if st.button("🗑️ पूरी बास्केट खाली करें", use_container_width=True):
            st.session_state.cart = {}
            st.toast("🗑️ बास्केट खाली हो गई!")
            st.rerun()
# =========================================================================

# --- टॉप हेडर और लोगो ---
col_logo, col_login = st.columns([7, 3])
with col_logo:
    if current_config.get("has_banner", False) and current_config.get("banner_url"):
        try: st.image(current_config["banner_url"], use_container_width=True)
        except: st.title("🛍️ Oura Wholesale")
    else:
        st.title("🛍️ Oura Wholesale")

with col_login:
    st.write("")
    if not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
        if st.button("🔒 लॉगिन"): st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button("🚪 लॉगआउट"):
            st.session_state.admin_logged_in = False
            st.session_state.seller_logged_in = None
            st.session_state.show_login = False
            st.rerun()

# --- सर्च बार ---
search_query = st.text_input("🔍 सर्च करें", placeholder="उत्पाद ढूँढें (जैसे: Watch)...")

multi_color_marquee = """
<div style="background: linear-gradient(90deg, #FF512F, #DD2476, #8A2387, #E94057, #F27121); padding: 12px; border-radius: 8px; margin-bottom: 20px; margin-top: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
    <marquee behavior="scroll" direction="left" scrollamount="7" style="color: white; font-size: 16px; font-weight: bold; font-family: sans-serif; letter-spacing: 0.5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
        🏭 क्या आप भी एक मैन्युफैक्चरर या होलसेलर हैं? आइए, Oura के साथ मिलकर अपने बिज़नेस को नई ऊंचाइयों पर ले जाएं! 🚀
    </marquee>
</div>
"""
st.markdown(multi_color_marquee, unsafe_allow_html=True)

if st.session_state.show_login and not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    with st.container(border=True):
        st.subheader("दुकान में लॉगिन करें")
        login_type = st.radio("लॉगिन का प्रकार चुनें:", ["सेलर (Seller)", "मालिक / एडमिन (Admin)"], horizontal=True)
        if login_type == "मालिक / एडमिन (Admin)":
            password = st.text_input("एडमिन पासवर्ड डालें", type="password")
            if st.button("लॉगिन करें"):
                try: correct_password = st.secrets["ADMIN_PASSWORD"]
                except: correct_password = None
                if correct_password and password == correct_password:
                    st.session_state.admin_logged_in = True; st.session_state.show_login = False; st.rerun()
                else: st.error("❌ गलत पासवर्ड!")
        else:
            seller_token = st.text_input("अपना सेलर टोकन (Token) डालें", type="password")
            if st.button("लॉगिन करें"):
                sellers_dict = current_config.get("sellers", {})
                if seller_token in sellers_dict:
                    st.session_state.seller_logged_in = sellers_dict[seller_token]; st.session_state.show_login = False; st.rerun()
                else: st.error("❌ गलत टोकन! कृपया एडमिन से संपर्क करें।")
    st.markdown("---")

if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success("✅ आप एडमिन (मालिक) के रूप में लॉगिन हैं।")
        tab_add, tab_banner, tab_settings = st.tabs(["➕ नया उत्पाद", "🖼️ बैनर व लोगो", "⚙️ सेटिंग्स"])
    else:
        st.success(f"🏪 स्वागत है: {st.session_state.seller_logged_in} (Seller)")
        tab_add, = st.tabs(["➕ नया उत्पाद"])
    
    with tab_add:
        # [ADD PRODUCT FORM REMAINS SAME AS BEFORE]
        with st.form("add_product", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                new_id = st.text_input("ID (यूनिक रखें)")
                new_name = st.text_input("नाम")
                new_price = st.number_input("सिंगल पीस रेट", min_value=1)
            with col_b:
                new_w_qty = st.number_input("होलसेल कम से कम पीस", min_value=1, value=10)
                new_w_price = st.number_input("होलसेल / बॉक्स रेट (प्रति पीस)", min_value=1)
                new_free_delivery = st.selectbox("सिंगल पीस डिलीवरी", ["फ्री डिलीवरी", "कोरियर चार्ज एक्स्ट्रा"])
            
            if st.session_state.seller_logged_in: new_seller_name = st.session_state.seller_logged_in
            else: new_seller_name = st.text_input("सेलर / ब्रांड का नाम")

            existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
            cat_options = ["नयी केटेगरी बनाएं..."] + existing_cats
            selected_cat = st.selectbox("केटेगरी चुनें", cat_options)
            if selected_cat == "नयी केटेगरी बनाएं...": final_cat = st.text_input("नई केटेगरी का नाम लिखें")
            else: final_cat = selected_cat
                
            uploaded_imgs = st.file_uploader("फोटो अपलोड करें (अधिकतम 3)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
            submit_btn = st.form_submit_button("उत्पाद सेव करें")
            
            if submit_btn and new_id and new_name and uploaded_imgs and final_cat:
                with st.spinner("फोटो सेव हो रही है..."):
                    image_paths = []
                    for img in uploaded_imgs:
                        compressed_bytes, _ = compress_image(img.getvalue())
                        img_url = upload_image_to_imgbb(compressed_bytes)
                        if img_url: image_paths.append(img_url)

                    final_path_str = "|".join(image_paths)
                    is_free = True if new_free_delivery == "फ्री डिलीवरी" else False
                    data = {"ID": new_id, "Name": new_name, "Price": new_price, "Wholesale_Price": new_w_price, "Wholesale_Qty": new_w_qty, "Category": final_cat, "Image_Path": final_path_str, "Free_Delivery": is_free, "Seller_Name": new_seller_name}
                    db.collection('products').document(str(new_id)).set(data)
                    load_products.clear()
                    st.success("✅ उत्पाद सेव हो गया!")
                    st.rerun()

    if st.session_state.admin_logged_in:
        with tab_banner:
            st.subheader("🖼️ ऐप का बैनर (Top Banner)")
            new_banner = st.file_uploader("नया बैनर चुनें", type=["jpg", "png", "jpeg"], key="banner_upload")
            if st.button("बैनर सेव करें") and new_banner:
                with st.spinner("बैनर सेव हो रहा है..."):
                    compressed_bytes, _ = compress_image(new_banner.getvalue())
                    b_url = upload_image_to_imgbb(compressed_bytes)
                    if b_url:
                        current_config["has_banner"] = True; current_config["banner_url"] = b_url
                        save_config(current_config); st.rerun()
            if current_config.get("has_banner", False):
                if st.button("❌ बैनर हटाएं"):
                    current_config["has_banner"] = False; current_config["banner_url"] = ""
                    save_config(current_config); st.rerun()
    
        with tab_settings:
            new_wa = st.text_input("WhatsApp नंबर", value=current_config.get("admin_whatsapp", "919891587437"))
            show_free_delivery = st.checkbox("✅ बाय डिफ़ॉल्ट 'फ्री डिलीवरी' दिखाएं?", value=current_config.get("free_delivery_tag", True))
            if st.button("⚙️ सभी सेटिंग्स सेव करें"):
                current_config["admin_whatsapp"] = new_wa; current_config["free_delivery_tag"] = show_free_delivery
                save_config(current_config); st.success("सेव हो गई!"); st.rerun()

def show_swipe_gallery(path_str):
    if not path_str: return []
    paths = [p.strip() for p in path_str.split('|') if p.strip()]
    if not paths: return []
    html_code = '<div class="swipe-gallery">'
    for src in paths: html_code += f'<a href="{src}" target="_blank"><img src="{src}" class="swipe-img" loading="lazy"></a>'
    html_code += '</div>'
    st.markdown(html_code, unsafe_allow_html=True)
    return paths

def show_product_card(row, idx, prefix):
    prefix_idx = f"{prefix}_{idx}"
    with st.container(border=True):
        image_path_str = str(row.get("Image_Path", ""))
        all_paths = show_swipe_gallery(image_path_str)
        img_link_for_wa = all_paths[0] if all_paths else ""
            
        st.write(f"**{row.get('Name', 'Unknown')}**")
        
        seller_val = row.get("Seller_Name")
        if pd.notna(seller_val) and str(seller_val).strip() != "":
            st.markdown(f"🏪 **सेलर / ब्रांड:** <span style='color:#E65100; font-weight:bold;'>{str(seller_val).strip()}</span>", unsafe_allow_html=True)
        
        try: w_qty = int(float(row.get('Wholesale_Qty', 1)))
        except: w_qty = 1
        try: retail_price = row.get('Price', 0)
        except: retail_price = 0
        try: w_price = int(float(row.get('Wholesale_Price', retail_price)))
        except: w_price = retail_price
        
        show_fd = current_config.get("free_delivery_tag", True)
        if w_qty > 1:
            st.markdown(f"🛵 **सिंगल पीस:** ₹{retail_price} <br> 📦 **होलसेल:** ₹{w_price} *(कम से कम {w_qty} पीस)*", unsafe_allow_html=True)
        else:
            st.markdown(f"🛵 **रेट:** ₹{retail_price}")
            
        qty = st.number_input("मात्रा (पीस)", min_value=1, value=1, key=f"q_{prefix_idx}")
        
        # पक्का इलाज 1: दबाते ही तुरंत बास्केट अपडेट और पेज रिफ्रेश
        if st.button("🛒 कार्ट में डालें", key=f"b_{prefix_idx}"):
            final_price = w_price if qty >= w_qty else retail_price
            st.session_state.cart[prefix_idx] = {"name": row.get('Name', 'Item'), "price": final_price, "qty": qty, "img_link": img_link_for_wa}
            st.toast("✅ कार्ट में जुड़ गया! ऊपर बास्केट चेक करें।")
            st.rerun() 
            
        show_edit_delete = False
        if st.session_state.admin_logged_in: show_edit_delete = True
        elif st.session_state.seller_logged_in and st.session_state.seller_logged_in == str(seller_val).strip(): show_edit_delete = True
            
        if show_edit_delete:
            with st.expander("✏️ बदलें या डिलीट करें"):
                if st.button("❌ डिलीट करें", key=f"del_{prefix_idx}"):
                    db.collection('products').document(str(row['ID'])).delete()
                    load_products.clear(); st.rerun()

if products_df.empty: st.info("जल्द ही नए उत्पाद आएंगे!")
else:
    if search_query:
        st.subheader(f"'{search_query}' के रिजल्ट:")
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        if filtered_df.empty: st.warning("कुछ नहीं मिला।")
        else:
            cols = st.columns(3)
            for idx, row in filtered_df.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "search")
    
    elif st.session_state.selected_category is None:
        st.subheader("🛍️ कैटेगरीज")
        valid_categories = products_df['Category'].dropna().unique().tolist()
        if len(valid_categories) == 0: st.write("अभी कोई कैटेगरी नहीं है।")
        else:
            cat_cols = st.columns(2)
            for i, cat in enumerate(valid_categories):
                with cat_cols[i % 2]:
                    # पक्का इलाज 2: बटन से कैटेगरी बदलें, पेज रीसेट नहीं होगा
                    if st.button(cat, key=f"btn_cat_{i}", use_container_width=True):
                        st.session_state.selected_category = cat
                        st.query_params["cat"] = cat
                        st.rerun()
            
    else:
        col_back, col_title = st.columns([3, 7])
        with col_back:
            if st.button("🔙 पीछे जाएं", use_container_width=True):
                st.query_params.clear()
                st.session_state.selected_category = None
                st.rerun()
        with col_title: st.subheader(f"📂 {st.session_state.selected_category}")

        cat_products = products_df[products_df['Category'] == st.session_state.selected_category]
        if cat_products.empty: st.write("कोई उत्पाद नहीं है।")
        else:
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "cat_view")

st.markdown("<br><br><br>", unsafe_allow_html=True) 

admin_wa_number = current_config.get("admin_whatsapp", "919891587437")
st.markdown(f'''<a id="oura-wa-btn" href="https://wa.me/{admin_wa_number}" target="_blank" title="WhatsApp Us">📞 {admin_wa_number}</a>''', unsafe_allow_html=True)

drag_js_code = """
<script>
const parentDoc = window.parent.document;
const btn = parentDoc.getElementById('oura-wa-btn');
if (btn && !btn.dataset.draggable) {
    btn.dataset.draggable = "true";
    let isDragging = false, startY, startTop;
    const onStart = (e) => {
        if(e.type === 'mousedown' || e.type === 'touchstart') {
            isDragging = true; startY = e.touches ? e.touches[0].clientY : e.clientY;
            startTop = btn.offsetTop; btn.style.animation = 'none'; btn.style.transition = 'none';
        }
    };
    const onMove = (e) => {
        if (!isDragging) return;
        e.preventDefault(); 
        let currentY = e.touches ? e.touches[0].clientY : e.clientY;
        let newTop = startTop + (currentY - startY);
        if (newTop < 80) newTop = 80;
        if (newTop > parentDoc.documentElement.clientHeight - 80) newTop = parentDoc.documentElement.clientHeight - 80;
        btn.style.top = newTop + 'px'; btn.style.bottom = 'auto'; 
    };
    const onEnd = () => { isDragging = false; btn.style.animation = 'glowing 2s infinite'; };
    btn.addEventListener('touchstart', onStart, {passive: false});
    parentDoc.addEventListener('touchmove', onMove, {passive: false});
    parentDoc.addEventListener('touchend', onEnd);
    btn.addEventListener('mousedown', onStart);
    parentDoc.addEventListener('mousemove', onMove);
    parentDoc.addEventListener('mouseup', onEnd);
    btn.addEventListener('click', (e) => { if (Math.abs(btn.offsetTop - startTop) > 10) e.preventDefault(); });
}
</script>
"""
st_components.html(drag_js_code, height=0, width=0)
