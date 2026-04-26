import streamlit as st
import streamlit.components.v1 as st_components
import pandas as pd
import urllib.parse
import time
import os
import datetime

# --- आपके बनाए गए मॉड्यूल्स (Modules) ---
from utils import t, safe_int, safe_float
from database import db, load_config, save_config, load_products, load_ledger_data
from pdf_generator import generate_pdf_bill
from ui_components import hide_streamlit_style, get_ai_js_code

# --- फोल्डर सेटअप ---
INVOICE_FOLDER = "saved_invoices"
if not os.path.exists(INVOICE_FOLDER): os.makedirs(INVOICE_FOLDER)

GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# --- कॉन्फिग और पेज सेटअप ---
current_config = load_config()
if "sellers" not in current_config: current_config["sellers"] = {}

app_icon_url = current_config.get("logo_url", "🛍️") if current_config.get("has_logo") else "🛍️"
st.set_page_config(page_title="9 Class - Wholesale", page_icon=app_icon_url, layout="wide")
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- प्रोडक्ट्स डेटा लोड करना ---
products_df = load_products()

# --- सेशन स्टेट (Session State) ---
if 'lang' not in st.session_state: st.session_state.lang = 'hi'
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'seller_logged_in' not in st.session_state: st.session_state.seller_logged_in = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'selected_category' not in st.session_state: st.session_state.selected_category = None

# --- कार्ट को रिफ्रेश से बचाने का लॉजिक (URL Saving) ---
def save_cart_to_url():
    if st.session_state.cart:
        cart_str = "_".join([f"{k}*{v['qty']}" for k, v in st.session_state.cart.items()])
        st.query_params["cart"] = cart_str
    elif "cart" in st.query_params:
        del st.query_params["cart"]

if 'cart' not in st.session_state:
    st.session_state.cart = {}
    # रिफ्रेश होने पर URL से कार्ट वापस लाना
    if "cart" in st.query_params and not products_df.empty:
        try:
            cart_str = st.query_params["cart"]
            items = cart_str.split("_")
            for item in items:
                if "*" in item:
                    k_part, qty_str = item.split("*", 1)
                    parts = k_part.split("|")
                    p_id = parts[0]
                    unit = parts[1] if len(parts) > 1 else "Pcs"
                    price = float(parts[2]) if len(parts) > 2 else 0.0
                    qty = safe_int(qty_str, 1)
                    
                    match = products_df[products_df['ID'].astype(str) == p_id]
                    if not match.empty:
                        row = match.iloc[0]
                        img_path = str(row.get("Image_Path", "")).split("|")[0]
                        if img_path and not img_path.startswith("http"):
                            img_path = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_path.replace('\\', '/'), safe='/')}"
                        st.session_state.cart[k_part] = {
                            "name": row.get('Name', 'Item'), "price": price, 
                            "qty": qty, "unit": unit, "img_link": img_path
                        }
        except: pass

if "cat" in st.query_params:
    st.session_state.selected_category = st.query_params["cat"]

# --- हैडर और लॉगिन (Header & Login) ---
col_logo, col_lang, col_login = st.columns([6, 2, 2])
with col_logo:
    if current_config.get("has_banner", False) and current_config.get("banner_url"):
        try: st.image(current_config["banner_url"], use_container_width=True)
        except: st.title("🛍️ 9 Class - Wholesale Market")
    else:
        st.title("🛍️ 9 Class - Wholesale Market")

with col_lang:
    if st.button("🌐 English / हिंदी", key="lang_btn"):
        st.session_state.lang = 'en' if st.session_state.lang == 'hi' else 'hi'
        st.rerun()

with col_login:
    if not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
        if st.button(t("🔒 Login", "🔒 एडमिन / सेलर लॉगिन")):
            st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button(t("🚪 Logout", "🚪 लॉगआउट")):
            st.session_state.admin_logged_in = False
            st.session_state.seller_logged_in = None
            st.session_state.show_login = False
            st.rerun()

hi_marquee = "🏭 क्या आप भी एक मैन्युफैक्चरर या होलसेलर हैं? आइए, 9 Class के साथ मिलकर अपने बिज़नेस को नई ऊंचाइयों पर ले जाएं! 🚀"
en_marquee = "🏭 Are you a manufacturer or wholesaler? Let's take your business to new heights with 9 Class! 🚀"
st.markdown(f'<div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #bbdefb;"><marquee behavior="scroll" direction="left" scrollamount="6" style="color: #0d47a1; font-size: 16px; font-weight: bold;">{t(en_marquee, hi_marquee)}</marquee></div>', unsafe_allow_html=True)

# --- लॉगिन सिस्टम ---
if st.session_state.show_login and not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    with st.container(border=True):
        st.subheader(t("Store Login", "दुकान में लॉगिन करें"))
        login_type = st.radio(t("Select Login Type:", "लॉगिन का प्रकार चुनें:"), [t("Seller", "सेलर (Seller)"), t("Admin", "मालिक / एडमिन (Admin)")], horizontal=True)
        
        if login_type == t("Admin", "मालिक / एडमिन (Admin)"):
            password = st.text_input(t("Enter Admin Password", "एडमिन पासवर्ड डालें"), type="password")
            if st.button(t("Login", "लॉगिन करें")):
                if password == st.secrets.get("ADMIN_PASSWORD", ""):
                    st.session_state.admin_logged_in = True
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error(t("❌ Incorrect Password!", "❌ गलत पासवर्ड!"))
        else:
            seller_token = st.text_input(t("Enter Seller Token", "अपना सेलर टोकन (Token) डालें"), type="password")
            if st.button(t("Login", "लॉगिन करें")):
                if seller_token in current_config.get("sellers", {}):
                    st.session_state.seller_logged_in = current_config["sellers"][seller_token].get("name", seller_token)
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error(t("❌ Invalid Token!", "❌ गलत टोकन!"))
    st.markdown("---")

# --- एडमिन और सेलर डैशबोर्ड ---
if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success(t("✅ Logged in as Admin.", "✅ आप एडमिन (मालिक) के रूप में लॉगिन हैं।"))
        tab_add, tab_settings, tab_ledger = st.tabs([t("➕ Add Product", "➕ नया उत्पाद"), t("⚙️ Settings", "⚙️ सेटिंग्स"), t("📒 Ledger", "📒 खाता और बिल")])
    else:
        st.success(t(f"🏪 Welcome: {st.session_state.seller_logged_in} (Seller)", f"🏪 स्वागत है: {st.session_state.seller_logged_in} (Seller)"))
        tab_add, = st.tabs([t("➕ Add Product", "➕ नया उत्पाद")])
    
    with tab_add:
        st.info("यहाँ से आप नया प्रोडक्ट ऐड कर सकते हैं।")
        st.write("*(भविष्य में प्रोडक्ट ऐड करने का फॉर्म यहाँ रहेगा)*")

    if st.session_state.admin_logged_in:
        with tab_settings:
            st.subheader("📱 Business Settings")
            new_wa = st.text_input("Admin WhatsApp Number", value=current_config.get("admin_whatsapp", "919891587437"))
            new_admin_gst = st.text_input("Admin GST Number", value=current_config.get("admin_gst", "07AKWPB1315K"))
            if st.button("⚙️ Save All Settings"):
                current_config["admin_whatsapp"] = new_wa
                current_config["admin_gst"] = new_admin_gst
                save_config(current_config)
                st.success("✅ Saved!")
                st.rerun()

        with tab_ledger:
            st.subheader("📒 पार्टियों का खाता (Smart Cloud Ledger)")
            all_ledgers = load_ledger_data()
            if not all_ledgers: st.warning("ℹ️ अभी तक किसी पार्टी का खाता नहीं बना है।")
            else:
                for cust_name, df_ledger in all_ledgers.items():
                    with st.expander(f"👤 {cust_name} का खाता"):
                        st.dataframe(df_ledger.drop(columns=['doc_id', 'Timestamp'], errors='ignore'))
    st.markdown("---")

# --- प्रोडक्ट लिस्टिंग और सर्च ---
search_query = st.text_input(t("🔍 Search any product...", "🔍 कोई भी उत्पाद सर्च करें..."), "")

def show_product_card(row, idx, prefix):
    prefix_idx = f"{prefix}_{idx}"
    p_id = str(row.get('ID', prefix_idx)) 
    retail_price = safe_float(row.get('Price'), 0.0)
    
    image_path_str = str(row.get("Image_Path", ""))
    paths = [p.strip() for p in image_path_str.split('|') if p.strip()]
    img_link = paths[0] if paths else ""
    if img_link and not img_link.startswith("http"):
        img_link = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link.replace('\\', '/'), safe='/')}"

    with st.container(border=True):
        if img_link:
            st.image(img_link, use_container_width=True)
            
        st.write(f"**{row.get('Name', 'Unknown')}**")
        st.markdown(f"<span style='color:#2b6cb0; font-size:18px; font-weight:bold;'>₹{retail_price}</span>", unsafe_allow_html=True)
        
        is_in_stock = row.get("In_Stock", True)
        if is_in_stock:
            buy_qty = st.number_input("पीस (Qty)", min_value=1, value=1, key=f"q_{prefix_idx}")
            if st.button("🛒 Add to Cart", key=f"btn_{prefix_idx}"):
                cart_key = f"{p_id}|Pcs|{retail_price}"
                if cart_key in st.session_state.cart:
                    st.session_state.cart[cart_key]["qty"] += buy_qty
                else:
                    st.session_state.cart[cart_key] = {
                        "name": row.get('Name'), "price": retail_price, 
                        "qty": buy_qty, "unit": "Pcs", "img_link": img_link
                    }
                save_cart_to_url() # कार्ट अपडेट होते ही URL में सेव होगा
                st.success("कार्ट में जुड़ गया! 🛒")
        else:
            st.markdown("<div style='color:red; font-weight:bold;'>🚫 Out of Stock</div>", unsafe_allow_html=True)

if not products_df.empty:
    if search_query:
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        cols = st.columns(3)
        for idx, row in filtered_df.reset_index().iterrows():
            with cols[idx % 3]: show_product_card(row, idx, "search")
    
    elif st.session_state.selected_category is None:
        st.subheader(t("🛍️ Categories", "🛍️ कैटेगरीज"))
        valid_categories = products_df['Category'].dropna().unique().tolist()
        
        if valid_categories:
            st.markdown('<div id="safe-cat-grid"></div>', unsafe_allow_html=True)
            st.markdown("""
            <style>
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) {
                display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; justify-content: flex-start !important;
            }
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"] { width: calc(25% - 8px) !important; }
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(#safe-cat-grid),
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(style) { display: none !important; }
            
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button {
                height: 90px !important; min-height: 90px !important; width: 100% !important; border-radius: 12px !important;
                background: #ffffff !important; border: 2px solid #e2e8f0 !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.08) !important; color: #1a202c !important; 
                font-weight: 700 !important; font-size: 13px !important; white-space: normal !important; 
                word-wrap: break-word !important; line-height: 1.2 !important; padding: 4px !important; 
                transition: all 0.2s ease-in-out !important; display: flex !important;
                align-items: center !important; justify-content: center !important; text-align: center !important;
            }
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button:hover { transform: translateY(-3px) !important; box-shadow: 0 6px 12px rgba(43, 108, 176, 0.2) !important; border-color: #2b6cb0 !important; color: #2b6cb0 !important;}
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button:active { transform: scale(0.95) !important; }
            </style>
            """, unsafe_allow_html=True)

            for idx, cat in enumerate(valid_categories):
                if st.button(cat, key=f"cat_btn_{idx}"):
                    st.session_state.selected_category = cat
                    st.query_params["cat"] = cat
                    save_cart_to_url() # रिफ्रेश के लिए कार्ट सुरक्षित
                    st.rerun()
    else:
        st.subheader(f"📂 {st.session_state.selected_category}")
        if st.button("🏠 वापस सारे बॉक्स पर जाएं"):
            st.session_state.selected_category = None
            if "cat" in st.query_params: del st.query_params["cat"]
            save_cart_to_url()
            st.rerun()
            
        cat_products = products_df[products_df['Category'] == st.session_state.selected_category]
        if cat_products.empty: 
            st.warning("इस बॉक्स में अभी कोई उत्पाद नहीं है।")
        else:
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "cat_view")

# --- कार्ट और बिलिंग (Cart & Billing) ---
st.markdown("---")
st.header(t("🛒 Your Basket", "🛒 आपकी बास्केट"))

if st.session_state.cart:
    total = sum([item['price'] * item['qty'] for item in st.session_state.cart.values()])
    for k, item in list(st.session_state.cart.items()):
        col1, col2 = st.columns([8, 2])
        with col1:
            st.write(f"✔️ {item['name']} - {item['qty']} {item.get('unit', 'Pcs')} x ₹{item['price']} = ₹{item['price']*item['qty']}")
        with col2:
            if st.button("❌", key=f"del_{k}"):
                del st.session_state.cart[k]
                save_cart_to_url()
                st.rerun()
                
    st.subheader(f"Total: ₹{total:.2f}")

    st.markdown(f"### 📍 {t('Delivery & Billing Information', 'डिलीवरी और बिल की जानकारी')}")
    with st.form("billing_form"):
        cust_name = st.text_input(t("Your Name", "आपका नाम"))
        cust_mobile = st.text_input(t("Mobile Number", "मोबाईल नंबर"))
        cust_address = st.text_area("Address")
        submit_billing = st.form_submit_button(t("✅ Prepare Bill", "✅ बिल तैयार करें"))

    if submit_billing:
        # बिल बनने के बाद कार्ट को खाली करने का लॉजिक
        pdf_bytes = generate_pdf_bill(
            st.session_state.cart, cust_name, cust_mobile, cust_address, 
            "", 0, 0, 0, 0, current_config, datetime.date.today()
        )
        st.session_state.ready_pdf = pdf_bytes
        
        # 🗑️ बिल बनने के बाद बास्केट साफ करें
        st.session_state.cart = {}
        save_cart_to_url()
        st.success("✅ बिल तैयार है! आपका कार्ट भी खाली कर दिया गया है।")

    if 'ready_pdf' in st.session_state:
        st.download_button("📄 Download PDF Bill", data=st.session_state.ready_pdf, file_name="Bill.pdf", mime="application/pdf")

    # 🗑️ मैन्युअल बास्केट खाली करने का बटन
    if st.session_state.cart:
        if st.button("🗑️ बास्केट खाली करें"):
            st.session_state.cart = {}
            if 'ready_pdf' in st.session_state: del st.session_state.ready_pdf
            save_cart_to_url()
            st.rerun()
else:
    st.info("आपकी बास्केट अभी खाली है।")

# --- AI हेल्प डेस्क (Chatbot) ---
admin_wa_number = current_config.get("admin_whatsapp", "919891587437")
st_components.html(get_ai_js_code(admin_wa_number), height=0, width=0)
