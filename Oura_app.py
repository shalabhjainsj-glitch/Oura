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

# 🛡️ सुरक्षा चक्र: Streamlit का मेन्यू और हेडर छुपाने का कोड
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
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
        st.error(f"⚠️ GitHub Token नहीं मिला या गलत है! कृपया ऐप की सेटिंग्स चेक करें।")
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
    
    if put_response.status_code in [200, 201]:
        return True
    else:
        return False

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"admin_whatsapp": "919891587437", "upi_id": "9891587437@upi"}

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

# 2. एडमिन पैनल
st.sidebar.title("🔒 एडमिन पैनल")

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    password = st.sidebar.text_input("पासवर्ड डालें", type="password")
    if st.sidebar.button("लॉगिन"):
        # 🛡️ सुरक्षा चक्र: अब पासवर्ड कोड में नहीं, बल्कि सुरक्षित तिजोरी (Secrets) से लिया जाएगा
        try:
            correct_password = st.secrets["ADMIN_PASSWORD"]
        except:
            st.sidebar.error("⚠️ सेटिंग्स में ADMIN_PASSWORD नहीं मिला! कृपया Secrets अपडेट करें।")
            correct_password = None
            
        if correct_password and password == correct_password:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.sidebar.error("❌ गलत पासवर्ड!")
else:
    if st.sidebar.button("🚪 लॉगआउट"):
        st.session_state.admin_logged_in = False
        st.rerun()
    
    with st.sidebar.expander("⚙️ ऐप सेटिंग्स"):
        new_wa = st.text_input("WhatsApp नंबर", value=current_config.get("admin_whatsapp", ""))
        new_upi = st.text_input("UPI ID (पेमेंट के लिए)", value=current_config.get("upi_id", ""))
        
        if st.button("सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["upi_id"] = new_upi
            save_config(current_config)
            st.success("सेटिंग्स हमेशा के लिए सेव हो गईं!")
            st.rerun()

    st.sidebar.subheader("➕ नया उत्पाद जोड़ें")
    with st.sidebar.form("add_product", clear_on_submit=True):
        new_id = st.text_input("ID (यूनिक रखें)")
        new_name = st.text_input("नाम")
        new_price = st.number_input("रिटेल रेट (1 पीस का)", min_value=1)
        new_w_qty = st.number_input("होलसेल के लिए कम से कम पीस", min_value=1, value=10)
        new_w_price = st.number_input("होलसेल रेट (प्रति पीस)", min_value=1)
        
        existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
        cat_options = ["नयी केटेगरी बनाएं..."] + existing_cats
        selected_cat = st.selectbox("केटेगरी चुनें", cat_options)
        
        if selected_cat == "नयी केटेगरी बनाएं...":
            final_cat = st.text_input("नई केटेगरी का नाम लिखें")
        else:
            final_cat = selected_cat
            
        img = st.file_uploader("फोटो अपलोड करें", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("सेव करें") and new_id and new_name and img and final_cat:
            with st.spinner("डेटा सेव हो रहा है, कृपया प्रतीक्षा करें..."):
                safe_filename = img.name.replace(" ", "_").replace("(", "").replace(")", "")
                path = f"images/{safe_filename}"
                
                img_bytes = img.getvalue()
                
                try:
                    with open(path, "wb") as f:
                        f.write(img_bytes)
                except:
                    pass

                image_saved = save_to_github(path, img_bytes, f"Add image {safe_filename}")
                
                if image_saved:
                    df = load_products()
                    new_row = pd.DataFrame([[new_id, new_name, new_price, new_w_price, new_w_qty, final_cat, path]], columns=expected_columns)
                    df = pd.concat([df, new_row], ignore_index=True)
                    df.to_csv(DATA_FILE, index=False)
                    
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        csv_content = f.read()
                    csv_saved = save_to_github(DATA_FILE, csv_content, f"Add product {new_name}")
                    
                    if csv_saved:
                        st.sidebar.success(f"✅ उत्पाद '{new_name}' हमेशा के लिए सेव हो गया!")
                        st.rerun()
                    else:
                        st.sidebar.error("डेटाबेस को सेव करने में समस्या आई।")
                else:
                    st.sidebar.error("इमेज को GitHub पर सेव करने में समस्या आई।")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ उत्पाद हटाएं (Delete)")
    df_del = load_products()
    if not df_del.empty and "ID" in df_del.columns and "Name" in df_del.columns:
        product_list = df_del['ID'].astype(str) + " - " + df_del['Name'].astype(str)
        item_to_delete = st.sidebar.selectbox("हटाने के लिए उत्पाद चुनें:", product_list)
        
        if st.sidebar.button("❌ पक्का डिलीट करें"):
            del_id = item_to_delete.split(" - ")[0]
            df_updated = df_del[df_del['ID'].astype(str) != del_id]
            df_updated.to_csv(DATA_FILE, index=False)
            
            with st.spinner("डेटाबेस को अपडेट किया जा रहा है..."):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    csv_content = f.read()
                csv_saved = save_to_github(DATA_FILE, csv_content, f"Delete product {del_id}")
                
                if csv_saved:
                    st.sidebar.success(f"उत्पाद हमेशा के लिए हटा दिया गया!")
                    st.rerun()
                else:
                    st.sidebar.error("डेटाबेस को अपडेट करने में समस्या आई।")
    else:
        st.sidebar.write("अभी कोई उत्पाद नहीं है।")

# 3. कस्टमर व्यू
st.title("🛍️ Oura")
search_query = st.text_input("🔍 कोई भी उत्पाद सर्च करें (जैसे: Shirt, Watch...)", "")

if 'cart' not in st.session_state:
    st.session_state.cart = {}

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



















