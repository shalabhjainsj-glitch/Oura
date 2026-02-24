import streamlit as st
import pandas as pd
import os
import urllib.parse
import json

# 1. ऐप का सेटअप (इसे केवल एक बार रखें)
st.set_page_config(page_title="Oura - Wholesale", page_icon="🛍️", layout="wide")

CONFIG_FILE = "config.json"
BANNER_FILE = "banner.png"
DATA_FILE = "oura_products.csv"

# डिफ़ॉल्ट सेटिंग्स लोड करना
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "admin_whatsapp": "919891587437", 
        "upi_id": "", 
        "payment_options": "UPI, Bank Transfer",
        "categories": ["General 📦", "Premium 🌟", "Offers 🎁"] 
    }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

current_config = load_config()

# डेटाबेस सेटअप
if not os.path.exists("images"):
    os.makedirs("images")

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["ID", "Name", "Price", "Category", "Image_Path"])
    df.to_csv(DATA_FILE, index=False)
else:
    df = pd.read_csv(DATA_FILE)

def load_products():
    return pd.read_csv(DATA_FILE)

# 2. एडमिन पैनल (Sidebar में)
st.sidebar.title("🔒 एडमिन पैनल")

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    password = st.sidebar.text_input("बदलाव करने के लिए पासवर्ड डालें", type="password")
    if st.sidebar.button("लॉगिन"):
        if password == "shalabh021208":
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
        cats_str = st.text_area("केटेगरी (कॉमा लगाकर)", value=", ".join(current_config.get("categories", [])))
        if st.button("सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["categories"] = [c.strip() for c in cats_str.split(",") if c.strip()]
            save_config(current_config)
            st.success("सेटिंग्स सेव!")
            st.rerun()

    st.sidebar.subheader("➕ नया उत्पाद")
    with st.sidebar.form("add_product", clear_on_submit=True):
        new_id = st.text_input("ID (यूनिक रखें)")
        new_name = st.text_input("नाम")
        new_price = st.number_input("रेट", min_value=1)
        new_cat = st.selectbox("केटेगरी", current_config.get("categories", ["General"]))
        img = st.file_uploader("फोटो", type=["jpg", "png", "jpeg"])
        if st.form_submit_button("सेव करें") and new_id and new_name and img:
            path = os.path.join("images", img.name)
            with open(path, "wb") as f:
                f.write(img.getbuffer())
            df = load_products()
            new_row = pd.DataFrame([[new_id, new_name, new_price, new_cat, path]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

# 3. कस्टमर व्यू
if os.path.exists(BANNER_FILE):
    st.image(BANNER_FILE, use_container_width=True)

st.title("🛍️ Oura")
if 'cart' not in st.session_state:
    st.session_state.cart = {}

products_df = load_products()

if products_df.empty:
    st.info("जल्द ही नए उत्पाद आएंगे!")
else:
    categories = current_config.get("categories", ["General"])
    tabs = st.tabs(categories)
    for i, cat in enumerate(categories):
        with tabs[i]:
            cat_products = products_df[products_df['Category'] == cat]
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]:
                    with st.container(border=True):
                        if os.path.exists(row["Image_Path"]):
                            st.image(row["Image_Path"], use_container_width=True)
                        st.write(f"**{row['Name']}**")
                        st.write(f"₹{row['Price']}")
                        # Duplicate Key एरर को रोकने के लिए key में idx जोड़ा गया है
                        qty = st.number_input("मात्रा", min_value=1, value=1, key=f"q_{cat}_{idx}")
                        if st.button("कार्ट में डालें", key=f"b_{cat}_{idx}"):
                            st.session_state.cart[f"{cat}_{idx}"] = {"name": row['Name'], "price": row['Price'], "qty": qty}
                            st.success("जोड़ा गया!")

st.markdown("---")
st.header("🛒 आपकी बास्केट")
if st.session_state.cart:
    total = 0
    msg = "नमस्ते Oura, मेरा ऑर्डर:\n\n"
    for k, item in st.session_state.cart.items():
        subtotal = item['price'] * item['qty']
        total += subtotal
        st.write(f"✔️ {item['name']} x {item['qty']} = ₹{subtotal}")
        msg += f"▪️ {item['name']} x {item['qty']} = ₹{subtotal}\n"
    
    st.subheader(f"कुल बिल: ₹{total}")
    if st.button("WhatsApp पर ऑर्डर भेजें"):
        encoded_msg = urllib.parse.quote(msg + f"\nकुल: ₹{total}")
        st.write(f"👉 [यहाँ क्लिक करके WhatsApp भेजें](https://wa.me/{current_config['admin_whatsapp']}?text={encoded_msg})")
    
    if st.button("बास्केट खाली करें"):
        st.session_state.cart = {}
        st.rerun()

    


