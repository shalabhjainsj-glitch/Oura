import streamlit as st
import streamlit.components.v1 as st_components
import pandas as pd
import urllib.parse
import json
import time
import random
import string
import re
import io
import os
import requests
import base64
from PIL import Image
import datetime
from fpdf import FPDF

# --- फोल्डर सेटअप (PDF के लिए) ---
INVOICE_FOLDER = "saved_invoices"
if not os.path.exists(INVOICE_FOLDER): os.makedirs(INVOICE_FOLDER)

# --- फायरबेस सिस्टम ---
import firebase_admin
from firebase_admin import credentials, firestore

GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# --- Firebase को चालू करना ---
if not firebase_admin._apps:
    try:
        firebase_secrets = st.secrets["FIREBASE_JSON"]
        if isinstance(firebase_secrets, str):
            cleaned_str = firebase_secrets.replace('“', '"').replace('”', '"')
            key_dict = json.loads(cleaned_str, strict=False)
        else:
            key_dict = dict(firebase_secrets)
        
        if 'private_key' in key_dict:
            key_dict['private_key'] = key_dict['private_key'].replace('\\n', '\n')
            
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"🚨 Firebase सेटअप में गलती: {e}")

db = firestore.client()

def upload_image_to_imgbb(file_bytes):
    try:
        imgbb_key = st.secrets.get("IMGBB_API_KEY")
        if not imgbb_key: return None
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": imgbb_key, "image": base64.b64encode(file_bytes).decode('utf-8')}
        res = requests.post(url, data=payload)
        if res.status_code == 200: return res.json()["data"]["url"]
        return None
    except Exception as e: return None

def compress_image(image_bytes):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        if pil_img.mode != 'RGB': pil_img = pil_img.convert('RGB')
        max_width = 800
        if pil_img.width > max_width:
            ratio = max_width / float(pil_img.width)
            new_height = int((float(pil_img.height) * float(ratio)))
            pil_img = pil_img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        compressed_io = io.BytesIO()
        pil_img.save(compressed_io, format='JPEG', quality=75)
        return compressed_io.getvalue(), pil_img
    except Exception as e: return image_bytes, None

def load_config():
    try:
        doc = db.collection('settings').document('config').get()
        if doc.exists: return doc.to_dict()
    except: pass
    return {
        "admin_whatsapp": "919891587437", "admin_gst": "07AKWPB1315K", 
        "phonepe_upi": "", "paytm_upi": "", "gpay_upi": "", "bhim_upi": "", "upi_id": "",
        "has_banner": False, "has_logo": False, "free_delivery_tag": True, "sellers": {}
    }

def save_config(config):
    db.collection('settings').document('config').set(config)

current_config = load_config()
if "sellers" not in current_config: current_config["sellers"] = {}

# --- PDF बिल जेनरेटर (फोटो के साथ) ---
def generate_pdf_bill(cart, cust_name, cust_mobile, cust_address, cust_gst, gst_rate, shipping_charge, last_balance, amount_paid, config, invoice_date):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(43, 108, 176)
    pdf.cell(0, 10, "9 CLASS PRODUCTS", ln=True, align='C') 
    
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(100, 100, 100)
    admin_phone = config.get("admin_whatsapp", "9891587437")
    admin_gst_number = config.get("admin_gst", "07AKWPB1315K").strip().upper()
    pdf.cell(0, 6, f"Delhi, India | Ph: +91 {admin_phone}", ln=True, align='C')
    if gst_rate > 0 and admin_gst_number: pdf.cell(0, 6, f"GSTIN: {admin_gst_number}", ln=True, align='C')
        
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    title = "TAX INVOICE" if gst_rate > 0 else "ESTIMATE / QUOTATION"
    pdf.cell(0, 8, title, ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(20, 6, "Billed To:")
    pdf.set_font("Arial", '', 10)
    c_name = cust_name if cust_name else "Cash/Walk-in Customer"
    pdf.cell(100, 6, c_name)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 6, "Invoice Date: ")
    pdf.set_font("Arial", '', 10)
    pdf.cell(40, 6, str(invoice_date), ln=True)
    
    pdf.cell(20, 6, "")
    pdf.cell(100, 6, f"Ph: {cust_mobile if cust_mobile else 'N/A'}")
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 6, "Invoice No: ")
    pdf.set_font("Arial", '', 10)
    inv_no = f"OURA-{datetime.datetime.now().strftime('%m%d%H%M')}"
    pdf.cell(40, 6, inv_no, ln=True)
    
    if cust_address:
        pdf.cell(20, 6, "")
        pdf.multi_cell(100, 6, f"Address: {cust_address}")
        
    if gst_rate > 0:
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(20, 6, "")
        if cust_gst and cust_gst.strip(): pdf.cell(100, 6, f"GSTIN: {cust_gst.strip().upper()}", ln=True)
        else: pdf.cell(100, 6, "GSTIN: Unregistered Consumer", ln=True)
        
    pdf.ln(10)
    
    # टेबल हैडर (Pic के साथ)
    pdf.set_fill_color(230, 240, 255) 
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(10, 10, "S.No", border=1, align='C', fill=True)
    pdf.cell(15, 10, "Pic", border=1, align='C', fill=True) # फोटो कॉलम
    pdf.cell(80, 10, "Item Description", border=1, align='L', fill=True)
    pdf.cell(25, 10, "Qty", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Rate (Rs)", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Amount", border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    subtotal = 0
    idx = 1
    
    for k, item in cart.items():
        amt = item['price'] * item['qty']
        subtotal += amt
        clean_name = re.sub(r'[^\x00-\x7F]+', ' ', str(item['name'])) 
        if len(clean_name) > 35: clean_name = clean_name[:32] + "..."
        
        y_before = pdf.get_y()
        
        # फोटो छापने का कोड
        pdf.cell(10, 10, str(idx), border=1, align='C')
        
        if item.get('img_link'):
            try:
                res = requests.get(item['img_link'], timeout=3)
                img_data = io.BytesIO(res.content)
                pdf.image(img_data, x=22, y=y_before+1, w=11, h=8)
            except:
                pass # अगर फोटो लोड न हो तो खाली रहने दें
        
        pdf.cell(15, 10, "", border=1) # फोटो के लिए खाली जगह
        pdf.cell(80, 10, clean_name, border=1, align='L')
        unit_display = item.get('unit', 'Pcs')
        pdf.cell(25, 10, f"{item['qty']} {unit_display[:5]}", border=1, align='C')
        pdf.cell(30, 10, f"{item['price']:.2f}", border=1, align='R')
        pdf.cell(30, 10, f"{amt:.2f}", border=1, align='R')
        pdf.ln()
        idx += 1
        
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(160, 10, "Subtotal", border=1, align='R')
    pdf.cell(30, 10, f"{subtotal:.2f}", border=1, align='R')
    pdf.ln()
    
    taxable_amount = subtotal
    if shipping_charge > 0:
        pdf.cell(160, 10, "Add: Shipping / Courier Charges", border=1, align='R')
        pdf.cell(30, 10, f"{shipping_charge:.2f}", border=1, align='R')
        pdf.ln()
        taxable_amount += shipping_charge 
    
    gst_amt = 0
    if gst_rate > 0:
        gst_amt = (taxable_amount * gst_rate) / 100
        pdf.cell(160, 10, f"Add: GST @ {gst_rate}%", border=1, align='R')
        pdf.cell(30, 10, f"{gst_amt:.2f}", border=1, align='R')
        pdf.ln()
        
    grand_total = taxable_amount + gst_amt

    if last_balance > 0:
        pdf.cell(160, 10, "Add: Previous Balance (Pichla Bakaya)", border=1, align='R')
        pdf.cell(30, 10, f"{last_balance:.2f}", border=1, align='R')
        pdf.ln()
        grand_total += last_balance
    elif last_balance < 0:
        pdf.cell(160, 10, "Less: Previous Advance (Pichla Jama)", border=1, align='R')
        pdf.cell(30, 10, f"{abs(last_balance):.2f}", border=1, align='R')
        pdf.ln()
        grand_total -= abs(last_balance)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 255, 220) 
    pdf.cell(160, 12, "GRAND TOTAL (Rs)", border=1, align='R', fill=True)
    pdf.cell(30, 12, f"{grand_total:.2f}", border=1, align='R', fill=True)
    pdf.ln()

    if amount_paid > 0:
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(160, 10, "Less: Amount Paid Now", border=1, align='R')
        pdf.cell(30, 10, f"{amount_paid:.2f}", border=1, align='R')
        pdf.ln()
        balance_due = grand_total - amount_paid
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(255, 200, 200) 
        pdf.cell(160, 12, "NET BALANCE DUE (Rs)", border=1, align='R', fill=True)
        pdf.cell(30, 12, f"{balance_due:.2f}", border=1, align='R', fill=True)
        pdf.ln()
    else: pdf.ln(5)

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 5, "Terms & Conditions:", ln=True)
    pdf.cell(0, 5, "1. Goods once sold will not be taken back without valid manufacturing defect.", ln=True)
    pdf.cell(0, 5, "2. We are not responsible for any transit/courier damages.", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 5, "For 9 CLASS PRODUCTS", ln=True, align='R') 
    
    return pdf.output(dest='S').encode('latin1')

app_icon_url = current_config.get("logo_url", "🛍️") if current_config.get("has_logo") else "🛍️"

st.set_page_config(page_title="9 Class - Wholesale", page_icon=app_icon_url, layout="wide")

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stDecoration"] {visibility: hidden; height: 0%; display: none;}
.stApp { background-color: #f4f6f9; }
div.stButton > button { background-color: #2b6cb0; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important; padding: 10px !important; min-height: 50px; }
div.stButton > button:hover { background-color: #2c5282; }
div[data-testid="stContainer"] { background-color: #ffffff; border-radius: 10px !important; border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 15px; }
div[data-testid="stExpander"] { background-color: #ffffff; border-radius: 8px; border-left: 4px solid #2b6cb0 !important; border-top: 1px solid #e2e8f0; }
.swipe-gallery { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding-bottom: 5px; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
.swipe-gallery::-webkit-scrollbar { display: none; }
.swipe-gallery a { scroll-snap-align: center; flex: 0 0 100%; max-width: 100%; text-decoration: none; }
.swipe-img { width: 100%; height: 300px; object-fit: contain; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if 'lang' not in st.session_state: st.session_state.lang = 'hi'
def t(en_text, hi_text): return en_text if st.session_state.lang == 'en' else hi_text

def safe_int(val, default=1):
    try: return int(float(val)) if val and str(val).strip() != "" else default
    except: return default

def safe_float(val, default=0.0):
    try: return float(val) if val and str(val).strip() != "" else default
    except: return default

expected_columns = ["ID", "Name", "Retail_Qty", "Price", "Tier1_Price", "Tier1_Qty", "Tier2_Price", "Tier2_Qty", "Category", "Image_Path", "Free_Delivery", "Seller_Name", "In_Stock", "Unit_Base", "Unit_T1", "Unit_T2"]

@st.cache_data(ttl=3600, show_spinner=False)
def load_products():
    try:
        docs = db.collection('products').stream()
        data = [doc.to_dict() for doc in docs]
        if data:
            df = pd.DataFrame(data)
            for col in ['Unit_Base', 'Unit_T1', 'Unit_T2']:
                if col not in df.columns: df[col] = df.get('Unit_Type', 'Pcs')
                df[col].fillna('Pcs', inplace=True)
            return df
    except: pass
    return pd.DataFrame(columns=expected_columns)

@st.cache_data(ttl=300, show_spinner=False)
def load_ledger_data():
    ledger_data = {}
    try:
        customers = db.collection('ledgers').stream()
        for cust in customers:
            if cust.id == "config": continue
            docs = db.collection('ledgers').document(cust.id).collection('transactions').order_by("Date").stream()
            transactions = [doc.to_dict() | {'doc_id': doc.id} for doc in docs]
            if transactions: ledger_data[cust.id] = pd.DataFrame(transactions)
    except: pass
    return ledger_data

products_df = load_products()

def save_cart_to_url():
    if st.session_state.cart:
        cart_str = "_".join([f"{k}*{v['qty']}" for k, v in st.session_state.cart.items()])
        st.query_params["cart"] = cart_str
    else:
        if "cart" in st.query_params: del st.query_params["cart"]

if 'cart_loaded' not in st.session_state:
    st.session_state.cart = {}
    if "cart" in st.query_params and not products_df.empty:
        cart_str = st.query_params["cart"]
        for item in cart_str.split("_"):
            try:
                if "*" in item:
                    k_part, qty_str = item.split("*", 1)
                    parts = k_part.split("|")
                    p_id = parts[0]
                    unit = parts[1] if len(parts) > 1 else "Pcs"
                    price = float(parts[2]) if len(parts) > 2 else 0.0
                    match = products_df[products_df['ID'].astype(str) == p_id]
                    if not match.empty:
                        row = match.iloc[0]
                        img_link = str(row.get("Image_Path", "")).split('|')[0].strip()
                        if img_link and not img_link.startswith("http"): img_link = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link.replace('\\', '/'), safe='/')}"
                        st.session_state.cart[k_part] = {
                            "name": row.get('Name', 'Item'), "price": price, "qty": safe_int(qty_str, 1), 
                            "img_link": img_link, "unit": unit
                        }
            except: pass
    st.session_state.cart_loaded = True

if "cat" in st.query_params: st.session_state.selected_category = st.query_params["cat"]
else: st.session_state.selected_category = None

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'seller_logged_in' not in st.session_state: st.session_state.seller_logged_in = None
if 'show_login' not in st.session_state: st.session_state.show_login = False

col_logo, col_lang, col_login = st.columns([6, 2, 2])
with col_logo:
    if current_config.get("has_banner", False) and current_config.get("banner_url"):
        try: st.image(current_config["banner_url"], use_container_width=True)
        except: st.title("🛍️ 9 Class Products")
    else: st.title("🛍️ 9 Class Products - Wholesale")

with col_lang:
    if st.button("🌐 English / हिंदी", key="lang_btn"):
        st.session_state.lang = 'en' if st.session_state.lang == 'hi' else 'hi'
        st.rerun()

with col_login:
    if not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
        if st.button(t("🔒 Login", "🔒 लॉगिन")): st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button(t("🚪 Logout", "🚪 लॉगआउट")):
            st.session_state.admin_logged_in = False
            st.session_state.seller_logged_in = None
            st.session_state.show_login = False
            st.rerun()

st.markdown(f'<div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #bbdefb;"><marquee behavior="scroll" direction="left" scrollamount="6" style="color: #0d47a1; font-size: 16px; font-weight: bold;">{t("🏭 Are you a manufacturer or wholesaler? Lets grow with 9 Class! 🚀", "🏭 क्या आप भी एक मैन्युफैक्चरर या होलसेलर हैं? आइए, 9 Class के साथ मिलकर अपने बिज़नेस को नई ऊंचाइयों पर ले जाएं! 🚀")}</marquee></div>', unsafe_allow_html=True)

if st.session_state.show_login and not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    with st.container(border=True):
        login_type = st.radio(t("Select Login Type:", "लॉगिन का प्रकार चुनें:"), [t("Seller", "सेलर"), t("Admin", "एडमिन")], horizontal=True)
        if login_type == t("Admin", "एडमिन"):
            password = st.text_input(t("Enter Admin Password", "एडमिन पासवर्ड"), type="password")
            if st.button(t("Login", "लॉगिन करें")):
                if password == st.secrets.get("ADMIN_PASSWORD", ""):
                    st.session_state.admin_logged_in = True
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("❌ गलत पासवर्ड!")
        else:
            seller_token = st.text_input(t("Enter Seller Token", "सेलर टोकन"), type="password")
            if st.button(t("Login", "लॉगिन करें")):
                if seller_token in current_config.get("sellers", {}):
                    s_data = current_config["sellers"][seller_token]
                    st.session_state.seller_logged_in = s_data["name"] if isinstance(s_data, dict) else s_data
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("❌ गलत टोकन!")

if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success(t("✅ Logged in as Admin.", "✅ आप एडमिन के रूप में लॉगिन हैं।"))
        tab_add, tab_banner, tab_settings, tab_ledger = st.tabs([t("➕ Add Product", "➕ नया उत्पाद"), t("🖼️ Banner", "🖼️ बैनर"), t("⚙️ Settings", "⚙️ सेटिंग्स"), t("📒 Ledger", "📒 खाते")])
    else:
        st.success(f"🏪 Welcome: {st.session_state.seller_logged_in}")
        tab_add, = st.tabs([t("➕ Add Product", "➕ नया उत्पाद")])
    
    with tab_add:
        with st.form("add_product", clear_on_submit=True):
            col_id, col_name = st.columns([1, 2])
            with col_id: new_id = st.text_input("ID (यूनिक रखें)")
            with col_name: new_name = st.text_input("Product Name (नाम)")
            
            st.markdown("**💰 Pricing Tiers (रेट और यूनिट)**")
            u_opts = ["Pcs", "Dozen", "Box", "Set"]
            c1, c2, c3 = st.columns(3)
            with c1: new_u_base = st.selectbox("इकाई (Unit)", u_opts, key="ub")
            with c2: new_retail_qty = st.number_input("कम से कम मात्रा", min_value=1, value=1)
            with c3: new_price = st.number_input("रेट (₹)", min_value=0.0, format="%.2f")
            
            c4, c5, c6 = st.columns(3)
            with c4: new_u_t1 = st.selectbox("इकाई (Tier 1)", u_opts, index=1)
            with c5: new_t1_qty = st.number_input("Tier 1 मात्रा", min_value=0, value=0)
            with c6: new_t1_price = st.number_input("Tier 1 रेट (₹)", min_value=0.0, format="%.2f")
            
            c7, c8, c9 = st.columns(3)
            with c7: new_u_t2 = st.selectbox("इकाई (Tier 2)", u_opts, index=2)
            with c8: new_t2_qty = st.number_input("Tier 2 मात्रा", min_value=0, value=0)
            with c9: new_t2_price = st.number_input("Tier 2 रेट (₹)", min_value=0.0, format="%.2f")
            
            new_free_delivery = st.selectbox("Delivery", ["Free Delivery", "Extra Courier Charge"])
            new_in_stock = st.checkbox("✅ In Stock", value=True)
            
            existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
            selected_cat = st.selectbox("Category (बॉक्स)", ["नयी केटेगरी बनाएं..."] + existing_cats)
            final_cat = st.text_input("New Category Name") if selected_cat == "नयी केटेगरी बनाएं..." else selected_cat
            
            uploaded_imgs = st.file_uploader("Upload Photos (Max 3)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
            
            if st.form_submit_button("Save Product") and new_id and new_name and final_cat:
                image_paths = []
                for img in uploaded_imgs:
                    compressed_bytes, _ = compress_image(img.getvalue())
                    url = upload_image_to_imgbb(compressed_bytes)
                    if url: image_paths.append(url)
                
                db.collection('products').document(str(new_id)).set({
                    "ID": new_id, "Name": new_name, "Category": final_cat, "Image_Path": "|".join(image_paths),
                    "Retail_Qty": new_retail_qty, "Price": new_price, "Unit_Base": new_u_base,
                    "Tier1_Qty": new_t1_qty, "Tier1_Price": new_t1_price, "Unit_T1": new_u_t1,
                    "Tier2_Qty": new_t2_qty, "Tier2_Price": new_t2_price, "Unit_T2": new_u_t2,
                    "Free_Delivery": True if new_free_delivery == "Free Delivery" else False,
                    "In_Stock": new_in_stock, "Seller_Name": st.session_state.seller_logged_in or ""
                })
                load_products.clear()
                st.success("✅ Saved!")
                st.rerun()

    if st.session_state.admin_logged_in:
        with tab_banner:
            st.subheader("🖼️ Top Banner")
            new_banner = st.file_uploader("Choose Banner", type=["jpg", "png", "jpeg"])
            if st.button("Save Banner") and new_banner:
                compressed_bytes, _ = compress_image(new_banner.getvalue())
                b_url = upload_image_to_imgbb(compressed_bytes)
                if b_url:
                    current_config["has_banner"] = True
                    current_config["banner_url"] = b_url
                    save_config(current_config)
                    st.rerun()
        with tab_settings:
            st.subheader("⚙️ Settings")
            new_wa = st.text_input("Admin WhatsApp", value=current_config.get("admin_whatsapp", "919891587437"))
            new_gst = st.text_input("Admin GST", value=current_config.get("admin_gst", "07AKWPB1315K"))
            if st.button("Save Settings"):
                current_config["admin_whatsapp"] = new_wa
                current_config["admin_gst"] = new_gst
                save_config(current_config)
                st.success("Saved!")
        with tab_ledger:
            st.subheader("📒 खाते (Ledgers)")
            ledgers = load_ledger_data()
            if not ledgers: st.warning("कोई खाता नहीं है।")
            for c_name, df in ledgers.items():
                with st.expander(f"👤 {c_name} का खाता"):
                    st.dataframe(df.drop(columns=['doc_id', 'Timestamp'], errors='ignore'))

st.markdown("---")
search_query = st.text_input(t("🔍 Search any product...", "🔍 कोई भी उत्पाद सर्च करें..."), "")

def show_product_card(row, idx, prefix):
    prefix_idx = f"{prefix}_{idx}"
    p_id = str(row.get('ID', prefix_idx)) 
    name = row.get('Name', 'Item')
    
    r_qty = safe_int(row.get('Retail_Qty'), 1)
    r_price = safe_float(row.get('Price'), 0.0)
    u_base = row.get('Unit_Base', 'Pcs')
    
    t1_qty = safe_int(row.get('Tier1_Qty'), 0)
    t1_price = safe_float(row.get('Tier1_Price'), r_price)
    u_t1 = row.get('Unit_T1', u_base)
    
    t2_qty = safe_int(row.get('Tier2_Qty'), 0)
    t2_price = safe_float(row.get('Tier2_Price'), t1_price)
    u_t2 = row.get('Unit_T2', u_base)

    image_path_str = str(row.get("Image_Path", ""))
    paths = [p.strip() for p in image_path_str.split('|') if p.strip()]
    
    img_link_for_wa = ""
    html_code = '<div style="position: relative;">'
    
    if paths:
        img_link_for_wa = paths[0]
        if not img_link_for_wa.startswith("http"): img_link_for_wa = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link_for_wa.replace('\\', '/'), safe='/')}"
        
        wa_text = urllib.parse.quote(f"⚡ *{name}*\n📦 Rates:\n🔹 {r_qty}+ {u_base}: ₹{r_price}\n🛒 Book Order: https://ouraindia.streamlit.app/")
        html_code += f'<div style="position: absolute; top: 10px; right: 10px; z-index: 10; display: flex; gap: 8px;">'
        html_code += f'<a href="{img_link_for_wa}" download target="_blank" style="background: #1877F2; color: white; padding: 6px 12px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: bold;">📥 Photo</a>'
        html_code += f'<a href="https://wa.me/?text={wa_text}" target="_blank" style="background: #25D366; color: white; padding: 6px 12px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: bold;">💬 WA</a></div>'
        
        html_code += '<div class="swipe-gallery">'
        for src in paths:
            if not src.startswith("http"): src = f"{GITHUB_RAW_URL}{urllib.parse.quote(src.replace('\\', '/'), safe='/')}"
            html_code += f'<a href="{src}" target="_blank"><img src="{src}" class="swipe-img"></a>'
        html_code += '</div></div>'
    else: html_code += '</div>'

    with st.container(border=True):
        if paths: st.markdown(html_code, unsafe_allow_html=True)
        st.write(f"**{name}**")
        
        is_in_stock = row.get("In_Stock", True)
        if not is_in_stock:
            st.markdown("<div style='color:red; font-weight:bold; text-align:center;'>🚫 Out of Stock</div>", unsafe_allow_html=True)
        else:
            if t2_qty > 0:
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px;">
                    <div style="flex:1;"><b>{r_qty}+ {u_base}</b><br><span style="color:#2b6cb0; font-weight:bold;">₹{r_price}</span></div>
                    <div style="border-left:1px solid #ccc;"></div>
                    <div style="flex:1;"><b>{t1_qty}+ {u_t1}</b><br><span style="color:#d32f2f; font-weight:bold;">₹{t1_price}</span></div>
                    <div style="border-left:1px solid #ccc;"></div>
                    <div style="flex:1;"><b>{t2_qty}+ {u_t2}</b><br><span style="color:#d32f2f; font-weight:bold;">₹{t2_price}</span></div>
                </div>""", unsafe_allow_html=True)
            elif t1_qty > 0:
                st.markdown(f"""
                <div style="display:flex; justify-content:space-around; text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px;">
                    <div style="flex:1;"><b>{r_qty}+ {u_base}</b><br><span style="color:#2b6cb0; font-weight:bold;">₹{r_price}</span></div>
                    <div style="border-left:1px solid #ccc;"></div>
                    <div style="flex:1;"><b>{t1_qty}+ {u_t1}</b><br><span style="color:#d32f2f; font-weight:bold;">₹{t1_price}</span></div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px;'><b>{r_qty}+ {u_base} रेट:</b> <span style='color:#2b6cb0; font-size:18px; font-weight:bold;'>₹{r_price}</span></div>", unsafe_allow_html=True)
                
            opts = {f"{r_qty} {u_base} (₹{r_price})": {"p": r_price, "u": u_base, "q": r_qty}}
            if t1_qty > 0: opts[f"{t1_qty} {u_t1} (₹{t1_price})"] = {"p": t1_price, "u": u_t1, "q": t1_qty}
            if t2_qty > 0: opts[f"{t2_qty} {u_t2} (₹{t2_price})"] = {"p": t2_price, "u": u_t2, "q": t2_qty}
            
            sel_opt = st.selectbox("क्या खरीदना है?", list(opts.keys()), key=f"sel_{prefix_idx}")
            buy_p, buy_u, min_q = opts[sel_opt]["p"], opts[sel_opt]["u"], opts[sel_opt]["q"]
            
            qty = st.number_input("मात्रा", min_value=min_q, value=min_q, key=f"q_{prefix_idx}")
            if st.button("🛒 Add to Cart", key=f"btn_{prefix_idx}"):
                c_key = f"{p_id}|{buy_u}|{buy_p}"
                if c_key in st.session_state.cart: st.session_state.cart[c_key]["qty"] += qty
                else: st.session_state.cart[c_key] = {"name": name, "price": buy_p, "qty": qty, "unit": buy_u, "img_link": img_link_for_wa}
                save_cart_to_url()
                st.success("कार्ट में जुड़ गया! 🛒")

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
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; }
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"] { width: calc(25% - 8px) !important; }
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(#safe-cat-grid),
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(style) { display: none !important; }
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button { height: 90px !important; width: 100% !important; border-radius: 12px !important; background: #ffffff !important; border: 2px solid #e2e8f0 !important; box-shadow: 0 4px 8px rgba(0,0,0,0.08) !important; color: #1a202c !important; font-weight: 700 !important; font-size: 13px !important; white-space: normal !important; padding: 4px !important; }
            div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button:hover { border-color: #2b6cb0 !important; color: #2b6cb0 !important;}
            </style>
            """, unsafe_allow_html=True)
            for idx, cat in enumerate(valid_categories):
                if st.button(cat, key=f"cat_btn_{idx}"):
                    st.session_state.selected_category = cat
                    st.query_params["cat"] = cat
                    save_cart_to_url()
                    st.rerun()
    else:
        st.subheader(f"📂 {st.session_state.selected_category}")
        if st.button("🏠 वापस सारे बॉक्स पर जाएं", key="float_back_btn"):
            st.session_state.selected_category = None
            if "cat" in st.query_params: del st.query_params["cat"]
            save_cart_to_url()
            st.rerun()
        st_components.html("""<script>const btns = window.parent.document.querySelectorAll('button'); btns.forEach(b => { if(b.innerText.includes('वापस सारे बॉक्स')) { b.style.position='fixed'; b.style.bottom='120px'; b.style.left='15px'; b.style.zIndex='999999'; b.style.background='#2b6cb0'; b.style.color='white'; b.style.padding='12px 18px'; b.style.borderRadius='50px'; } });</script>""", height=0)
            
        cat_products = products_df[products_df['Category'] == st.session_state.selected_category]
        if cat_products.empty: st.warning("इस बॉक्स में अभी कोई उत्पाद नहीं है।")
        else:
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "cat_view")

# --- कार्ट और बिलिंग ---
st.markdown("<br><br><br><br>", unsafe_allow_html=True) 
st.markdown("---")
st.header("🛒 आपकी बास्केट")
if st.session_state.cart:
    total = 0
    for k, item in list(st.session_state.cart.items()):
        sub = item['price'] * item['qty']
        total += sub
        c1, c2 = st.columns([8, 2])
        c1.write(f"✔️ **{item['name']}** - {item['qty']} {item.get('unit','Pcs')} x ₹{item['price']} = **₹{sub}**")
        if c2.button("❌", key=f"del_{k}"):
            del st.session_state.cart[k]
            save_cart_to_url()
            st.rerun()
    st.subheader(f"कुल माल: ₹{total:.2f}")
    
    with st.form("billing_form"):
        c1, c2 = st.columns(2)
        with c1:
            cust_name = st.text_input("Customer Name")
            cust_mobile = st.text_input("Mobile")
            cust_address = st.text_area("Address")
        with c2:
            gst_choice = st.selectbox("GST Type", ["Estimate", "5%", "12%", "18%", "28%"])
            gst_rate = 5 if "5" in gst_choice else (12 if "12" in gst_choice else (18 if "18" in gst_choice else (28 if "28" in gst_choice else 0)))
            cust_gst = st.text_input("Customer GST")
            shipping = st.number_input("Shipping (₹)", min_value=0.0)
            paid = st.number_input("Advance Paid (₹)", min_value=0.0)
        submit_bill = st.form_submit_button("✅ बिल तैयार करें")

    if submit_bill:
        last_bal = 0.0
        safe_name = cust_name.strip().upper() if cust_name else ""
        if safe_name:
            try:
                docs = db.collection('ledgers').document(safe_name).collection('transactions').stream()
                t_b, t_a = 0, 0
                for d in docs:
                    data = d.to_dict()
                    if data.get("Type")=="Bill": t_b += data.get("Amount",0)
                    elif data.get("Type")=="Advance": t_a += data.get("Amount",0)
                last_bal = t_b - t_a
            except: pass
            
        pdf_bytes = generate_pdf_bill(st.session_state.cart, cust_name, cust_mobile, cust_address, cust_gst, gst_rate, shipping, last_bal, paid, current_config, datetime.date.today())
        st.session_state.ready_pdf = pdf_bytes
        
        # बिल बनने पर कार्ट खाली करना
        st.session_state.cart = {}
        save_cart_to_url()
        st.success("✅ बिल तैयार है! कार्ट खाली कर दिया गया है।")
        
    if 'ready_pdf' in st.session_state:
        st.download_button("📄 Download PDF Bill (With Photos)", data=st.session_state.ready_pdf, file_name="Bill.pdf", mime="application/pdf")
        
    if st.session_state.cart:
        if st.button("🗑️ बास्केट खाली करें"):
            st.session_state.cart = {}
            save_cart_to_url()
            st.rerun()

# --- AI हेल्प डेस्क (Chatbot) ---
admin_wa = current_config.get("admin_whatsapp", "919891587437")
ai_js = """
<script>
const parentDoc = window.parent.document;
if (!parentDoc.getElementById('oura-ai-widget')) {
    const widgetDiv = parentDoc.createElement('div');
    widgetDiv.id = 'oura-ai-widget';
    widgetDiv.innerHTML = `
    <style>
    @keyframes floatDoll { 0% { transform: translateY(0px); } 50% { transform: translateY(-15px); } 100% { transform: translateY(0px); } }
    #oura-ai-btn { position: fixed; bottom: 90px; right: 15px; z-index: 9999999; cursor: pointer; animation: floatDoll 3s ease-in-out infinite; }
    #oura-ai-btn img { width: 70px; height: 70px; border-radius: 50%; border: 3px solid #2b6cb0; background: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    #ai-chat-box { position: fixed; bottom: 170px; right: 15px; z-index: 9999999; width: 320px; height: 400px; background: #ffffff; border-radius: 15px; box-shadow: 0 15px 30px rgba(0,0,0,0.2); display: none; flex-direction: column; border: 2px solid #e2e8f0; }
    .ai-header { background: linear-gradient(135deg, #2b6cb0 0%, #4299e1 100%); color: white; padding: 12px 15px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
    .ai-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
    .msg-ai { background: #f1f3f5; padding: 10px 15px; border-radius: 0 15px 15px 15px; align-self: flex-start; max-width: 85%; font-size: 13px; color: #333; }
    .msg-user { background: #2b6cb0; color: white; padding: 10px 15px; border-radius: 15px 0 15px 15px; align-self: flex-end; max-width: 85%; font-size: 13px; }
    .ai-input-area { display: flex; border-top: 1px solid #eee; padding: 10px; background: white; }
    .ai-input-area input { flex: 1; padding: 10px 12px; border: 1px solid #ccc; border-radius: 20px; outline: none; }
    .ai-input-area button { background: #25D366; color: white; border: none; padding: 10px 16px; margin-left: 8px; border-radius: 20px; cursor: pointer; font-weight: bold; }
    </style>
    <div id="ai-chat-box">
        <div class="ai-header"><span>👩‍💻 9 Class Helpline</span><span id="close-ai-btn" style="cursor:pointer; font-size:20px;">×</span></div>
        <div class="ai-messages" id="ai-msgs"><div class="msg-ai">नमस्ते! 🙏 मैं असिस्टेंट हूँ। बताइए, मैं आपकी क्या मदद कर सकती हूँ?</div></div>
        <div class="ai-input-area"><input type="text" id="ai-input" placeholder="मैसेज लिखें..."/><button id="ai-send-btn">Send</button></div>
    </div>
    <div id="oura-ai-btn"><img src="https://img.icons8.com/color/256/customer-support.png" alt="AI"/></div>
    `;
    parentDoc.body.appendChild(widgetDiv);
    
    let msgCount = 0; const adminWA = "__ADMIN_WA__";
    function handleSend() {
        let input = parentDoc.getElementById('ai-input'); let text = input.value.trim(); if(!text) return;
        let msgs = parentDoc.getElementById('ai-msgs'); msgs.innerHTML += `<div class="msg-user">${text}</div>`;
        input.value = ''; msgs.scrollTop = msgs.scrollHeight; msgCount++;
        setTimeout(() => {
            let reply = "मैं अभी नई हूँ! 👩‍💻 सीधे मालिक से बात करने के लिए बस 'Call' या 'Admin' लिखें।";
            let t = text.toLowerCase();
            if(msgCount >= 4 || t.includes("call") || t.includes("admin") || t.includes("whatsapp")) reply = `📲 <a href="https://wa.me/${adminWA}?text=Hello" target="_blank" style="color:#25D366; font-weight:bold; text-decoration:none;">यहाँ क्लिक करके WhatsApp करें</a><br><br>📞 या कॉल करें: <b>+91-${adminWA}</b>`;
            msgs.innerHTML += `<div class="msg-ai">${reply}</div>`; msgs.scrollTop = msgs.scrollHeight;
        }, 800);
    }
    parentDoc.getElementById('ai-send-btn').addEventListener('click', handleSend);
    parentDoc.getElementById('ai-input').addEventListener('keypress', e => { if(e.key === 'Enter') handleSend(); });
    parentDoc.getElementById('close-ai-btn').addEventListener('click', () => parentDoc.getElementById('ai-chat-box').style.display = 'none');
    parentDoc.getElementById('oura-ai-btn').addEventListener('click', () => { let box = parentDoc.getElementById('ai-chat-box'); box.style.display = box.style.display === 'flex' ? 'none' : 'flex'; });
}
</script>
""".replace("__ADMIN_WA__", str(admin_wa))
st_components.html(ai_js, height=0)
