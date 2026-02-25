import streamlit as st
import pandas as pd
import os
import urllib.parse
import json

# 1. ऐप का सेटअप
st.set_page_config(page_title="Oura - Wholesale", page_icon="🛍️", layout="wide")

CONFIG_FILE = "config.json"
DATA_FILE = "oura_products.csv"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "admin_whatsapp": "919891587437", 
        "categories": ["cloth", "electronic", "electrical", "toys", "Footwear"],
        "banner_url": "" # अब बैनर भी लिंक से चलेगा
    }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

current_config = load_config()

# डेटाबेस सेटअप (अब हमें images फोल्डर की जरूरत नहीं है)
def init_db():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_URL"])
        df.to_csv(DATA_FILE, index=False)
    else:
        df = pd.read_csv(DATA_FILE)
        # अगर पुराना डेटाबेस है, तो उसे नए सिस्टम (URL) के हिसाब से अपडेट करें
        if "Image_URL" not in df.columns:
            if "Image_Path" in df.columns:
                df.rename(columns={"Image_Path": "Image_URL"}, inplace=True)
            else:
                df["Image_URL"] = ""
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
        new_banner = st.text_input("बैनर फोटो का लिंक (URL)", value=current_config.get("banner_url", ""))
        
        if st.button("सेटिंग्स सेव करें"):
            current_config["admin_whatsapp"] = new_wa
            current_config["categories"] = [c.strip() for c in cats_str.split(",") if c.strip()]
            current_config["banner_url"] = new_banner
            save_config(current_config)
            st.success("सेटिंग्स सेव हो गईं!")
            st.rerun()

    st.sidebar.subheader("➕ नया उत्पाद जोड़ें")
    with st.sidebar.form("add_product", clear_on_submit=True):
        new_id = st.text_input("ID (यूनिक रखें, जैसे: P001)")
        new_name = st.text_input("नाम")
        new_price = st.number_input("रिटेल रेट (1 पीस का)", min_value=1)
        new_w_qty = st.number_input("होलसेल के लिए कम से कम पीस", min_value=1, value=10)
        new_w_price = st.number_input("होलसेल रेट (प्रति पीस)", min_value=1)
        new_cat = st.selectbox("केटेगरी", current_config.get("categories", ["General"]))
        img_url = st.text_input("फोटो का लिंक (Image URL डालें)") # फोटो अपलोड की जगह लिंक
        
        if st.form_submit_button("सेव करें"):
            if new_id and new_name and img_url:
                df = load_products()
                new_row = pd.DataFrame([[new_id, new_name, new_price, new_w_price, new_w_qty, new_cat, img_url]], columns=df.columns)
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.sidebar.success("✅ प्रोडक्ट जुड़ गया!")
                st.rerun()
            else:
                st.sidebar.error("⚠️ कृपया ID, नाम और फोटो का लिंक जरूर डालें।")

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
            st.sidebar.success("उत्पाद हटा दिया गया!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🧨 पूरा डेटाबेस साफ करें")
    if st.sidebar.button("सब कुछ डिलीट करें (Reset)"):
        df_empty = pd.DataFrame(columns=["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_URL"])
        df_empty.to_csv(DATA_FILE, index=False)
        st.sidebar.success("सब कुछ साफ हो गया!")
        st.rerun()

# 3. कस्टमर व्यू
banner_url = current_config.get("banner_url", "")
if banner_url:
    try:
        st.image(banner_url, use_container_width=True)
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
    all_saved_cats = products_df['Category'].dropna().unique()
    missing_cats = [c for c in all_saved_cats if c not in app_categories]
    
    display_tabs = app_categories.copy()
    if missing_cats:
        display_tabs.append("अन्य")

    tabs = st.tabs(display_tabs)
    
    for i, tab_name in enumerate(display_tabs):
        with tabs[i]:
            if tab_name == "अन्य":
                cat_products = products_df[products_df['Category'].isin(missing_cats)]
            else:
                cat_products = products_df[products_df['Category'] == tab_name]
            
            if cat_products.empty:
                st.write("इस केटेगरी में अभी कोई उत्पाद नहीं है।")
            else:
                cols = st.columns(2) # मोबाइल के लिए 2 कॉलम बेहतरीन हैं
                for idx, row in cat_products.reset_index().iterrows():
                    with cols[idx % 2]:
                        with st.container(border=True):
                            img_url = str(row.get("Image_URL", ""))
                            if img_url:
                                try:
                                    st.image(img_url, use_container_width=True)
                                except:
                                    st.warning("⚠️ फोटो लिंक खराब है")
                            else:
                                st.warning("⚠️ फोटो उपलब्ध नहीं")
                                
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
                                st.markdown(f"**रिटेल:** ₹{row['Price']} <br> **होलसेल:** ₹{w_price} *(min {w_qty} pcs)*", unsafe_allow_html=True)
                            else:
                                st.markdown(f"**रेट:** ₹{row['Price']}")
                                
                            qty = st.number_input("मात्रा", min_value=1, value=1, key=f"q_{idx}_{row['ID']}")
                            
                            if st.button("कार्ट में डालें", key=f"b_{idx}_{row['ID']}"):
                                final_price = w_price if qty >= w_qty else row['Price']
                                
                                st.session_state.cart[f"{idx}_{row['ID']}"] = {
                                    "name": row['Name'], 
                                    "price": final_price, 
                                    "qty": qty,
                                    "img_link": img_url
                                }
                                st.success("जुड़ गया! 🛒")

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
        msg += f"   🖼️ Link: {item['img_link']}\n"
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












