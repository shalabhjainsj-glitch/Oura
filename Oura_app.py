import streamlit as st
import streamlit.components.v1 as st_components
import pandas as pd
import urllib.parse
import time
import os
import re
import datetime
from firebase_admin import firestore

# --- हमारे बनाए गए नए मॉड्यूल्स (Modules) ---
from utils import upload_image_to_imgbb, compress_image, t, safe_int, safe_float
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
st.set_page_config(page_title="9 Class / Oura - Wholesale", page_icon=app_icon_url, layout="wide")
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- सेशन स्टेट (Session State) ---
if 'lang' not in st.session_state: st.session_state.lang = 'hi'
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'seller_logged_in' not in st.session_state: st.session_state.seller_logged_in = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'share_msg' not in st.session_state: st.session_state.share_msg = None
if 'share_img_path' not in st.session_state: st.session_state.share_img_path = None

# --- प्रोडक्ट्स डेटा ---
products_df = load_products()

def save_cart_to_url():
    if st.session_state.cart:
        cart_str = "_".join([f"{k}*{v['qty']}" for k, v in st.session_state.cart.items()])
        st.query_params["cart"] = cart_str
    elif "cart" in st.query_params:
        del st.query_params["cart"]

def toggle_stock_callback(doc_id, key):
    if key in st.session_state:
        db.collection('products').document(doc_id).update({"In_Stock": st.session_state[key]})
        load_products.clear()

def toggle_fd_callback(doc_id, key):
    if key in st.session_state:
        db.collection('products').document(doc_id).update({"Free_Delivery": st.session_state[key]})
        load_products.clear()

# --- हैडर और लॉगिन (Header & Login) ---
col_logo, col_lang, col_login = st.columns([6, 2, 2])
with col_logo:
    if current_config.get("has_banner", False) and current_config.get("banner_url"):
        try: st.image(current_config["banner_url"], use_container_width=True)
        except: st.title("🛍️ 9 Class / Oura Products - Wholesale")
    else:
        st.title("🛍️ 9 Class / Oura Products - Wholesale")

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

hi_marquee = "🏭 क्या आप भी एक मैन्युफैक्चरर या होलसेलर हैं? आइए, 9 Class / Oura के साथ मिलकर अपने बिज़नेस को नई ऊंचाइयों पर ले जाएं! 🚀"
en_marquee = "🏭 Are you a manufacturer or wholesaler? Let's take your business to new heights with 9 Class / Oura! 🚀"
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

# --- एडमिन और सेलर डैशबोर्ड (Tabs) ---
if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success(t("✅ Logged in as Admin.", "✅ आप एडमिन (मालिक) के रूप में लॉगिन हैं।"))
        tab_add, tab_settings, tab_ledger = st.tabs([t("➕ Add Product", "➕ नया उत्पाद"), t("⚙️ Settings", "⚙️ सेटिंग्स"), t("📒 Ledger", "📒 खाता और बिल")])
    else:
        st.success(t(f"🏪 Welcome: {st.session_state.seller_logged_in} (Seller)", f"🏪 स्वागत है: {st.session_state.seller_logged_in} (Seller)"))
        tab_add, = st.tabs([t("➕ Add Product", "➕ नया उत्पाद")])
    
    with tab_add:
        st.info("यहाँ से आप नया प्रोडक्ट ऐड कर सकते हैं।")
        # (जगह बचाने के लिए Add Product का फॉर्म यहाँ आएगा - आप अपना पुराना फॉर्म यहाँ रख सकते हैं)
        st.write("*(अपना Add Product वाला फॉर्म यहाँ इस्तेमाल करें)*")

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
    # यह आपका पुराना प्रोडक्ट कार्ड दिखाने वाला कोड है
    st.write(f"**{row.get('Name', 'Unknown')}**")
    st.write(f"Rate: ₹{row.get('Price', 0.0)}")
    
    buy_qty = st.number_input("Qty", min_value=1, value=1, key=f"q_{prefix}_{idx}")
    if st.button("🛒 Add to Cart", key=f"btn_{prefix}_{idx}"):
        cart_key = f"{row.get('ID')}|Pcs|{row.get('Price')}"
        st.session_state.cart[cart_key] = {
            "name": row.get('Name'), "price": float(row.get('Price', 0)), 
            "qty": buy_qty, "unit": "Pcs", "img_link": ""
        }
        save_cart_to_url()
        st.success("Added!")

if not products_df.empty:
    if search_query:
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        cols = st.columns(3)
        for idx, row in filtered_df.reset_index().iterrows():
            with cols[idx % 3]: show_product_card(row, idx, "search")
    else:
        st.subheader(t("🛍️ Categories", "🛍️ कैटेगरीज"))
        valid_categories = products_df['Category'].dropna().unique().tolist()
        for cat in valid_categories:
            if st.button(cat): st.write(f"Showing {cat}...")

# --- कार्ट और बिलिंग (Cart & Billing) ---
st.markdown("---")
st.header(t("🛒 Your Basket", "🛒 आपकी बास्केट"))

if st.session_state.cart:
    total = sum([item['price'] * item['qty'] for item in st.session_state.cart.values()])
    for k, item in st.session_state.cart.items():
        st.write(f"✔️ {item['name']} - {item['qty']} {item.get('unit', 'Pcs')} x ₹{item['price']} = ₹{item['price']*item['qty']}")
    st.subheader(f"Total: ₹{total:.2f}")

    st.markdown(f"### 📍 {t('Delivery & Billing Information', 'डिलीवरी और बिल की जानकारी')}")
    with st.form("billing_form"):
        cust_name = st.text_input(t("Your Name", "आपका नाम"))
        cust_mobile = st.text_input(t("Mobile Number", "मोबाईल नंबर"))
        cust_address = st.text_area("Address")
        submit_billing = st.form_submit_button(t("✅ Prepare Bill", "✅ बिल तैयार करें"))

    if submit_billing:
        pdf_bytes = generate_pdf_bill(
            st.session_state.cart, cust_name, cust_mobile, cust_address, 
            "", 0, 0, 0, 0, current_config, datetime.date.today()
        )
        st.session_state.ready_pdf = pdf_bytes
        st.success("✅ Bill Ready!")

    if 'ready_pdf' in st.session_state:
        st.download_button("📄 Download PDF Bill", data=st.session_state.ready_pdf, file_name="Bill.pdf", mime="application/pdf")

# --- AI हेल्प डेस्क (Chatbot) ---
admin_wa_number = current_config.get("admin_whatsapp", "919891587437")
st_components.html(get_ai_js_code(admin_wa_number), height=0, width=0)
