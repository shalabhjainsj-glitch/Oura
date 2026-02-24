import streamlit as st
import pandas as pd
import os
import urllib.parse
import json

# 1. ऐप का सेटअप
st.set_page_config(page_title="Oura - Wholesale", page_icon="🛍️", layout="wide")

CONFIG_FILE = "config.json"
BANNER_FILE = "banner.png"
DATA_FILE = "oura_products.csv"

# डिफ़ॉल्ट सेटिंग्स
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "admin_whatsapp": "919876543210", # अपना WhatsApp नंबर यहाँ सेट करें
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
    if "Category" not in df.columns:
        df["Category"] = current_config["categories"][0] if current_config["categories"] else "General"
        df.to_csv(DATA_FILE, index=False)

def load_products():
    return pd.read_csv(DATA_FILE)

# ---------------------------------------------------------
# 2. एडमिन पैनल (सिर्फ आपके लिए - Sidebar में)
# ---------------------------------------------------------
st.sidebar.title("🔒 एडमिन पैनल")

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# अगर एडमिन लॉगिन नहीं है, तो पासवर्ड मांगें
if not st.session_state.admin_logged_in:
    password = st.sidebar.text_input("बदलाव करने के लिए पासवर्ड डालें", type="password")
    if st.sidebar.button("लॉगिन"):
        if password == "oura123": # यहाँ अपना पासवर्ड बदल सकते हैं
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.sidebar.error("❌ गलत पासवर्ड!")
            
# अगर एडमिन लॉगिन है, तो कंट्रोल दिखाएं
else:
    if st.sidebar.button("🚪 एडमिन से बाहर आएं (Logout)"):
        st.session_state.admin_logged_in = False
        st.rerun()
        
    st.sidebar.markdown("---")
    
    # ऐप सेटिंग्स
    with st.sidebar.expander("⚙️ ऐप सेटिंग्स बदलें"):
        new_wa = st.text_input("ऑर्डर के लिए आपका WhatsApp नंबर", value=current_config.get("admin_whatsapp", ""))
        cats_str = st.text_area("केटेगरी बॉक्स (कॉमा लगाकर)", value=", ".join(current_config.get("categories", [])))
        new_banner = st.file_uploader("बैनर बदलें", type=["jpg", "png", "jpeg"])
        if new_banner is not None:
            with open(BANNER_FILE, "wb") as f:
                f.write(new_banner.getbuffer())
            st.success("बैनर अपडेट हो गया!")
            
        new_upi = st.text_input("आपका UPI नंबर / ID", value=current_config.get("upi_id", ""))
        new_options = st.text_input("पेमेंट के तरीके", value=current_config.get("payment_options", ""))
        
        if st.button("सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["upi_id"] = new_upi
            current_config["payment_options"] = new_options
            current_config["categories"] = [c.strip() for c in cats_str.split(",") if c.strip()]
            save_config(current_config)
            st.success("सेटिंग्स सेव हो गईं!")
            st.rerun()

    # नया उत्पाद जोड़ने का फॉर्म
    st.sidebar.subheader("➕ नया उत्पाद जोड़ें")
    with st.sidebar.form("add_product_form", clear_on_submit=True):
        new_id = st.text_input("प्रोडक्ट ID")
        new_name = st.text_input("उत्पाद का नाम")
        new_price = st.number_input("रेट (₹)", min_value=1)
        new_category = st.selectbox("केटेगरी चुनें", current_config.get("categories", ["General"]))
        uploaded_image = st.file_uploader("तस्वीर चुनें", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("उत्पाद सेव करें") and new_id and new_name and uploaded_image:
            image_path = os.path.join("images", uploaded_image.name)
            with open(image_path, "wb") as f:
                f.write(uploaded_image.getbuffer())
            
            df = load_products()
            new_data = pd.DataFrame([[new_id, new_name, new_price, new_category, image_path]], 
                                    columns=["ID", "Name", "Price", "Category", "Image_Path"])
            df = pd.concat([df, new_data], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.sidebar.success(f"{new_name} जुड़ गया!")
            st.rerun()

# ---------------------------------------------------------
# 3. कस्टमर व्यू (सबके लिए खुला - Main Screen)
# ---------------------------------------------------------

if os.path.exists(BANNER_FILE):
    st.image(BANNER_FILE, use_container_width=True)

st.title("🛍️ Oura")
st.write("अपने पसंदीदा उत्पाद चुनें और सीधा WhatsApp पर ऑर्डर करें।")

if 'cart' not in st.session_state:
    st.session_state.cart = {}

products_df = load_products()

if products_df.empty:
    st.info("जल्द ही नए उत्पाद जोड़े जाएंगे! 🚀")
else:
    # केटेगरी के टैब्स
    categories = current_config.get("categories", ["General"])
    tabs = st.tabs(categories)
    
    for i, cat in enumerate(categories):
        with tabs[i]:
            cat_products = products_df[products_df['Category'] == cat]
            if cat_products.empty:
                st.write("इस केटेगरी में अभी कोई उत्पाद नहीं है।")
            else:
                cols = st.columns(3)
                for index, row in cat_products.reset_index().iterrows():
                    with cols[index % 3]:
                        with st.container(border=True):
                            if os.path.exists(row["Image_Path"]):
                                st.image(row["Image_Path"], use_container_width=True)
                            st.markdown(f"**{row['Name']}**")
                            st.markdown(f"🏷️ ₹{row['Price']}")
                            qty = st.number_input("मात्रा", min_value=1, value=1, key=f"c_qty_{row['ID']}")
                            if st.button("कार्ट में डालें", key=f"c_btn_{row['ID']}"):
                                st.session_state.cart[row['ID']] = {"name": row['Name'], "price": row['Price'], "qty": qty}
                                st.success("बास्केट में जुड़ गया! 🛒")

    st.markdown("---")

    # बास्केट और चेकआउट
    st.header("🛒 आपकी बास्केट (Cart)")

    if st.session_state.cart:
        total_amount = 0
        order_text = "नमस्ते Oura, मैं यह ऑर्डर प्लेस करना चाहता हूँ:\n\n"
        
        for pid, item in st.session_state.cart.items():
            item_total = item['price'] * item['qty']
            total_amount += item_total
            st.write(f"✔️ {item['name']} - {item['qty']} यूनिट (₹{item_total})")
            order_text += f"▪️ {item['name']} x {item['qty']} = ₹{item_total}\n"
        
        st.write(f"### **कुल बिल: ₹{total_amount}**")
        order_text += f"\n*कुल बिल (Total): ₹{total_amount}*\n"
        
        # कस्टमर को पेमेंट की जानकारी दिखाना
        if current_config["upi_id"]:
            st.info(f"💳 **हमारा UPI ID:** {current_config['upi_id']}\n(आप ऑर्डर कंफर्म करने के बाद पेमेंट कर सकते हैं)")
            order_text += "मैं जल्द ही पेमेंट कर दूँगा। कृपया मेरा ऑर्डर पक्का करें!"
        
        # WhatsApp पर भेजने का बटन
        encoded_message = urllib.parse.quote(order_text)
        admin_number = current_config.get("admin_whatsapp", "")
        whatsapp_url = f"https://wa.me/{admin_number}?text={encoded_message}"
        
        st.markdown(f"### [📲 **अपना ऑर्डर WhatsApp पर भेजें**]({whatsapp_url})", unsafe_allow_html=True)
        
        if st.button("बास्केट खाली करें"):
            st.session_state.cart = {}
            st.rerun()
    else:
        st.write("आपकी बास्केट अभी खाली है। ऊपर दिए गए बॉक्स में से उत्पाद चुनें।")
{
    "admin_whatsapp": "919891587437",
    "upi_id": "",
    "payment_options": "UPI, Bank Transfer",
    "categories": [
        "General 📦",
        "Premium 🌟",
        "Offers 🎁"
    


