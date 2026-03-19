import streamlit as st
import pandas as pd
import os
import urllib.parse
import json
import requests
import base64
import time

# 1. ऐप का सेटअप (फास्ट लोडिंग के लिए)
st.set_page_config(page_title="Oura - Wholesale", page_icon="🛍️", layout="wide")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            div[data-testid="stDecoration"] {visibility: hidden; height: 0%; display: none;}
            
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
            .swipe-img {
                scroll-snap-align: center;
                flex: 0 0 100%;
                max-width: 100%;
                height: 300px;
                object-fit: contain;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #eee;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

BANNER_FILE = "banner.png" 
CONFIG_FILE = "config.json"
DATA_FILE = "oura_products.csv"
GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

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

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"admin_whatsapp": "919891587437", "upi_id": "9891587437@upi", "has_banner": False}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    save_to_github(CONFIG_FILE, json.dumps(config, indent=4), "Update settings.json")

current_config = load_config()

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

@st.cache_data(ttl=5) # 🚀 कैशिंग का इस्तेमाल ताकि डेटाबेस बार-बार लोड न हो
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

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False
if 'cart' not in st.session_state:
    st.session_state.cart = {}

if current_config.get("has_banner", False):
    if os.path.exists(BANNER_FILE):
        st.image(BANNER_FILE, use_container_width=True)
    else:
        # बैनर के लिए कैश-बस्टिंग ज़रूरी है क्योंकि उसका नाम नहीं बदलता
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
                st.error("⚠️ सेटिंग्स में ADMIN_PASSWORD नहीं मिला! कृपया Secrets अपडेट करें।")
                correct_password = None
                
            if correct_password and password == correct_password:
                st.session_state.admin_logged_in = True
                st.session_state.show_login = False
                st.rerun()
            else:
                st.error("❌ गलत पासवर्ड!")
    st.markdown("---")

if st.session_state.admin_logged_in:
    st.success("✅ आप एडमिन हैं। किसी उत्पाद को बदलने/हटाने के लिए सीधे नीचे उस उत्पाद पर जाएं।")
    
    tab_add, tab_banner, tab_settings = st.tabs(["➕ नया उत्पाद जोड़ें", "🖼️ बैनर सेटिंग्स", "⚙️ ऐप सेटिंग्स"])
    
    with tab_add:
        with st.form("add_product", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                new_id = st.text_input("ID (यूनिक रखें)")
                new_name = st.text_input("नाम")
                new_price = st.number_input("रिटेल रेट (1 पीस का)", min_value=1)
            with col_b:
                new_w_qty = st.number_input("होलसेल कम से कम पीस", min_value=1, value=10)
                new_w_price = st.number_input("होलसेल रेट (प्रति पीस)", min_value=1)
            
            existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
            cat_options = ["नयी केटेगरी बनाएं..."] + existing_cats
            selected_cat = st.selectbox("केटेगरी चुनें", cat_options)
            
            if selected_cat == "नयी केटेगरी बनाएं...":
                final_cat = st.text_input("नई केटेगरी का नाम लिखें")
            else:
                final_cat = selected_cat
                
            uploaded_imgs = st.file_uploader("फोटो अपलोड करें (अधिकतम 3 फोटो)", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="add_imgs")
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
                                load_products.clear() # कैश साफ करें
                                st.success("✅ सेव हो गया!")
                                time.sleep(1)
                                st.rerun()

    with tab_banner:
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

    with tab_settings:
        new_wa = st.text_input("WhatsApp नंबर", value=current_config.get("admin_whatsapp", ""))
        new_upi = st.text_input("UPI ID (पेमेंट के लिए)", value=current_config.get("upi_id", ""))
        if st.button("सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["upi_id"] = new_upi
            save_config(current_config)
            st.success("सेव हो गईं!")
            time.sleep(1)
            st.rerun()
    st.markdown("---")

search_query = st.text_input("🔍 कोई भी उत्पाद सर्च करें (जैसे: Shirt, Watch...)", "")

# 🚀 फास्ट इमेज लोडिंग (Cache Busting हटा दिया गया है)
def get_image_src(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        return f"data:image/jpeg;base64,{b64}"
    else:
        # अब बिना ?t=time के लिंक जाएगा, ताकि ब्राउज़र इसे कैश कर सके!
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
        html_code += f'<img src="{src}" class="swipe-img" loading="lazy" alt="Product Image">'
    html_code += '</div>'
    
    if len(paths) > 1:
        html_code += f'<div style="text-align:center; font-size:12px; color:gray; margin-top:-5px; margin-bottom:10px;">स्वाइप करें 👉</div>'
        
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
            st.markdown(f"**रिटेल:** ₹{retail_price} <br> **होलसेल:** ₹{w_price} *(कम से कम {w_qty} पीस)*", unsafe_allow_html=True)
        else:
            st.markdown(f"**रेट:** ₹{retail_price}")
            
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
                        e_price = st.number_input("रिटेल", value=retail_price)
                        e_w_qty = st.number_input("होलसेल मात्रा", value=w_qty)
                    with col_y:
                        e_w_price = st.number_input("होलसेल", value=w_price)
                        
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
                                    load_products.clear() # कैश साफ़ करें
                                    st.success("✅ अपडेट हो गया!")
                                    time.sleep(1)
                                    st.rerun()

                if st.button("❌ पक्का डिलीट करें", key=f"del_{prefix_idx}"):
                    with st.spinner("डिलीट हो रहा है..."):
                        df_del = load_products()
                        p_id = str(row['ID'])
                        df_updated = df_del[df_del['ID'].astype(str) != p_id]
                        df_updated.to_csv(DATA_FILE, index=False)
                        with open(DATA_FILE, "r", encoding="utf-8") as f:
                            csv_content = f.read()
                        if save_to_github(DATA_FILE, csv_content, f"Delete product"):
                            load_products.clear()
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
    else:
        valid_categories = products_df['Category'].dropna().unique().tolist()
        if len(valid_categories) == 0: valid_categories = ["General"]
        tabs = st.tabs(valid_categories)
        for i, cat in enumerate(valid_categories):
            with tabs[i]:
                cat_products = products_df[products_df['Category'] == cat]
                if cat_products.empty: st.write("अभी कोई उत्पाद नहीं है।")
                else:
                    cols = st.columns(3)
                    for idx, row in cat_products.reset_index().iterrows():
                        with cols[idx % 3]: show_product_card(row, idx, f"tab_{i}")

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
    
    msg += f"\n💰 *कुल बिल:* ₹{total}\n⚠️ *पैकिंग व ट्रांसपोर्ट Extra*"
    st.subheader(f"कुल बिल: ₹{total}")
    upi = current_config.get("upi_id", "")
    if upi:
        st.success(f"💳 **पेमेंट के लिए UPI ID:** `{upi}`")
        msg += f"\n\n💳 *UPI ID:* {upi}"
    
    if st.button("WhatsApp पर ऑर्डर भेजें"):
        encoded_msg = urllib.parse.quote(msg)
        wa_link = f"https://wa.me/{current_config['admin_whatsapp']}?text={encoded_msg}"
        st.write(f"👉 [यहाँ क्लिक करके WhatsApp भेजें]({wa_link})")
    
    if st.button("बास्केट खाली करें"):
        st.session_state.cart = {}
        st.rerun()
