import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import urllib.parse
import json
import requests
import base64
import time

# --- 1. सबसे पहले सेटिंग्स और लोगो लोड करें ---
CONFIG_FILE = "config.json"
BANNER_FILE = "banner.png" 
LOGO_FILE = "logo.png"
DATA_FILE = "oura_products.csv"
GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {
        "admin_whatsapp": "919891587437", 
        "phonepe_upi": "",
        "paytm_upi": "",
        "gpay_upi": "",
        "bhim_upi": "",
        "upi_id": "",
        "has_banner": False,
        "has_logo": False
    }

current_config = load_config()

# 🌟 असली ऐप वाला लोगो (App Icon) 🌟
if current_config.get("has_logo", False):
    app_icon_url = f"{GITHUB_RAW_URL}{LOGO_FILE}?t={int(time.time())}"
else:
    app_icon_url = "🛍️"

# --- 2. ऐप का सेटअप (कस्टम लोगो के साथ) ---
st.set_page_config(page_title="Oura - Wholesale", page_icon=app_icon_url, layout="wide")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            div[data-testid="stDecoration"] {visibility: hidden; height: 0%; display: none;}
            
            /* 📸 स्मार्ट स्वाइप गैलरी */
            .swipe-gallery {
                display: flex;
                overflow-x: auto;
                scroll-snap-type: x mandatory;
                gap: 10px;
                padding-bottom: 5px;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
            }
            .swipe-gallery::-webkit-scrollbar {
                display: none;
            }
            .swipe-gallery a {
                scroll-snap-align: center;
                flex: 0 0 100%;
                max-width: 100%;
                text-decoration: none;
            }
            .swipe-img {
                width: 100%;
                height: 300px;
                object-fit: contain;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #eee;
            }
            
            /* 🌟 4-कॉलम स्मार्ट बॉक्स डिज़ाइन */
            .category-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 10px;
                padding: 10px 0;
            }
            .category-box {
                border-radius: 12px;
                padding: 10px 5px;
                text-align: center;
                font-size: 13px;
                font-weight: 700;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 75px; 
                text-decoration: none !important;
                box-shadow: 0 2px 5px rgba(0,0,0,0.06);
                line-height: 1.3;
                overflow: hidden;
                transition: transform 0.1s;
                border: 1px solid rgba(0,0,0,0.05);
            }
            .category-box:active {
                transform: scale(0.95);
            }
            
            /* 🚀 हवा में तैरने वाला (Floating) बैक बटन */
            .floating-back-btn {
                position: fixed;
                bottom: 25px;
                left: 50%;
                transform: translateX(-50%);
                background-color: #222222;
                color: #ffffff !important;
                padding: 12px 24px;
                border-radius: 40px;
                font-size: 15px;
                font-weight: 700;
                box-shadow: 0 6px 15px rgba(0,0,0,0.3);
                z-index: 999999;
                text-decoration: none !important;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: background-color 0.2s;
            }
            .floating-back-btn:active {
                background-color: #000000;
                transform: translateX(-50%) scale(0.95);
            }

            /* 📞 चमकता हुआ व्हाट्सएप बटन (Draggable) */
            @keyframes glowing {
              0% { box-shadow: 0 0 5px #25D366; }
              50% { box-shadow: 0 0 20px #25D366, 0 0 30px #25D366; transform: scale(1.05); }
              100% { box-shadow: 0 0 5px #25D366; }
            }
            #oura-wa-btn {
                position: fixed;
                bottom: 120px;
                right: 15px;
                background-color: #25D366;
                color: white !important;
                padding: 12px 18px;
                border-radius: 50px;
                font-size: 16px;
                font-weight: bold;
                text-decoration: none !important;
                z-index: 9999999;
                display: flex;
                align-items: center;
                gap: 8px;
                animation: glowing 2s infinite;
                cursor: grab;
                border: 2px solid white;
                user-select: none;
                touch-action: none;
            }
            #oura-wa-btn:active {
                cursor: grabbing;
            }
            
            /* 💳 मल्टी UPI बटन के लिए होवर इफ़ेक्ट */
            .multi-upi-btn {
                transition: transform 0.1s;
            }
            .multi-upi-btn:active {
                transform: scale(0.96);
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 🌟 मोबाइल 'Add to Home Screen' के लिए जावास्क्रिप्ट जादू 🌟
if current_config.get("has_logo", False) and app_icon_url != "🛍️":
    pwa_js = f"""
    <script>
    const parentHead = window.parent.document.head;
    
    let appleIcon = parentHead.querySelector('link[rel="apple-touch-icon"]');
    if (!appleIcon) {{
        appleIcon = window.parent.document.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        parentHead.appendChild(appleIcon);
    }}
    appleIcon.href = '{app_icon_url}';
    
    let mobIcon = parentHead.querySelector('link[rel="icon"][sizes="192x192"]');
    if (!mobIcon) {{
        mobIcon = window.parent.document.createElement('link');
        mobIcon.rel = 'icon';
        mobIcon.sizes = '192x192';
        parentHead.appendChild(mobIcon);
    }}
    mobIcon.href = '{app_icon_url}';
    </script>
    """
    components.html(pwa_js, height=0, width=0)

def save_to_github(file_path, content, commit_message):
    try:
        token = st.secrets["GITHUB_TOKEN"]
    except Exception as e:
        st.error("⚠️ GitHub Token नहीं मिला या गलत है! कृपया ऐप की सेटिंग्स चेक करें।")
        return False

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None
        
    if isinstance(content, str):
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    else:
        encoded_content = base64.b64encode(content).decode('utf-8')
        
    data = {"message": commit_message, "content": encoded_content, "branch": GITHUB_BRANCH}
    if sha:
        data["sha"] = sha
        
    put_response = requests.put(url, headers=headers, json=data)
    return put_response.status_code in [200, 201]

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    save_to_github(CONFIG_FILE, json.dumps(config, indent=4), "Update settings.json")

if not os.path.exists("images"):
    os.makedirs("images")

expected_columns = ["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_Path"]

def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=expected_columns)
        df.to_csv(DATA_FILE, index=False)
    else:
        try:
            df = pd.read_csv(DATA_FILE)
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = None
            df.to_csv(DATA_FILE, index=False)
        except:
            df = pd.DataFrame(columns=expected_columns)
            df.to_csv(DATA_FILE, index=False)

init_db()

@st.cache_data(ttl=5)
def load_products():
    try:
        df = pd.read_csv(DATA_FILE)
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None
        return df
    except:
        return pd.DataFrame(columns=expected_columns)

products_df = load_products()

# --- 🌟 सुरक्षित नेविगेशन 🌟 ---
if "cat" in st.query_params:
    st.session_state.selected_category = st.query_params["cat"]
else:
    st.session_state.selected_category = None

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'share_msg' not in st.session_state:
    st.session_state.share_msg = None
if 'share_img_path' not in st.session_state:
    st.session_state.share_img_path = None

if current_config.get("has_banner", False):
    if os.path.exists(BANNER_FILE):
        st.image(BANNER_FILE, use_container_width=True)
    else:
        banner_img_link = f"{GITHUB_RAW_URL}{BANNER_FILE}?t={int(time.time())}"
        try:
            st.image(banner_img_link, use_container_width=True)
        except:
            st.title("🛍️ Oura Wholesale")
else:
    st.title("🛍️ Oura Wholesale")

col1, col2 = st.columns([8, 2])
with col2:
    if not st.session_state.admin_logged_in:
        if st.button("🔒 एडमिन लॉगिन"):
            st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button("🚪 लॉगआउट"):
            st.session_state.admin_logged_in = False
            st.session_state.show_login = False
            st.rerun()

if st.session_state.show_login and not st.session_state.admin_logged_in:
    with st.container(border=True):
        st.subheader("एडमिन एक्सेस")
        password = st.text_input("पासवर्ड डालें", type="password")
        if st.button("लॉगिन करें"):
            try:
                correct_password = st.secrets["ADMIN_PASSWORD"]
            except:
                st.error("⚠️ सेटिंग्स में ADMIN_PASSWORD नहीं मिला!")
                correct_password = None
                
            if correct_password and password == correct_password:
                st.session_state.admin_logged_in = True
                st.session_state.show_login = False
                st.rerun()
            else:
                st.error("❌ गलत पासवर्ड!")
    st.markdown("---")

if st.session_state.admin_logged_in:
    st.success("✅ आप एडमिन हैं।")
    
    # 🌟 एडमिन टैब्स में लोगो का विकल्प जोड़ा गया है 🌟
    tab_add, tab_banner, tab_settings = st.tabs(["➕ नया उत्पाद", "🖼️ बैनर व लोगो", "⚙️ सेटिंग्स"])
    
    with tab_add:
        if st.session_state.share_msg:
            st.success("✅ शानदार! आपका नया उत्पाद दुकान में जुड़ गया है।")
            
            if st.session_state.share_img_path and os.path.exists(st.session_state.share_img_path):
                st.image(st.session_state.share_img_path, width=200)
                st.info("💡 **टिप:** इस फोटो को WhatsApp पर भेजने के लिए, फोटो पर उंगली दबाए रखें (Long Press) और **'Copy Image'** चुनें, फिर WhatsApp में Paste कर दें।")
            
            encoded_share = urllib.parse.quote(st.session_state.share_msg)
            wa_share_link = f"https://wa.me/?text={encoded_share}"
            
            st.markdown(f'''
            <a href="{wa_share_link}" target="_blank" style="display:inline-block; background-color:#25D366; color:white; padding:12px 25px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:16px; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                📢 WhatsApp पर शेयर करें
            </a>
            ''', unsafe_allow_html=True)
            
            st.write("*(नोट: WhatsApp लिंक में सीधे फोटो नहीं भेजता, लेकिन इस लिंक पर क्लिक करते ही ग्राहक सीधा इसी प्रोडक्ट की फोटो देखेगा!)*")
            
            if st.button("➕ एक और नया उत्पाद जोड़ें"):
                st.session_state.share_msg = None
                st.session_state.share_img_path = None
                st.rerun()
                
        else:
            with st.form("add_product", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    new_id = st.text_input("ID (यूनिक रखें)")
                    new_name = st.text_input("नाम")
                    new_price = st.number_input("सिंगल पीस रेट (कोरियर चार्ज जोड़कर लिखें)", min_value=1)
                with col_b:
                    new_w_qty = st.number_input("होलसेल कम से कम पीस", min_value=1, value=10)
                    new_w_price = st.number_input("होलसेल / बॉक्स रेट (प्रति पीस)", min_value=1)
                
                existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
                cat_options = ["नयी केटेगरी बनाएं..."] + existing_cats
                selected_cat = st.selectbox("केटेगरी चुनें", cat_options)
                
                if selected_cat == "नयी केटेगरी बनाएं...":
                    final_cat = st.text_input("नई केटेगरी का नाम लिखें (इमोजी 👕👟 भी लगा सकते हैं)")
                else:
                    final_cat = selected_cat
                    
                uploaded_imgs = st.file_uploader("फोटो अपलोड करें (अधिकतम 3)", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="add_imgs")
                submit_btn = st.form_submit_button("उत्पाद सेव करें")
                
                if submit_btn and new_id and new_name and uploaded_imgs and final_cat:
                    if len(uploaded_imgs) > 3:
                        st.error("⚠️ कृपया अधिकतम 3 फोटो ही चुनें।")
                    else:
                        with st.spinner("डेटा सेव हो रहा है..."):
                            image_paths = []
                            all_images_saved = True
                            
                            for idx, img in enumerate(uploaded_imgs):
                                safe_filename = img.name.replace(" ", "_").replace("(", "").replace(")", "")
                                timestamp = int(time.time())
                                final_filename = f"{new_id}_{idx}_{timestamp}_{safe_filename}"
                                path = f"images/{final_filename}"
                                img_bytes = img.getvalue()
                                try:
                                    with open(path, "wb") as f: f.write(img_bytes)
                                except: pass

                                if save_to_github(path, img_bytes, f"Add image {final_filename}"):
                                    image_paths.append(path)
                                else:
                                    all_images_saved = False
                                    break

                            if all_images_saved:
                                final_path_str = "|".join(image_paths)
                                df = load_products()
                                new_row = pd.DataFrame([[new_id, new_name, new_price, new_w_price, new_w_qty, final_cat, final_path_str]], columns=expected_columns)
                                df = pd.concat([df, new_row], ignore_index=True)
                                df.to_csv(DATA_FILE, index=False)
                                
                                with open(DATA_FILE, "r", encoding="utf-8") as f:
                                    csv_content = f.read()
                                if save_to_github(DATA_FILE, csv_content, f"Add product {new_name}"):
                                    load_products.clear()
                                    
                                    safe_cat_link = urllib.parse.quote(final_cat)
                                    app_link = f"https://ouraindia.streamlit.app/?cat={safe_cat_link}"
                                    
                                    msg = f"⚡ *मार्केट का सबसे हॉट आइटम अब Oura पर!* ⚡\n\nआपकी दुकान की सेल बढ़ाने के लिए हमने एक नया डिज़ाइन लॉन्च किया है!\n\n🎁 *नया उत्पाद:* {new_name}\n\nयह डिज़ाइन मार्केट में आते ही बिक रहा है। इससे पहले कि स्टॉक खत्म हो जाए...\n👇 *तुरंत रेट देखें और अपना माल बुक करें:*\n{app_link}"
                                    
                                    st.session_state.share_msg = msg
                                    st.session_state.share_img_path = image_paths[0] if image_paths else None
                                    st.rerun()

    with tab_banner:
        st.subheader("🖼️ ऐप का बैनर (Top Banner)")
        new_banner = st.file_uploader("नया बैनर चुनें", type=["jpg", "png", "jpeg"], key="banner_upload")
        if st.button("बैनर सेव करें") and new_banner:
            with st.spinner("बैनर सेव हो रहा है..."):
                banner_bytes = new_banner.getvalue()
                try:
                    with open(BANNER_FILE, "wb") as f: f.write(banner_bytes)
                except: pass
                if save_to_github(BANNER_FILE, banner_bytes, "Update banner image"):
                    current_config["has_banner"] = True
                    save_config(current_config)
                    st.success("✅ बैनर लग गया!")
                    time.sleep(1)
                    st.rerun()
                    
        if current_config.get("has_banner", False):
            if st.button("❌ बैनर हटाएं"):
                current_config["has_banner"] = False
                save_config(current_config)
                st.rerun()
                
        st.markdown("---")
        
        # 🌟 नया: होम स्क्रीन लोगो अपलोड करने का सेक्शन 🌟
        st.subheader("📱 ऐप का लोगो (App Icon)")
        st.info("यह लोगो तब दिखेगा जब ग्राहक ऐप को 'Add to Home Screen' करेंगे। (कृपया चकोर/Square फोटो ही चुनें)")
        new_logo = st.file_uploader("नया लोगो चुनें (Square)", type=["jpg", "png", "jpeg"], key="logo_upload")
        if st.button("लोगो सेव करें") and new_logo:
            with st.spinner("लोगो सेव हो रहा है..."):
                logo_bytes = new_logo.getvalue()
                try:
                    with open(LOGO_FILE, "wb") as f: f.write(logo_bytes)
                except: pass
                if save_to_github(LOGO_FILE, logo_bytes, "Update app logo"):
                    current_config["has_logo"] = True
                    save_config(current_config)
                    st.success("✅ आपका खुद का लोगो सेट हो गया!")
                    time.sleep(1)
                    st.rerun()
                    
        if current_config.get("has_logo", False):
            if st.button("❌ लोगो हटाएं"):
                current_config["has_logo"] = False
                save_config(current_config)
                st.rerun()

    with tab_settings:
        st.subheader("📱 संपर्क सेटिंग्स")
        new_wa = st.text_input("WhatsApp नंबर", value=current_config.get("admin_whatsapp", "919891587437"))
        
        st.markdown("---")
        st.subheader("💳 मल्टी UPI सेटिंग्स")
        st.info("आप अलग-अलग ऐप्स के लिए अलग-अलग UPI ID डाल सकते हैं। जो बॉक्स आप खाली छोड़ेंगे, उसका बटन ग्राहक को नहीं दिखेगा।")
        
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            new_phonepe = st.text_input("PhonePe UPI ID", value=current_config.get("phonepe_upi", current_config.get("upi_id", "")))
            new_paytm = st.text_input("Paytm UPI ID", value=current_config.get("paytm_upi", ""))
        with col_u2:
            new_gpay = st.text_input("Google Pay (GPay) UPI ID", value=current_config.get("gpay_upi", ""))
            new_bhim = st.text_input("BHIM UPI ID", value=current_config.get("bhim_upi", ""))
            
        if st.button("⚙️ सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["phonepe_upi"] = new_phonepe
            current_config["paytm_upi"] = new_paytm
            current_config["gpay_upi"] = new_gpay
            current_config["bhim_upi"] = new_bhim
            current_config["upi_id"] = "" 
            save_config(current_config)
            st.success("✅ नई UPI सेटिंग्स सेव हो गईं!")
            time.sleep(1)
            st.rerun()
    st.markdown("---")

search_query = st.text_input("🔍 कोई भी उत्पाद सर्च करें (जैसे: Shirt, Watch...)", "")

@st.cache_data(max_entries=100) 
def get_image_src(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        return f"data:image/jpeg;base64,{b64}"
    else:
        img_link = f"{GITHUB_RAW_URL}{urllib.parse.quote(path.replace('\\', '/'), safe='/')}"
        return img_link

def show_swipe_gallery(path_str):
    if not path_str:
        st.info("📷 फोटो उपलब्ध नहीं है")
        return []
    paths = [p.strip() for p in path_str.split('|') if p.strip()]
    if not paths: return []

    html_code = '<div class="swipe-gallery">'
    for p in paths:
        src = get_image_src(p)
        full_url = f"{GITHUB_RAW_URL}{urllib.parse.quote(p.replace('\\', '/'), safe='/')}"
        html_code += f'<a href="{full_url}" target="_blank"><img src="{src}" class="swipe-img" loading="lazy" alt="Product Image"></a>'
    html_code += '</div>'
    
    if len(paths) > 1:
        html_code += f'<div style="text-align:center; font-size:12px; color:gray; margin-top:-5px; margin-bottom:10px;">फोटो बड़ी करने के लिए उस पर क्लिक करें 🔍</div>'
    else:
        html_code += f'<div style="text-align:center; font-size:12px; color:gray; margin-top:-5px; margin-bottom:10px;">ज़ूम करने के लिए फोटो पर क्लिक करें 🔍</div>'
        
    st.markdown(html_code, unsafe_allow_html=True)
    return paths

def show_product_card(row, idx, prefix):
    prefix_idx = f"{prefix}_{idx}"
    with st.container(border=True):
        image_path_str = str(row.get("Image_Path", ""))
        all_paths = show_swipe_gallery(image_path_str)
        
        img_link_for_wa = ""
        if all_paths:
            img_link_for_wa = f"{GITHUB_RAW_URL}{urllib.parse.quote(all_paths[0].replace('\\', '/'), safe='/')}"
            
        st.write(f"**{row.get('Name', 'Unknown')}**")
        
        try: w_qty = int(float(row.get('Wholesale_Qty', 1)))
        except: w_qty = 1
        try: retail_price = row.get('Price', 0)
        except: retail_price = 0
        try: w_price = int(float(row.get('Wholesale_Price', retail_price)))
        except: w_price = retail_price
        
        if w_qty > 1:
            st.markdown(f"🛵 **सिंगल पीस (फ्री डिलीवरी):** ₹{retail_price} <br> 📦 **होलसेल (बॉक्स रेट):** ₹{w_price} *(कम से कम {w_qty} पीस)*", unsafe_allow_html=True)
        else:
            st.markdown(f"🛵 **सिंगल पीस रेट:** ₹{retail_price} *(फ्री डिलीवरी)*")
            
        qty = st.number_input("मात्रा (पीस)", min_value=1, value=1, key=f"q_{prefix_idx}")
        
        if st.button("कार्ट में डालें", key=f"b_{prefix_idx}"):
            final_price = w_price if qty >= w_qty else retail_price
            st.session_state.cart[prefix_idx] = {
                "name": row.get('Name', 'Item'), 
                "price": final_price, 
                "qty": qty,
                "img_link": img_link_for_wa
            }
            st.success("कार्ट में जुड़ गया! 🛒")
            
        if st.session_state.admin_logged_in:
            st.markdown("---")
            with st.expander("⚙️ एडिट / डिलीट"):
                with st.form(f"edit_form_{prefix_idx}"):
                    e_name = st.text_input("नया नाम", value=str(row.get("Name", "")))
                    col_x, col_y = st.columns(2)
                    with col_x:
                        e_price = st.number_input("सिंगल पीस (कोरियर सहित)", value=retail_price)
                        e_w_qty = st.number_input("होलसेल मात्रा", value=w_qty)
                    with col_y:
                        e_w_price = st.number_input("होलसेल (बॉक्स रेट)", value=w_price)
                        
                    existing_cats_edit = products_df['Category'].dropna().unique().tolist()
                    current_cat = str(row.get("Category", ""))
                    if current_cat not in existing_cats_edit:
                        existing_cats_edit.insert(0, current_cat)
                    e_cat = st.selectbox("केटेगरी", existing_cats_edit, index=existing_cats_edit.index(current_cat))
                    
                    e_uploaded_imgs = st.file_uploader("नई फोटो (Optional, max 3)", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=f"edit_imgs_{prefix_idx}")
                    update_btn = st.form_submit_button("✅ अपडेट करें")
                    
                if update_btn:
                    if e_uploaded_imgs and len(e_uploaded_imgs) > 3:
                        st.error("⚠️ अधिकतम 3 फोटो ही चुनें।")
                    else:
                        with st.spinner("अपडेट हो रहा है..."):
                            df_edit = load_products()
                            p_id = str(row['ID'])
                            final_path_str = row.get("Image_Path", "")
                            images_updated = True
                            
                            if e_uploaded_imgs:
                                new_image_paths = []
                                timestamp = int(time.time())
                                for idx_img, img in enumerate(e_uploaded_imgs):
                                    safe_filename = img.name.replace(" ", "_").replace("(", "").replace(")", "")
                                    final_filename = f"{p_id}_{idx_img}_{timestamp}_{safe_filename}"
                                    path = f"images/{final_filename}"
                                    try:
                                        with open(path, "wb") as f: f.write(img.getvalue())
                                    except: pass
                                    if save_to_github(path, img.getvalue(), f"Update image"):
                                        new_image_paths.append(path)
                                    else:
                                        images_updated = False
                                        break
                                if images_updated: final_path_str = "|".join(new_image_paths)

                            if images_updated:
                                df_edit.loc[df_edit['ID'].astype(str) == p_id, ['Name', 'Price', 'Wholesale_Price', 'Wholesale_Qty', 'Category', 'Image_Path']] = [e_name, e_price, e_w_price, e_w_qty, e_cat, final_path_str]
                                df_edit.to_csv(DATA_FILE, index=False)
                                with open(DATA_FILE, "r", encoding="utf-8") as f:
                                    csv_content = f.read()
                                if save_to_github(DATA_FILE, csv_content, f"Update product"):
                                    load_products.clear()
                                    get_image_src.clear() 
                                    st.success("✅ अपडेट हो गया!")
                                    time.sleep(1)
                                    st.rerun()

                if st.button("❌ पक्का डिलीट करें", key=f"del_{prefix_idx}"):
                    with st.spinner("डिलीट हो रहा है..."):
                        df_del = load_products()
                        p_id = str(row['ID'])
                        current_cat_before_delete = st.session_state.selected_category
                        
                        df_updated = df_del[df_del['ID'].astype(str) != p_id]
                        df_updated.to_csv(DATA_FILE, index=False)
                        with open(DATA_FILE, "r", encoding="utf-8") as f:
                            csv_content = f.read()
                        if save_to_github(DATA_FILE, csv_content, f"Delete product"):
                            load_products.clear()
                            get_image_src.clear()
                            
                            st.session_state.selected_category = current_cat_before_delete
                            if current_cat_before_delete:
                                st.query_params["cat"] = current_cat_before_delete
                            st.success("डिलीट हो गया!")
                            time.sleep(1)
                            st.rerun()

if products_df.empty:
    st.info("जल्द ही नए उत्पाद आएंगे!")
else:
    if search_query:
        st.subheader(f"'{search_query}' के सर्च रिजल्ट:")
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        if filtered_df.empty: st.warning("इस नाम से कोई उत्पाद नहीं मिला।")
        else:
            cols = st.columns(3)
            for idx, row in filtered_df.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "search")
    
    elif st.session_state.selected_category is None:
        st.subheader("🛍️ कैटेगरीज")
        valid_categories = products_df['Category'].dropna().unique().tolist()
        
        if len(valid_categories) == 0:
            st.write("अभी कोई कैटेगरी नहीं है।")
        else:
            colors = [
                ("#e1f5fe", "#0288d1"), ("#fce4ec", "#c2185b"), 
                ("#e8f5e9", "#388e3c"), ("#fff3e0", "#f57c00"), 
                ("#f3e5f5", "#7b1fa2"), ("#e0f7fa", "#0097a7"), 
                ("#fff8e1", "#ffa000"), ("#ffebee", "#d32f2f")
            ]
            
            html_grid = '<div class="category-grid">'
            for i, cat in enumerate(valid_categories):
                safe_cat = urllib.parse.quote(cat)
                bg_color, text_color = colors[i % len(colors)]
                
                html_grid += f'<a href="?cat={safe_cat}" target="_self" class="category-box" style="background-color: {bg_color}; color: {text_color};">{cat}</a>'
            
            html_grid += '</div>'
            st.markdown(html_grid, unsafe_allow_html=True)
            
    else:
        col_back, col_title = st.columns([2, 8])
        with col_back:
            if st.button("🔙 बाहर आएं", use_container_width=True):
                st.query_params.clear()
                st.session_state.selected_category = None
                st.rerun()
        with col_title:
            st.subheader(f"📂 {st.session_state.selected_category}")
        
        floating_btn_html = '''
        <a href="?" target="_self" class="floating-back-btn">
            🔙 सभी कैटेगरीज 
        </a>
        '''
        st.markdown(floating_btn_html, unsafe_allow_html=True)
        
        if st.session_state.admin_logged_in:
            with st.expander(f"✏️ इस कैटेगरी का नाम/आइकॉन बदलें"):
                new_cat_name = st.text_input("नया नाम या इमोजी डालें:", value=st.session_state.selected_category)
                if st.button("✅ सेव करें", key="rename_cat_btn"):
                    if new_cat_name and new_cat_name != st.session_state.selected_category:
                        with st.spinner("नाम बदला जा रहा है..."):
                            df_update = load_products()
                            old_cat = st.session_state.selected_category
                            df_update.loc[df_update['Category'] == old_cat, 'Category'] = new_cat_name
                            df_update.to_csv(DATA_FILE, index=False)
                            
                            with open(DATA_FILE, "r", encoding="utf-8") as f:
                                csv_content = f.read()
                            if save_to_github(DATA_FILE, csv_content, f"Rename category to {new_cat_name}"):
                                load_products.clear()
                                st.session_state.selected_category = new_cat_name
                                st.query_params["cat"] = new_cat_name
                                st.success("✅ नाम बदल गया!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("डेटाबेस अपडेट करने में समस्या आई।")

        cat_products = products_df[products_df['Category'] == st.session_state.selected_category]
        if cat_products.empty: 
            st.write("इस कैटेगरी में अभी कोई उत्पाद नहीं है।")
        else:
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]: 
                    show_product_card(row, idx, "cat_view")

st.markdown("<br><br><br>", unsafe_allow_html=True) 
st.markdown("---")
st.header("🛒 आपकी बास्केट (कच्चा बिल)")

if st.session_state.cart:
    total = 0
    msg = "🧾 *Oura - Kaccha Bill* 🧾\n\n"
    count = 1
    for k, item in st.session_state.cart.items():
        subtotal = item['price'] * item['qty']
        total += subtotal
        st.write(f"✔️ **{item['name']}** ({item['qty']} x ₹{item['price']}) = **₹{subtotal}**")
        msg += f"{count}. {item['name']} ({item['qty']} x ₹{item['price']}) = ₹{subtotal}\n"
        count += 1
    
    msg += f"\n💰 *कुल बिल:* ₹{total}\n⚠️ *होलसेल (बॉक्स) ऑर्डर पर ट्रांसपोर्ट/पैकिंग अलग से लगेगा। सिंगल पीस पर डिलीवरी फ्री है।*\n"
    st.subheader(f"कुल बिल: ₹{total}")
    
    available_upis = {}
    if current_config.get("phonepe_upi"): available_upis["PhonePe"] = {"id": current_config["phonepe_upi"], "color": "#5e35b1", "icon": "🟣"}
    if current_config.get("paytm_upi"): available_upis["Paytm"] = {"id": current_config["paytm_upi"], "color": "#00baf2", "icon": "🔵"}
    if current_config.get("gpay_upi"): available_upis["Google Pay"] = {"id": current_config["gpay_upi"], "color": "#1a73e8", "icon": "🔴"}
    if current_config.get("bhim_upi"): available_upis["BHIM"] = {"id": current_config["bhim_upi"], "color": "#ff7043", "icon": "🟠"}
    
    if not available_upis and current_config.get("upi_id"):
        available_upis["UPI App"] = {"id": current_config["upi_id"], "color": "#673AB7", "icon": "📲"}

    if available_upis:
        st.markdown("### 💳 सुरक्षित ऑनलाइन पेमेंट")
        st.write("अपने पसंदीदा ऐप से 1-क्लिक में पेमेंट करें:")
        
        for name, data in available_upis.items():
            upi_str = f"upi://pay?pa={data['id']}&pn=Oura_Wholesale&am={total}&cu=INR"
            st.markdown(f'''
            <a href="{upi_str}" class="multi-upi-btn" style="display:block; text-align:center; background:{data['color']}; color:white !important; padding:12px; border-radius:10px; text-decoration:none; font-size:16px; font-weight:bold; margin-bottom:10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                {data['icon']} {name} से ₹{total} पे करें
            </a>
            ''', unsafe_allow_html=True)
            msg += f"\n💳 *{name} UPI:* {data['id']}"
        
        with st.expander("स्कैन करके पेमेंट करें (QR Code)"):
            qr_tabs = st.tabs(list(available_upis.keys()))
            for idx, (name, data) in enumerate(available_upis.items()):
                with qr_tabs[idx]:
                    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(f'upi://pay?pa={data['id']}&pn=Oura_Wholesale&am={total}&cu=INR')}"
                    st.image(qr_url, width=150)
                    st.success(f"**{name} UPI ID:** `{data['id']}`")

    st.markdown("---")
    st.markdown("### 🤝 100% ग्राहक संतुष्टि (Customer Trust)")
    st.success("✅ **लाइव पैकिंग प्रूफ:** आपकी पूरी संतुष्टि और भरोसे के लिए, आपके माल की **पैकिंग की लाइव वीडियो और फोटो** डिस्पैच (Dispatch) से पहले सीधे आपके WhatsApp पर भेजी जाएगी। आप बिल्कुल बेफिक्र होकर ऑर्डर करें!")
    
    msg += "\n\n🤝 *भरोसा:* आपके माल की पैकिंग की लाइव वीडियो और फोटो डिस्पैच से पहले आपको WhatsApp पर भेजी जाएगी。\n"

    st.markdown("---")
    st.markdown("### 📜 रिफंड और रिटर्न पॉलिसी")
    st.warning("""
    ⚠️ **ध्यान दें:**
    1. रिफंड या वापसी सिर्फ **'खराब उत्पाद' (Manufacturing Defect)** की स्थिति में ही होगी।
    2. ट्रांसपोर्ट या कूरियर में **'माल टूटने' (Transit Damage)** की कोई जिम्मेदारी या रिफंड नहीं होगा।
    3. **इम्पोर्टेड (Imported) आइटम की कोई गारंटी नहीं होगी।**
    """)
    
    msg += "\n📜 *पॉलिसी:*\n- रिफंड सिर्फ 'खराब उत्पाद' पर मिलेगा।\n- ट्रांसपोर्ट में 'माल टूटने' पर कोई रिफंड नहीं।\n- इम्पोर्टेड आइटम की कोई गारंटी नहीं।"

    st.markdown("---")
    st.markdown("### 📍 डिलीवरी की जानकारी")
    st.info("ऑर्डर भेजने से पहले आप चाहें तो अपना पता यहाँ भर सकते हैं, या सीधे WhatsApp पर भी बता सकते हैं।")
    
    cust_name = st.text_input("आपका नाम (Optional / ऐच्छिक)")
    cust_mobile = st.text_input("मोबाईल नंबर (Optional / ऐच्छिक)")
    cust_address = st.text_area("पूरा पता (Optional / ऐच्छिक)")
    
    st.write("") 
    
    final_msg = msg
    final_msg += "\n\n📍 *डिलीवरी की जानकारी:*\n"
    final_msg += f"👤 नाम: {cust_name if cust_name else 'WhatsApp पर बताएंगे'}\n"
    final_msg += f"📞 मोबाईल: {cust_mobile if cust_mobile else 'WhatsApp पर बताएंगे'}\n"
    final_msg += f"🏠 पता: {cust_address if cust_address else 'WhatsApp पर बताएंगे'}\n"

    encoded_msg = urllib.parse.quote(final_msg)
    wa_link = f"https://wa.me/{current_config['admin_whatsapp']}?text={encoded_msg}"
    
    st.markdown(f'''
    <a href="{wa_link}" target="_blank" style="display:block; text-align:center; background-color:#25D366; color:white; padding:15px; border-radius:10px; text-decoration:none; font-size:18px; font-weight:bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom:10px;">
        ✅ सीधा WhatsApp पर ऑर्डर भेजें
    </a>
    ''', unsafe_allow_html=True)
    
    st.write("")
    if st.button("🗑️ बास्केट खाली करें"):
        st.session_state.cart = {}
        st.rerun()

# ---------------------------------------------------------
# 📞 खिसकने (Draggable) और चमकने वाला WhatsApp नंबर
# ---------------------------------------------------------
admin_wa_number = current_config.get("admin_whatsapp", "919891587437")
wa_chat_link = f"https://wa.me/{admin_wa_number}"

floating_wa_html = f"""
<a id="oura-wa-btn" href="{wa_chat_link}" target="_blank" title="WhatsApp Us">
    📞 {admin_wa_number}
</a>
"""
st.markdown(floating_wa_html, unsafe_allow_html=True)

drag_js_code = """
<script>
const parentDoc = window.parent.document;
const btn = parentDoc.getElementById('oura-wa-btn');

if (btn && !btn.dataset.draggable) {
    btn.dataset.draggable = "true";
    let isDragging = false;
    let startY, startTop;

    const onStart = (e) => {
        if(e.type === 'mousedown' || e.type === 'touchstart') {
            isDragging = true;
            startY = e.touches ? e.touches[0].clientY : e.clientY;
            startTop = btn.offsetTop;
            btn.style.animation = 'none'; 
            btn.style.transition = 'none';
        }
    };

    const onMove = (e) => {
        if (!isDragging) return;
        e.preventDefault(); 
        let currentY = e.touches ? e.touches[0].clientY : e.clientY;
        let dy = currentY - startY;
        let newTop = startTop + dy;
        
        if (newTop < 80) newTop = 80;
        if (newTop > parentDoc.documentElement.clientHeight - 80) newTop = parentDoc.documentElement.clientHeight - 80;
        
        btn.style.top = newTop + 'px';
        btn.style.bottom = 'auto'; 
    };

    const onEnd = () => {
        isDragging = false;
        btn.style.animation = 'glowing 2s infinite'; 
    };

    btn.addEventListener('touchstart', onStart, {passive: false});
    parentDoc.addEventListener('touchmove', onMove, {passive: false});
    parentDoc.addEventListener('touchend', onEnd);

    btn.addEventListener('mousedown', onStart);
    parentDoc.addEventListener('mousemove', onMove);
    parentDoc.addEventListener('mouseup', onEnd);
    
    btn.addEventListener('click', (e) => {
        if (Math.abs(btn.offsetTop - startTop) > 10) {
            e.preventDefault(); 
        }
    });
}
</script>
"""
components.html
