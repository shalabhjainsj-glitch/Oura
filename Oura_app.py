import streamlit as st
import pandas as pd
import os
import urllib.parse
import json
import shutil

# 1. ऐप का सेटअप
st.set_page_config(page_title="Oura - Wholesale", page_icon="🛍️", layout="wide")

BANNER_FILE = "banner.png" 
CONFIG_FILE = "config.json"
DATA_FILE = "oura_products.csv"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/shalabhjainsj-glitch/Oura/main/"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "admin_whatsapp": "919891587437", 
        "upi_id": "", 
        "payment_options": "UPI, Bank Transfer",
        "categories": ["cloth", "electronic", "electrical", "toys", "Footwear"] 
    }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

current_config = load_config()

# डेटाबेस सेटअप
if not os.path.exists("images"):
    os.makedirs("images")

def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_Path"])
        df.to_csv(DATA_FILE, index=False)
    else:
        df = pd.read_csv(DATA_FILE)
        if "Wholesale_Price" not in df.columns:
            df["Wholesale_Price"] = df["Price"]
            df["Wholesale_Qty"] = 1
            df.to_csv(DATA_FILE, index=False)

init_db()

def load_products():
    try:
        return pd.read_csv(DATA_FILE)
    except:
        return pd.DataFrame()

# 2. एडमिन पैनल
st.sidebar.title("🔒 एडमिन पैनल")

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    password = st.sidebar.text_input("पासवर्ड डालें", type="password")
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
        cats_str = st.text_area("कैटगरी (कॉमा लगाकर लिखें)", value=", ".join(current_config.get("categories", [])))
        new_banner = st.file_uploader("बैनर बदलें", type=["jpg", "png", "jpeg"])
        if new_banner is not None:
            with open(BANNER_FILE, "wb") as f:
                f.write(new_banner.getbuffer())
            st.success("बैनर अपडेट हो गया!")
            
        if st.button("सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["categories"] = [c.strip() for c in cats_str.split(",") if c.strip()]
            save_config(current_config)
            st.success("सेटिंग्स सेव!")
            st.rerun()

    st.sidebar.subheader("➕ नया उत्पाद जोड़ें")
    with st.sidebar.form("add_product", clear_on_submit=True):
        new_id = st.text_input("ID (यूनिक रखें, जैसे: P001)")
        new_name = st.text_input("नाम")
        new_price = st.number_input("रिटेल रेट (1 पीस का)", min_value=1)
        new_w_qty = st.number_input("होलसेल के लिए कम से कम पीस (जैसे 100)", min_value=1, value=10)
        new_w_price = st.number_input("होलसेल रेट (प्रति पीस)", min_value=1)
        new_cat = st.selectbox("केटेगरी", current_config.get("categories", ["General"]))
        img = st.file_uploader("फोटो", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("सेव करें") and new_id and new_name and img:
            path = os.path.join("images", img.name.replace(" ", "_"))
            with open(path, "wb") as f:
                f.write(img.getbuffer())
            df = load_products()
            new_row = pd.DataFrame([[new_id, new_name, new_price, new_w_price, new_w_qty, new_cat, path]], columns=df.columns)
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.sidebar.success("✅ प्रोडक्ट जुड़ गया!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ उत्पाद हटाएं (Delete)")
    df_del = load_products()
    if not df_del.empty:
        product_list = df_del['ID'].astype(str) + " - " + df_del['Name'] + " [" + df_del['Category'].astype(str) + "]"
        item_to_delete = st.sidebar.selectbox("हटाने के लिए उत्पाद चुनें:", product_list)
        
        if st.sidebar.button("❌ पक्का डिलीट करें"):
            del_id = item_to_delete.split(" - ")[0]
            df_updated = df_del[df_del['ID'].astype(str) != del_id]
            df_updated.to_csv(DATA_FILE, index=False)
            st.sidebar.success(f"उत्पाद हटा दिया गया!")
            st.rerun()
    else:
        st.sidebar.write("अभी कोई उत्पाद नहीं है।")

    # नया क्लीनअप फीचर (पूरा डेटाबेस साफ करने के लिए)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧨 पूरा डेटाबेस साफ करें")
    st.sidebar.caption("अगर ऐप अटक जाए या पुराना कचरा न जाए, तो इसे दबाएं।")
    if st.sidebar.button("सब कुछ डिलीट करें (Reset)"):
        # डेटा फाइल खाली करें
        df_empty = pd.DataFrame(columns=["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_Path"])
        df_empty.to_csv(DATA_FILE, index=False)
        # पुरानी इमेजेज उड़ा दें
        if os.path.exists("images"):
            shutil.rmtree("images")
        os.makedirs("images")
        st.sidebar.success("सब कुछ साफ हो गया! ऐप एकदम नया है।")
        st.rerun()

# 3. कस्टमर व्यू
if os.path.isfile(BANNER_FILE):
    try:
        st.image(BANNER_FILE, use_container_width=True)
    except:
        pass

st.title("🛍️ Oura")
if 'cart' not in st.session_state:
    st.session_state.cart = {}

products_df = load_products()

if products_df.empty:
    st.info("जल्द ही नए उत्पाद आएंगे!")
else:
    app_categories = current_config.get("categories", ["General"])
    # स्मार्ट फिल्टर: सिर्फ वही केटेगरी दिखाएं जो सेटिंग्स में हैं
    tabs = st.tabs(app_categories)
    
    for i, tab_name in enumerate(app_categories):
        with tabs[i]:
            cat_products = products_df[products_df['Category'] == tab_name]
            
            # ऑटो-हाइड: उन प्रोडक्ट्स को लिस्ट से बाहर कर दें जिनकी फोटो फाइल नहीं मिल रही
            valid_products = []
            for _, r in cat_products.iterrows():
                if os.path.isfile(str(r.get("Image_Path", ""))):
                    valid_products.append(r)
            
            if not valid_products:
                st.write("इस केटेगरी में अभी कोई नया उत्पाद नहीं है।")
            else:
                valid_df = pd.DataFrame(valid_products)
                cols = st.columns(3)
                for idx, row in valid_df.reset_index().iterrows():
                    with cols[idx % 3]:
                        with st.container(border=True):
                            img_path = str(row.get("Image_Path", ""))
                            st.image(img_path, use_container_width=True)
                                
                            st.write(f"**{row['Name']}**")
                            
                            try:
                                w_qty = int(float(row.get('Wholesale_Qty', 1)))
                            except:
                                w_qty = 1
                                
                            try:
                                w_price = int(float(row.get('Wholesale_Price', row['Price'])))
                            except:
                                w_price = row['Price']
                            
                            if w_qty > 1:
                                st.markdown(f"**रिटेल:** ₹{row['Price']} <br> **होलसेल:** ₹{w_price} *(कम से कम {w_qty} पीस)*", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**रेट:** ₹{row['Price']}")
                                
                            qty = st.number_input("मात्रा (पीस)", min_value=1, value=1, key=f"q_{idx}_{row['ID']}")
                            
                            if st.button("कार्ट में डालें", key=f"b_{idx}_{row['ID']}"):
                                final_price = w_price if qty >= w_qty else row['Price']
                                img_link = GITHUB_RAW_URL + urllib.parse.quote(img_path)
                                
                                st.session_state.cart[f"{idx}_{row['ID']}"] = {
                                    "name": row['Name'], 
                                    "price": final_price, 
                                    "qty": qty,
                                    "img_link": img_link
                                }
                                st.success("कार्ट में जुड़ गया! 🛒")

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
        msg += f"   🖼️ {item['img_link']}\n"
        count += 1
    
    msg += f"\n💰 *कुल बिल:* ₹{total}\n"
    msg += "⚠️ *पैकिंग व ट्रांसपोर्ट Extra*"
    
    st.subheader(f"कुल बिल: ₹{total}")
    st.info("⚠️ नोट: पैकिंग व ट्रांसपोर्ट चार्ज Extra (अलग से लगेंगे)")
    
    if st.button("WhatsApp पर ऑर्डर भेजें"):
        encoded_msg = urllib.parse.quote(msg)
        st.write(f"👉 [यहाँ क्लिक करके WhatsApp भेजें](https://wa.me/{current_config['admin_whatsapp']}?text={encoded_msg})")
    
    if st.button("बास्केट खाली करें"):
        st.session_state.cart = {}
        st.rerun()









