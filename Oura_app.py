import streamlit as st
import pandas as pd
import os
import urllib.parse
import json
import requests
import base64
import time

# 1. ऐप का सेटअप
st.set_page_config(page_title="Oura - Wholesale", page_icon="🛍️", layout="wide")

# 🛡️ सुरक्षा चक्र: Streamlit का मेन्यू, हेडर और 'लाल लाइन' छुपाने का कोड
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            div[data-testid="stDecoration"] {visibility: hidden; height: 0%; display: none;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

BANNER_FILE = "banner.png" 
CONFIG_FILE = "config.json"
DATA_FILE = "oura_products.csv"
GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# 🌟 जादुई फंक्शन: जो डेटा को हमेशा के लिए GitHub में सेव करेगा
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
        except:
            pass
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

# --- सेशन स्टेट इनिशियलाइज़ेशन ---
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False
if 'cart' not in st.session_state:
    st.session_state.cart = {}

# --- 🖼️ बैनर (सबके लिए) ---
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

# --- 🔒 सुरक्षित लॉगिन सिस्टम (मुख्य पेज पर) ---
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

# --- 🛠️ एडमिन पैनल (सिर्फ लॉगिन होने पर दिखेगा) ---
if st.session_state.admin_logged_in:
    st.success("✅ आप एडमिन के रूप में लॉग इन हैं।")
    
    # 🌟 नया डिज़ाइन: अब आपके पास 5 टैब होंगे
    tab_add, tab_edit, tab_del, tab_banner, tab_settings = st.tabs(["➕ नया", "✏️ एडिट", "🗑️ डिलीट", "🖼️ बैनर", "⚙️ सेटिंग्स"])
    
    # --- 1. नया उत्पाद ---
    with tab_add:
        st.subheader("नया उत्पाद जोड़ें")
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
                
            img = st.file_uploader("फोटो अपलोड करें", type=["jpg", "png", "jpeg"])
            
            if st.form_submit_button("उत्पाद सेव करें") and new_id and new_name and img and final_cat:
                with st.spinner("डेटा सेव हो रहा है..."):
                    safe_filename = img.name.replace(" ", "_").replace("(", "").replace(")", "")
                    path = f"images/{safe_filename}"
                    img_bytes = img.getvalue()
                    
                    try:
                        with open(path, "wb") as f:
                            f.write(img_bytes)
                    except:
                        pass

                    if save_to_github(path, img_bytes, f"Add image {safe_filename}"):
                        df = load_products()
                        new_row = pd.DataFrame([[new_id, new_name, new_price, new_w_price, new_w_qty, final_cat, path]], columns=expected_columns)
                        df = pd.concat([df, new_row], ignore_index=True)
                        df.to_csv(DATA_FILE, index=False)
                        
                        with open(DATA_FILE, "r", encoding="utf-8") as f:
                            csv_content = f.read()
                        if save_to_github(DATA_FILE, csv_content, f"Add product {new_name}"):
                            st.success(f"✅ उत्पाद '{new_name}' सेव हो गया!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("डेटाबेस सेव करने में समस्या आई।")
                    else:
                        st.error("इमेज को GitHub पर सेव करने में समस्या आई।")

    # --- 2. 🌟 नया फीचर: उत्पाद एडिट करें (Update) ---
    with tab_edit:
        st.subheader("✏️ उत्पाद में बदलाव करें (Edit)")
        df_edit = load_products()
        if not df_edit.empty and "ID" in df_edit.columns and "Name" in df_edit.columns:
            product_list = df_edit['ID'].astype(str) + " - " + df_edit['Name'].astype(str)
            item_to_edit = st.selectbox("बदलने के लिए उत्पाद चुनें:", product_list, key="edit_select")
            
            if item_to_edit:
                edit_id = item_to_edit.split(" - ")[0]
                current_row = df_edit[df_edit['ID'].astype(str) == edit_id].iloc[0]
                
                # पुरानी वैल्यूज़ को सुरक्षित तरीके से निकालना
                try: p_price = int(float(current_row.get("Price", 1)))
                except: p_price = 1
                try: p_w_price = int(float(current_row.get("Wholesale_Price", 1)))
                except: p_w_price = 1
                try: p_w_qty = int(float(current_row.get("Wholesale_Qty", 10)))
                except: p_w_qty = 10
                
                with st.form("edit_product_form"):
                    st.write("नई जानकारी भरें (जो नहीं बदलना, उसे वैसे ही रहने दें)")
                    col_c, col_d = st.columns(2)
                    with col_c:
                        e_name = st.text_input("नाम", value=str(current_row.get("Name", "")))
                        e_price = st.number_input("रिटेल रेट", min_value=1, value=p_price)
                    with col_d:
                        e_w_qty = st.number_input("होलसेल कम से कम पीस", min_value=1, value=p_w_qty)
                        e_w_price = st.number_input("होलसेल रेट", min_value=1, value=p_w_price)
                    
                    existing_cats_edit = df_edit['Category'].dropna().unique().tolist()
                    current_cat = str(current_row.get("Category", ""))
                    if current_cat not in existing_cats_edit:
                        existing_cats_edit.insert(0, current_cat)
                        
                    e_cat = st.selectbox("केटेगरी", existing_cats_edit, index=existing_cats_edit.index(current_cat) if current_cat in existing_cats_edit else 0)
                    
                    st.info("🖼️ अगर फोटो बदलनी है तभी नई फोटो अपलोड करें, वरना इसे खाली छोड़ दें।")
                    e_img = st.file_uploader("नई फोटो अपलोड करें (Optional)", type=["jpg", "png", "jpeg"], key="edit_img")
                    
                    if st.form_submit_button("✅ उत्पाद अपडेट करें"):
                        with st.spinner("अपडेट हो रहा है..."):
                            final_path = current_row.get("Image_Path", "")
                            image_updated = True
                            
                            # अगर नई फोटो डाली गई है
                            if e_img:
                                safe_filename = e_img.name.replace(" ", "_").replace("(", "").replace(")", "")
                                final_path = f"images/{safe_filename}"
                                img_bytes = e_img.getvalue()
                                try:
                                    with open(final_path, "wb") as f:
                                        f.write(img_bytes)
                                except:
                                    pass
                                image_updated = save_to_github(final_path, img_bytes, f"Update image for {e_name}")
                            
                            if image_updated:
                                # डेटाबेस में नई जानकारी डालना
                                df_edit.loc[df_edit['ID'].astype(str) == edit_id, ['Name', 'Price', 'Wholesale_Price', 'Wholesale_Qty', 'Category', 'Image_Path']] = [e_name, e_price, e_w_price, e_w_qty, e_cat, final_path]
                                df_edit.to_csv(DATA_FILE, index=False)
                                
                                with open(DATA_FILE, "r", encoding="utf-8") as f:
                                    csv_content = f.read()
                                if save_to_github(DATA_FILE, csv_content, f"Update product {edit_id}"):
                                    st.success("✅ उत्पाद सफलतापूर्वक अपडेट हो गया!")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("डेटाबेस अपडेट करने में समस्या आई।")
                            else:
                                st.error("नई फोटो सेव करने में समस्या आई।")
        else:
            st.write("अभी कोई उत्पाद नहीं है।")

    # --- 3. उत्पाद हटाएं ---
    with tab_del:
        st.subheader("🗑️ उत्पाद हटाएं (Delete)")
        df_del = load_products()
        if not df_del.empty and "ID" in df_del.columns and "Name" in df_del.columns:
            product_list = df_del['ID'].astype(str) + " - " + df_del['Name'].astype(str)
            item_to_delete = st.selectbox("हटाने के लिए उत्पाद चुनें:", product_list, key="del_select")
            
            if st.button("❌ पक्का डिलीट करें"):
                del_id = item_to_delete.split(" - ")[0]
                df_updated = df_del[df_del['ID'].astype(str) != del_id]
                df_updated.to_csv(DATA_FILE, index=False)
                
                with st.spinner("डेटाबेस को अपडेट किया जा रहा है..."):
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        csv_content = f.read()
                    if save_to_github(DATA_FILE, csv_content, f"Delete product {del_id}"):
                        st.success("उत्पाद हमेशा के लिए हटा दिया गया!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("डेटाबेस को अपडेट करने में समस्या आई।")
        else:
            st.write("अभी कोई उत्पाद नहीं है।")

    # --- 4. बैनर सेटिंग्स ---
    with tab_banner:
        st.subheader("🖼️ बैनर (Banner) सेटिंग्स")
        st.write("दुकान के सबसे ऊपर दिखने वाला फोटो लगाएं/बदलें")
        new_banner = st.file_uploader("नया बैनर चुनें (चौड़ी फोटो बेहतर रहेगी)", type=["jpg", "png", "jpeg"], key="banner_upload")
        
        if st.button("बैनर सेव करें") and new_banner:
            with st.spinner("बैनर सेव हो रहा है..."):
                banner_bytes = new_banner.getvalue()
                try:
                    with open(BANNER_FILE, "wb") as f:
                        f.write(banner_bytes)
                except:
                    pass
                
                if save_to_github(BANNER_FILE, banner_bytes, "Update banner image"):
                    current_config["has_banner"] = True
                    save_config(current_config)
                    st.success("✅ शानदार! बैनर लग गया है।")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("बैनर सेव करने में समस्या आई।")
                    
        if current_config.get("has_banner", False):
            if st.button("❌ बैनर हटाएं"):
                current_config["has_banner"] = False
                save_config(current_config)
                st.success("बैनर हटा दिया गया है!")
                time.sleep(2)
                st.rerun()

    # --- 5. ऐप सेटिंग्स ---
    with tab_settings:
        st.subheader("⚙️ ऐप सेटिंग्स")
        new_wa = st.text_input("WhatsApp नंबर", value=current_config.get("admin_whatsapp", ""))
        new_upi = st.text_input("UPI ID (पेमेंट के लिए)", value=current_config.get("upi_id", ""))
        
        if st.button("सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["upi_id"] = new_upi
            save_config(current_config)
            st.success("सेटिंग्स हमेशा के लिए सेव हो गईं!")
            time.sleep(2)
            st.rerun()
    
    st.markdown("---")

# --- 🛍️ कस्टमर व्यू (प्रोडक्ट लिस्ट) ---
search_query = st.text_input("🔍 कोई भी उत्पाद सर्च करें (जैसे: Shirt, Watch...)", "")

def show_product_card(row, idx, prefix):
    with st.container(border=True):
        image_path = str(row.get("Image_Path", "")).replace("\\", "/")
        img_link = f"{GITHUB_RAW_URL}{urllib.parse.quote(image_path, safe='/')}"
        
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
        else:
            try:
                cache_bust_link = f"{img_link}?t={int(time.time())}"
                st.image(cache_bust_link, use_container_width=True)
            except:
                st.info("⏳ फोटो लोड हो रही है...")
            
        st.write(f"**{row.get('Name', 'Unknown')}**")
        
        try:
            w_qty = int(float(row.get('Wholesale_Qty', 1)))
            retail_price = row.get('Price', 0)
            w_price = int(float(row.get('Wholesale_Price', retail_price)))
        except:
            w_qty = 1
            retail_price = row.get('Price', 0)
            w_price = retail_price
        
        if w_qty > 1:
            st.markdown(f"**रिटेल:** ₹{retail_price} <br> **होलसेल:** ₹{w_price} *(कम से कम {w_qty} पीस)*", unsafe_allow_html=True)
        else:
            st.markdown(f"**रेट:** ₹{retail_price}")
            
        qty = st.number_input("मात्रा (पीस)", min_value=1, value=1, key=f"q_{prefix}_{idx}")
        
        if st.button("कार्ट में डालें", key=f"b_{prefix}_{idx}"):
            final_price = w_price if qty >= w_qty else retail_price
            st.session_state.cart[f"{prefix}_{idx}"] = {
                "name": row.get('Name', 'Item'), 
                "price": final_price, 
                "qty": qty,
                "img_link": img_link
            }
            st.success("कार्ट में जुड़ गया! 🛒")

if products_df.empty:
    st.info("जल्द ही नए उत्पाद आएंगे!")
else:
    if search_query:
        st.subheader(f"'{search_query}' के सर्च रिजल्ट:")
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        
        if filtered_df.empty:
            st.warning("इस नाम से कोई उत्पाद नहीं मिला।")
        else:
            cols = st.columns(3)
            for idx, row in filtered_df.reset_index().iterrows():
                with cols[idx % 3]:
                    show_product_card(row, idx, "search")
    else:
        valid_categories = products_df['Category'].dropna().unique().tolist()
        if len(valid_categories) == 0:
            valid_categories = ["General"]
            
        tabs = st.tabs(valid_categories)
        
        for i, cat in enumerate(valid_categories):
            with tabs[i]:
                cat_products = products_df[products_df['Category'] == cat]
                
                if cat_products.empty:
                     st.write("इस केटेगरी में अभी कोई उत्पाद नहीं है।")
                else:
                    cols = st.columns(3)
                    for idx, row in cat_products.reset_index().iterrows():
                        with cols[idx % 3]:
                            show_product_card(row, idx, f"tab_{i}")

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
    
    msg += f"\n💰 *कुल बिल:* ₹{total}\n"
    msg += "⚠️ *पैकिंग व ट्रांसपोर्ट Extra*"
    
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

















