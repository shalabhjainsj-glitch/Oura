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

try:
    import pytesseract
except ImportError:
    pass

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
        if not imgbb_key:
            st.error("🚨 ImgBB की चाबी तिजोरी (Secrets) में नहीं मिली!")
            return None
            
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": imgbb_key,
            "image": base64.b64encode(file_bytes).decode('utf-8')
        }
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            return res.json()["data"]["url"]
        else:
            st.error("फोटो अपलोड फेल हो गई।")
            return None
    except Exception as e:
        st.error(f"एरर: {e}")
        return None

def compress_image(image_bytes):
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        max_width = 800
        if pil_img.width > max_width:
            ratio = max_width / float(pil_img.width)
            new_height = int((float(pil_img.height) * float(ratio)))
            pil_img = pil_img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        compressed_io = io.BytesIO()
        pil_img.save(compressed_io, format='JPEG', quality=75)
        return compressed_io.getvalue(), pil_img
    except Exception as e:
        return image_bytes, None

def load_config():
    try:
        doc = db.collection('settings').document('config').get()
        if doc.exists:
            return doc.to_dict()
    except: pass
    return {
        "admin_whatsapp": "919891587437", 
        "admin_gst": "07AKWPB1315K", 
        "phonepe_upi": "", "paytm_upi": "", "gpay_upi": "", "bhim_upi": "", "upi_id": "",
        "has_banner": False, "has_logo": False, "free_delivery_tag": True, "sellers": {}
    }

def save_config(config):
    db.collection('settings').document('config').set(config)

current_config = load_config()

if "sellers" not in current_config:
    current_config["sellers"] = {}
else:
    migrated = False
    for k, v in current_config["sellers"].items():
        if isinstance(v, str):
            current_config["sellers"][k] = {"name": v, "phone": ""}
            migrated = True
    if migrated:
        save_config(current_config)

def generate_pdf_bill(cart, cust_name, cust_mobile, cust_address, cust_gst, gst_rate, shipping_charge, last_balance, amount_paid, config, invoice_date):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(43, 108, 176)
    pdf.cell(0, 10, "OURA PRODUCTS", ln=True, align='C') 
    
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(100, 100, 100)
    admin_phone = config.get("admin_whatsapp", "9891587437")
    admin_gst_number = config.get("admin_gst", "07AKWPB1315K").strip().upper()
    
    pdf.cell(0, 6, f"Delhi, India | Ph: +91 {admin_phone}", ln=True, align='C')
    
    if gst_rate > 0 and admin_gst_number:
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, f"GSTIN: {admin_gst_number}", ln=True, align='C')
        
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
        if cust_gst and cust_gst.strip():
            pdf.cell(100, 6, f"GSTIN: {cust_gst.strip().upper()}", ln=True)
        else:
            pdf.cell(100, 6, "GSTIN: Unregistered Consumer", ln=True)
        
    pdf.ln(10)
    
    pdf.set_fill_color(230, 240, 255) 
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(15, 10, "S.No", border=1, align='C', fill=True)
    pdf.cell(90, 10, "Item Description", border=1, align='L', fill=True)
    pdf.cell(25, 10, "Qty", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Rate (Rs)", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Amount", border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    subtotal = 0
    idx = 1
    
    for k, item in cart.items():
        amt = item['price'] * item['qty']
        subtotal += amt
        clean_name = re.sub(r'[^\x00-\x7F]+', ' ', str(item['name'])) 
        if len(clean_name) > 40: clean_name = clean_name[:37] + "..."
        
        pdf.cell(15, 10, str(idx), border=1, align='C')
        pdf.cell(90, 10, clean_name, border=1, align='L')
        pdf.cell(25, 10, f"{item['qty']} Pcs", border=1, align='C')
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
        admin_state = admin_gst_number[:2] if len(admin_gst_number) >= 2 else "07" 
        cust_state = cust_gst[:2] if cust_gst and len(cust_gst) >= 2 else admin_state
        
        if admin_state != cust_state:
            gst_amt = (taxable_amount * gst_rate) / 100
            pdf.cell(160, 10, f"Add: IGST @ {gst_rate}%", border=1, align='R')
            pdf.cell(30, 10, f"{gst_amt:.2f}", border=1, align='R')
            pdf.ln()
        else:
            half_rate = gst_rate / 2
            cgst_amt = (taxable_amount * half_rate) / 100
            sgst_amt = cgst_amt
            gst_amt = cgst_amt + sgst_amt
            
            pdf.cell(160, 10, f"Add: CGST @ {half_rate}%", border=1, align='R')
            pdf.cell(30, 10, f"{cgst_amt:.2f}", border=1, align='R')
            pdf.ln()
            pdf.cell(160, 10, f"Add: SGST @ {half_rate}%", border=1, align='R')
            pdf.cell(30, 10, f"{sgst_amt:.2f}", border=1, align='R')
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
        pdf.cell(160, 10, "Less: Amount Paid Now (Advance/Cash)", border=1, align='R')
        pdf.cell(30, 10, f"{amount_paid:.2f}", border=1, align='R')
        pdf.ln()
        
        balance_due = grand_total - amount_paid
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(255, 200, 200) 
        pdf.cell(160, 12, "NET BALANCE DUE (Rs)", border=1, align='R', fill=True)
        pdf.cell(30, 12, f"{balance_due:.2f}", border=1, align='R', fill=True)
        pdf.ln()
    else:
        pdf.ln(5)

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 5, "Terms & Conditions:", ln=True)
    pdf.cell(0, 5, "1. Goods once sold will not be taken back without valid manufacturing defect.", ln=True)
    pdf.cell(0, 5, "2. We are not responsible for any transit/courier damages.", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 5, "For OURA PRODUCTS", ln=True, align='R') 
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "(Authorized Signatory)", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin1')

app_icon_url = current_config.get("logo_url", "🛍️") if current_config.get("has_logo") else "🛍️"

st.set_page_config(page_title="Oura Products - Wholesale", page_icon=app_icon_url, layout="wide")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            div[data-testid="stDecoration"] {visibility: hidden; height: 0%; display: none;}
            
            .stApp { background-color: #f4f6f9; }

            div.stButton > button {
                background-color: #2b6cb0;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
                transition: background-color 0.2s;
                padding: 10px !important;
                min-height: 50px;
            }
            div.stButton > button:hover { background-color: #2c5282; }
            div.stButton > button:active { transform: scale(0.98); }

            div[data-testid="stContainer"] {
                background-color: #ffffff;
                border-radius: 10px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                padding: 15px;
                transition: box-shadow 0.2s;
            }
            div[data-testid="stContainer"]:hover {
                box-shadow: 0 6px 12px rgba(0,0,0,0.08);
                border-color: #cbd5e0 !important;
            }

            div[data-testid="stExpander"] {
                background-color: #ffffff;
                border-radius: 8px;
                border-left: 4px solid #2b6cb0 !important;
                border-top: 1px solid #e2e8f0;
                border-right: 1px solid #e2e8f0;
                border-bottom: 1px solid #e2e8f0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }

            .swipe-gallery {
                display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding-bottom: 5px;
                -webkit-overflow-scrolling: touch; scrollbar-width: none;
            }
            .swipe-gallery::-webkit-scrollbar { display: none; }
            .swipe-gallery a { scroll-snap-align: center; flex: 0 0 100%; max-width: 100%; text-decoration: none; }
            .swipe-img { width: 100%; height: 300px; object-fit: contain; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; transition: all 0.3s ease;}

            #oura-wa-btn {
                position: fixed; bottom: 120px; right: 15px; background-color: #25D366; color: white !important;
                padding: 12px 18px; border-radius: 50px; font-size: 16px; font-weight: bold; text-decoration: none !important;
                z-index: 9999999; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 10px rgba(37, 211, 102, 0.4);
                cursor: grab; border: 2px solid white; user-select: none; touch-action: none;
            }
            #oura-wa-btn:active { cursor: grabbing; }
            
            .multi-upi-btn { transition: transform 0.1s; }
            .multi-upi-btn:active { transform: scale(0.96); }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if current_config.get("has_logo", False) and app_icon_url != "🛍️":
    pwa_js = f"""
    <script>
    const parentHead = window.parent.document.head;
    let appleIcon = parentHead.querySelector('link[rel="apple-touch-icon"]');
    if (!appleIcon) {{
        appleIcon = window.parent.document.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        parentHead.appendChild(appleIcon);
    }}
    appleIcon.href = '{app_icon_url}';
    let mobIcon = parentHead.querySelector('link[rel="icon"][sizes="192x192"]');
    if (!mobIcon) {{
        mobIcon = window.parent.document.createElement('link');
        mobIcon.rel = 'icon';
        mobIcon.sizes = '192x192';
        parentHead.appendChild(mobIcon);
    }}
    mobIcon.href = '{app_icon_url}';
    </script>
    """
    st_components.html(pwa_js, height=0, width=0)

if 'lang' not in st.session_state:
    st.session_state.lang = 'hi'

def t(en_text, hi_text):
    return en_text if st.session_state.lang == 'en' else hi_text

expected_columns = ["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_Path", "Free_Delivery", "Seller_Name", "In_Stock"]

@st.cache_data(ttl=3600, show_spinner=False)
def load_products():
    try:
        docs = db.collection('products').stream()
        data = [doc.to_dict() for doc in docs]
        if data:
            return pd.DataFrame(data)
    except: pass
    return pd.DataFrame(columns=expected_columns)

# 🚀 फिक्स: Cache हटा दिया है ताकि नई एंट्री तुरंत रिफ्रेश होकर दिखे
def load_ledger_data():
    ledger_data = {}
    try:
        customers = db.collection('ledgers').stream()
        for cust in customers:
            cust_name = cust.id
            if cust_name == "config": continue
            transactions = []
            docs = db.collection('ledgers').document(cust_name).collection('transactions').order_by("Date").stream()
            for doc in docs:
                t_data = doc.to_dict()
                t_data['doc_id'] = doc.id 
                transactions.append(t_data)
            if transactions:
                ledger_data[cust_name] = pd.DataFrame(transactions)
    except Exception as e:
        pass
    return ledger_data

def toggle_stock_callback(doc_id, key):
    if key in st.session_state:
        db.collection('products').document(doc_id).update({"In_Stock": st.session_state[key]})
        load_products.clear()

def toggle_fd_callback(doc_id, key):
    if key in st.session_state:
        db.collection('products').document(doc_id).update({"Free_Delivery": st.session_state[key]})
        load_products.clear()

products_df = load_products()

def save_cart_to_url():
    if st.session_state.cart:
        cart_str = "_".join([f"{k}-{v['qty']}" for k, v in st.session_state.cart.items()])
        st.query_params["cart"] = cart_str
    else:
        if "cart" in st.query_params:
            del st.query_params["cart"]

if 'cart_loaded' not in st.session_state:
    st.session_state.cart = {}
    if "cart" in st.query_params and not products_df.empty:
        cart_str = st.query_params["cart"]
        items = cart_str.split("_")
        for item in items:
            if "-" in item:
                try:
                    p_id, qty_str = item.split("-", 1)
                    qty = int(qty_str)
                    match = products_df[products_df['ID'].astype(str) == p_id]
                    if not match.empty:
                        row = match.iloc[0]
                        w_qty = int(float(row.get('Wholesale_Qty', 1)))
                        retail_price = row.get('Price', 0)
                        w_price = float(row.get('Wholesale_Price', retail_price))
                        final_price = w_price if qty >= w_qty else retail_price
                        
                        image_path_str = str(row.get("Image_Path", ""))
                        paths = [p.strip() for p in image_path_str.split('|') if p.strip()]
                        img_link = paths[0] if paths else ""
                        if img_link and not img_link.startswith("http"):
                            img_link = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link.replace('\\', '/'), safe='/')}"
                            
                        st.session_state.cart[p_id] = {
                            "name": row.get('Name', 'Item'),
                            "price": final_price,
                            "qty": qty,
                            "img_link": img_link,
                            "seller": str(row.get("Seller_Name", "")).strip()
                        }
                except Exception as e:
                    pass
    st.session_state.cart_loaded = True

if "cat" in st.query_params:
    st.session_state.selected_category = st.query_params["cat"]
else:
    st.session_state.selected_category = None

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'seller_logged_in' not in st.session_state: st.session_state.seller_logged_in = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'share_msg' not in st.session_state: st.session_state.share_msg = None
if 'share_img_path' not in st.session_state: st.session_state.share_img_path = None

if st.session_state.seller_logged_in:
    seller_name = st.session_state.seller_logged_in
    valid_sellers = [v["name"] if isinstance(v, dict) else v for v in current_config.get("sellers", {}).values()]
    if seller_name not in valid_sellers:
        st.session_state.seller_logged_in = None
        st.error(t("⚠️ Your seller account has been closed by Admin!", "⚠️ आपका सेलर अकाउंट एडमिन द्वारा बंद कर दिया गया है!"))
        time.sleep(2)
        st.rerun()

col_logo, col_lang, col_login = st.columns([6, 2, 2])
with col_logo:
    if current_config.get("has_banner", False) and current_config.get("banner_url"):
        try: st.image(current_config["banner_url"], use_container_width=True)
        except: st.title("🛍️ Oura Products - Wholesale")
    else:
        st.title("🛍️ Oura Products - Wholesale")

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

hi_marquee = "🏭 क्या आप भी एक मैन्युफैक्चरर या होलसेलर हैं? आइए, Oura के साथ मिलकर अपने बिज़नेस को नई ऊंचाइयों पर ले जाएं! 🚀"
en_marquee = "🏭 Are you a manufacturer or wholesaler? Let's take your business to new heights with Oura! 🚀"
multi_color_marquee = f"""
<div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; margin-bottom: 20px; margin-top: 10px; border: 1px solid #bbdefb;">
    <marquee behavior="scroll" direction="left" scrollamount="6" style="color: #0d47a1; font-size: 16px; font-weight: bold; font-family: sans-serif;">
        {t(en_marquee, hi_marquee)}
    </marquee>
</div>
"""
st.markdown(multi_color_marquee, unsafe_allow_html=True)

if st.session_state.show_login and not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    with st.container(border=True):
        st.subheader(t("Store Login", "दुकान में लॉगिन करें"))
        login_type = st.radio(t("Select Login Type:", "लॉगिन का प्रकार चुनें:"), [t("Seller", "सेलर (Seller)"), t("Admin", "मालिक / एडमिन (Admin)")], horizontal=True)
        
        if login_type == t("Admin", "मालिक / एडमिन (Admin)"):
            password = st.text_input(t("Enter Admin Password", "एडमिन पासवर्ड डालें"), type="password")
            if st.button(t("Login", "लॉगिन करें")):
                try: correct_password = st.secrets["ADMIN_PASSWORD"]
                except: correct_password = None
                    
                if correct_password and password == correct_password:
                    st.session_state.admin_logged_in = True
                    st.session_state.seller_logged_in = None
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error(t("❌ Incorrect Password!", "❌ गलत पासवर्ड!"))
        else:
            seller_token = st.text_input(t("Enter Seller Token", "अपना सेलर टोकन (Token) डालें"), type="password")
            if st.button(t("Login", "लॉगिन करें")):
                sellers_dict = current_config.get("sellers", {})
                if seller_token in sellers_dict:
                    s_data = sellers_dict[seller_token]
                    st.session_state.seller_logged_in = s_data["name"] if isinstance(s_data, dict) else s_data
                    st.session_state.admin_logged_in = False
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error(t("❌ Invalid Token! Contact Admin.", "❌ गलत टोकन! कृपया एडमिन से संपर्क करें।"))
            
            st.markdown("---")
            st.markdown(f"**{t('Dont have a Seller Token?', 'क्या आपके पास सेलर टोकन नहीं है?')}**")
            admin_wa = current_config.get("admin_whatsapp", "919891587437")
            req_msg = t("Hello Admin, I want to become a seller on Oura Products. Please provide me a Seller Token.\n\nMy Brand Name is: \nMy Contact Number is: ", "नमस्ते एडमिन, मैं Oura Products पर एक सेलर बनना चाहता हूँ। कृपया मुझे एक सेलर टोकन (Password) प्रदान करें।\n\nमेरे ब्रांड का नाम है: \nमेरा संपर्क नंबर है: ")
            encoded_req = urllib.parse.quote(req_msg)
            wa_req_link = f"https://wa.me/{admin_wa}?text={encoded_req}"
            
            st.markdown(f'''<a href="{wa_req_link}" target="_blank" style="display:block; text-align:center; background-color:#25D366; color:white; padding:10px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:14px; margin-top:5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">📲 {t("Request Token via WhatsApp", "WhatsApp से टोकन मांगें")}</a>''', unsafe_allow_html=True)

    st.markdown("---")

if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success(t("✅ Logged in as Admin. You have full control.", "✅ आप एडमिन (मालिक) के रूप में लॉगिन हैं। आपके पास पूरे ऐप का कंट्रोल है।"))
        tab_add, tab_banner, tab_settings, tab_ledger = st.tabs([
            t("➕ Add Product", "➕ नया उत्पाद"), 
            t("🖼️ Banner & Logo", "🖼️ बैनर व लोगो"), 
            t("⚙️ Settings", "⚙️ सेटिंग्स"),
            t("📒 Ledger / Invoices", "📒 खाता और बिल (Ledger)")
        ])
    else:
        st.success(t(f"🏪 Welcome: {st.session_state.seller_logged_in} (Seller)", f"🏪 स्वागत है: {st.session_state.seller_logged_in} (Seller)"))
        tab_add, = st.tabs([t("➕ Add Product", "➕ नया उत्पाद")])
    
    with tab_add:
        if st.session_state.share_msg:
            st.success(t("✅ Great! Your new product is live on Oura.", "✅ शानदार! आपका नया उत्पाद Oura पर लाइव है।"))
            if st.session_state.share_img_path:
                st.image(st.session_state.share_img_path, width=200)
            encoded_share = urllib.parse.quote(st.session_state.share_msg)
            wa_share_link = f"https://wa.me/?text={encoded_share}"
            st.markdown(f'''<a href="{wa_share_link}" target="_blank" style="display:inline-block; background-color:#25D366; color:white; padding:12px 25px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:16px; margin-bottom:15px;">📢 {t("Share on WhatsApp", "WhatsApp पर शेयर करें")}</a>''', unsafe_allow_html=True)
            if st.button(t("➕ Add Another Product", "➕ एक और नया उत्पाद जोड़ें")):
                st.session_state.share_msg = None
                st.session_state.share_img_path = None
                st.rerun()
        else:
            with st.form("add_product", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    new_id = st.text_input(t("ID (Keep Unique)", "ID (यूनिक रखें)"))
                    new_name = st.text_input(t("Product Name", "नाम"))
                    new_price = st.number_input(t("Single Piece Rate", "सिंगल पीस रेट"), min_value=0.0, value=0.0, step=0.50, format="%.2f")
                with col_b:
                    new_w_qty = st.number_input(t("Min Wholesale Qty", "होलसेल कम से कम पीस"), min_value=1, value=10)
                    new_w_price = st.number_input(t("Wholesale Rate (Per Piece)", "होलसेल / बॉक्स रेट (प्रति पीस)"), min_value=0.0, value=0.0, step=0.50, format="%.2f")
                    new_free_delivery = st.selectbox(t("Single Piece Delivery", "सिंगल पीस डिलीवरी"), [t("Free Delivery", "फ्री डिलीवरी"), t("Extra Courier Charge", "कोरियर चार्ज एक्स्ट्रा")])
                
                new_in_stock = st.checkbox(t("✅ Product is currently in stock?", "✅ उत्पाद अभी स्टॉक में उपलब्ध है?"), value=True)
                
                if st.session_state.seller_logged_in:
                    st.info(f"🏪 {t('Your Brand/Seller Name', 'आपका ब्रांड/सेलर नाम')}: **{st.session_state.seller_logged_in}**")
                    new_seller_name = st.session_state.seller_logged_in
                else:
                    new_seller_name = st.text_input(t("Seller/Brand Name (Leave blank to hide)", "सेलर / ब्रांड का नाम (अगर खाली छोड़ेंगे तो कुछ नहीं दिखेगा)"))
                
                existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
                cat_options = [t("Create New Category...", "नयी केटेगरी बनाएं...")] + existing_cats
                selected_cat = st.selectbox(t("Select Category", "केटेगरी चुनें"), cat_options)
                if selected_cat == t("Create New Category...", "नयी केटेगरी बनाएं..."):
                    final_cat = st.text_input(t("Enter New Category Name (Emojis allowed 👕👟)", "नई केटेगरी का नाम लिखें (इमोजी 👕👟 भी लगा सकते हैं)"))
                else:
                    final_cat = selected_cat
                
                uploaded_imgs = st.file_uploader(t("Upload Photos (Max 3)", "फोटो अपलोड करें (अधिकतम 3)"), type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="add_imgs")
                submit_btn = st.form_submit_button(t("Save Product", "उत्पाद सेव करें"))
                if submit_btn and new_id and new_name and uploaded_imgs and final_cat:
                    if len(uploaded_imgs) > 3: st.error(t("⚠️ Please select max 3 photos.", "⚠️ कृपया अधिकतम 3 फोटो ही चुनें।"))
                    else:
                        with st.spinner("Saving..."):
                            image_paths = []
                            for img in uploaded_imgs:
                                compressed_bytes, pil_img = compress_image(img.getvalue())
                                img_url = upload_image_to_imgbb(compressed_bytes)
                                if img_url: image_paths.append(img_url)
                            
                            final_path_str = "|".join(image_paths)
                            is_free = True if new_free_delivery in ["फ्री डिलीवरी", "Free Delivery"] else False
                            seller_val = new_seller_name.strip() if new_seller_name else ""
                            data = {
                                "ID": new_id, "Name": new_name, "Price": new_price, "Wholesale_Price": new_w_price,
                                "Wholesale_Qty": new_w_qty, "Category": final_cat, "Image_Path": final_path_str,
                                "Free_Delivery": is_free, "Seller_Name": seller_val, "In_Stock": new_in_stock
                            }
                            db.collection('products').document(str(new_id)).set(data)
                            load_products.clear()
                            st.session_state.share_msg = f"⚡ *Market's hottest item on Oura!* ⚡\n\n🎁 *Product:* {new_name}\n\n👇 *Check rates & book now:*\nhttps://ouraindia.streamlit.app/"
                            st.session_state.share_img_path = image_paths[0] if image_paths else None
                            st.rerun()

    if st.session_state.admin_logged_in:
        with tab_banner:
            st.subheader("🖼️ Top Banner")
            new_banner = st.file_uploader("Choose Banner", type=["jpg", "png", "jpeg"], key="banner_upload")
            if st.button("Save Banner") and new_banner:
                compressed_bytes, _ = compress_image(new_banner.getvalue())
                b_url = upload_image_to_imgbb(compressed_bytes)
                if b_url:
                    current_config["has_banner"] = True
                    current_config["banner_url"] = b_url
                    save_config(current_config)
                    st.rerun()
            if current_config.get("has_banner", False):
                if st.button("❌ Remove Banner"):
                    current_config["has_banner"] = False
                    current_config["banner_url"] = ""
                    save_config(current_config)
                    st.rerun()
            st.markdown("---")
            st.subheader("📱 App Logo")
            new_logo = st.file_uploader("Choose Logo", type=["jpg", "png", "jpeg"], key="logo_upload")
            if st.button("Save Logo") and new_logo:
                compressed_bytes, _ = compress_image(new_logo.getvalue())
                l_url = upload_image_to_imgbb(compressed_bytes)
                if l_url:
                    current_config["has_logo"] = True
                    current_config["logo_url"] = l_url
                    save_config(current_config)
                    st.rerun()
            if current_config.get("has_logo", False):
                if st.button("❌ Remove Logo"):
                    current_config["has_logo"] = False
                    current_config["logo_url"] = ""
                    save_config(current_config)
                    st.rerun()
        
        with tab_settings:
            st.subheader("👥 Seller Management (सेलर मैनेजमेंट)")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                new_s_name = st.text_input("New Seller Brand Name (सेलर का नाम)")
            with col_s2:
                new_s_phone = st.text_input("Seller WhatsApp (सेलर का नंबर)")
            with col_s3:
                new_s_token = st.text_input("Create Password/Token")
                
            if st.button("➕ Add Seller (नया सेलर जोड़ें)"):
                if new_s_name and new_s_token:
                    current_config["sellers"][new_s_token] = {"name": new_s_name, "phone": new_s_phone}
                    save_config(current_config)
                    st.success(f"✅ Added Seller: {new_s_name}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ Please fill Brand Name and Token.")
            
            if current_config.get("sellers"):
                st.markdown("**Current Active Sellers (मौजूदा सेलर्स):**")
                for token, s_data in list(current_config["sellers"].items()):
                    s_name = s_data["name"] if isinstance(s_data, dict) else s_data
                    s_phone = s_data.get("phone", "N/A") if isinstance(s_data, dict) else "N/A"
                    
                    col_sa, col_sb = st.columns([8, 2])
                    with col_sa: 
                        st.info(f"🏪 **{s_name}** | 📞 {s_phone} (Token: `{token}`)")
                    with col_sb:
                        if st.button("❌ Block / Delete", key=f"del_sel_{token}"):
                            del current_config["sellers"][token]
                            save_config(current_config)
                            st.success(f"🚫 {s_name} का अकाउंट बंद कर दिया गया है!")
                            time.sleep(1)
                            st.rerun()

            st.markdown("---")
            st.subheader("📱 Business Settings")
            new_wa = st.text_input("Admin WhatsApp Number", value=current_config.get("admin_whatsapp", "919891587437"))
            new_admin_gst = st.text_input("Admin GST Number", value=current_config.get("admin_gst", "07AKWPB1315K"))
            show_free_delivery = st.checkbox("✅ Show 'Free Delivery' tag by default?", value=current_config.get("free_delivery_tag", True))
            
            st.markdown("---")
            st.subheader("💳 UPI Settings")
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                new_phonepe = st.text_input("PhonePe UPI ID", value=current_config.get("phonepe_upi", ""))
                new_paytm = st.text_input("Paytm UPI ID", value=current_config.get("paytm_upi", ""))
            with col_u2:
                new_gpay = st.text_input("GPay UPI ID", value=current_config.get("gpay_upi", ""))
                new_bhim = st.text_input("BHIM UPI ID", value=current_config.get("bhim_upi", ""))
            if st.button("⚙️ Save All Settings"):
                current_config["admin_whatsapp"] = new_wa
                current_config["admin_gst"] = new_admin_gst
                current_config["free_delivery_tag"] = show_free_delivery
                current_config["phonepe_upi"] = new_phonepe
                current_config["paytm_upi"] = new_paytm
                current_config["gpay_upi"] = new_gpay
                current_config["bhim_upi"] = new_bhim
                save_config(current_config)
                st.success("✅ Saved!")
                time.sleep(1)
                st.rerun()

            st.markdown("---")
            st.subheader("🏷️ Category Management (नाम और इमोजी बदलें)")
            st.info("💡 टिप: Windows पर इमोजी के लिए (Win + .) दबाएं। यहाँ से नाम बदलने पर उस केटेगरी के सभी प्रोडक्ट्स अपने आप अपडेट हो जाएंगे।")
            
            current_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
            
            if current_cats:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    old_cat = st.selectbox("पुरानी केटेगरी चुनें", current_cats)
                with col_c2:
                    new_cat_name = st.text_input("नया नाम और इमोजी डालें (जैसे: 🔊 Speakers)", value=old_cat)
                
                if st.button("💾 नाम अपडेट करें (Update Name)"):
                    if new_cat_name and new_cat_name.strip() != old_cat:
                        with st.spinner("क्लाउड पर अपडेट हो रहा है..."):
                            prods_to_update = products_df[products_df['Category'] == old_cat]
                            batch = db.batch()
                            
                            for idx, row in prods_to_update.iterrows():
                                doc_id = str(row['ID'])
                                doc_ref = db.collection('products').document(doc_id)
                                batch.update(doc_ref, {"Category": new_cat_name.strip()})
                            
                            batch.commit()
                            load_products.clear()
                            st.success(f"✅ केटेगरी का नाम बदलकर '{new_cat_name}' कर दिया गया है!")
                            time.sleep(1)
                            st.rerun()
                            
            st.markdown("---")
            # 🚀 फिक्स: इंटरनेट के लिए नया फाइल अपलोडर सिस्टम
            st.subheader("🔄 पुराने खातों को क्लाउड पर लाएं (Upload Old Ledgers)")
            st.warning("चूंकि ऐप अब इंटरनेट (Cloud) पर है, इसलिए आपको अपने डिवाइस से अपनी पुरानी .csv फाइलें यहाँ अपलोड करनी होंगी।")
            
            uploaded_csvs = st.file_uploader("अपनी पुरानी CSV फाइलें चुनें (Select old _ledger.csv files)", type=["csv"], accept_multiple_files=True)
            
            if st.button("🚀 फाइलें क्लाउड पर सेव करें"):
                if uploaded_csvs:
                    with st.spinner("खाते क्लाउड पर शिफ्ट हो रहे हैं... कृपया रुकें..."):
                        for file in uploaded_csvs:
                            cust_name = file.name.replace("_ledger.csv", "").replace(".csv", "")
                            try:
                                df = pd.read_csv(file)
                                # पैरेंट डॉक्यूमेंट बनाएं
                                db.collection('ledgers').document(cust_name).set({"active": True}, merge=True)
                                for _, row in df.iterrows():
                                    entry = {
                                        "Date": str(row.get("Date", "")),
                                        "Type": str(row.get("Type", "Bill")),
                                        "Amount": float(row.get("Amount", 0.0)),
                                        "Note": str(row.get("Note", "")),
                                        "Timestamp": firestore.SERVER_TIMESTAMP
                                    }
                                    db.collection('ledgers').document(cust_name).collection('transactions').add(entry)
                                
                            except Exception as e:
                                st.error(f"{cust_name} की फाइल में दिक्कत: {e}")
                        
                        st.success("✅ बधाई हो! आपके सारे पुराने खाते सफलतापूर्वक क्लाउड पर सेव हो गए हैं!")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("⚠️ कृपया पहले 'Browse files' पर क्लिक करके कोई पुरानी .csv फाइल सेलेक्ट करें।")

        with tab_ledger:
            st.subheader("📒 पार्टियों का खाता (Smart Cloud Ledger)")
            
            # --- 1. नई एंट्री / नया खाता ---
            with st.expander("➕ नई एंट्री या नया खाता बनाएं (Add New Entry)", expanded=False):
                with st.form("firebase_ledger_entry", clear_on_submit=True):
                    col_l1, col_l2 = st.columns(2)
                    with col_l1:
                        ledger_customer = st.text_input("पार्टी का नाम (Customer Name)*").strip().upper()
                        ledger_amount = st.number_input("अमाउंट (₹)*", min_value=0.0, step=100.0)
                    with col_l2:
                        ledger_status = st.selectbox("कैटेगरी चुनें", ["Bill (मार्केट से लेना है)", "Advance (पार्टी से पेमेंट आ गया)"])
                        ledger_note = st.text_input("विवरण (जैसे: Cash from shop, Old balance)")
                        
                    ledger_date = st.date_input("तारीख (Date)", datetime.datetime.today())
                    save_ledger_btn = st.form_submit_button("एंट्री सेव करें 💾")
                    
                    if save_ledger_btn and ledger_customer and ledger_amount > 0:
                        new_entry = {
                            "Date": ledger_date.strftime("%Y-%m-%d"), 
                            "Type": "Bill" if "Bill" in ledger_status else "Advance", 
                            "Amount": ledger_amount, 
                            "Note": ledger_note,
                            "Timestamp": firestore.SERVER_TIMESTAMP
                        }
                        # पैरेंट डॉक्यूमेंट बनाने का फिक्स
                        db.collection('ledgers').document(ledger_customer).set({"active": True}, merge=True)
                        db.collection('ledgers').document(ledger_customer).collection('transactions').add(new_entry)
                        st.success(f"✅ {ledger_customer} के खाते में एंट्री लाइव हो गई!")
                        time.sleep(1)
                        st.rerun()

            st.markdown("---")

            # --- 2. खाते देखना और एडिट करना (View/Edit Ledgers) ---
            st.markdown("### 👥 सभी खाते (Customer Ledgers)")
            st.info("💡 **टिप:** आप सीधे टेबल के अंदर क्लिक करके नई एंट्री जोड़ सकते हैं, या पुराने अमाउंट और विवरण बदल सकते हैं। डिलीट करने के लिए 'Delete' बॉक्स पर टिक करें और 'सेव' दबाएं।")
            all_ledgers = load_ledger_data()
            
            if not all_ledgers:
                st.warning("ℹ️ अभी तक किसी पार्टी का खाता नहीं बना है।")
            else:
                for cust_name, df_ledger in all_ledgers.items():
                    with st.expander(f"👤 {cust_name} का खाता"):
                        total_bill = df_ledger[df_ledger["Type"] == "Bill"]["Amount"].sum()
                        total_advance = df_ledger[df_ledger["Type"] == "Advance"]["Amount"].sum()
                        net_balance = total_bill - total_advance
                        
                        lc1, lc2, lc3 = st.columns(3)
                        lc1.metric("कुल बिल (लेना है)", f"₹ {total_bill:,.2f}")
                        lc2.metric("कुल जमा (आ गया)", f"₹ {total_advance:,.2f}")
                        
                        if net_balance > 0: lc3.metric("🔴 बकाया (Balance)", f"₹ {net_balance:,.2f}")
                        elif net_balance < 0: lc3.metric("🟢 एक्स्ट्रा जमा (Advance)", f"₹ {abs(net_balance):,.2f}")
                        else: lc3.metric("⚪ हिसाब चुकता", "₹ 0.00")

                        display_df = df_ledger.drop(columns=['doc_id', 'Timestamp'], errors='ignore')
                        display_df['Delete'] = False 
                        
                        edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, key=f"ed_{cust_name}")
                        
                        if st.button(f"💾 {cust_name} का खाता सेव करें", key=f"save_ed_{cust_name}", type="primary"):
                            with st.spinner("क्लाउड पर अपडेट हो रहा है..."):
                                for idx, row in edited_df.iterrows():
                                    if idx < len(df_ledger): 
                                        doc_id = df_ledger.iloc[idx]['doc_id']
                                        if row.get('Delete', False):
                                            db.collection('ledgers').document(cust_name).collection('transactions').document(doc_id).delete()
                                        else:
                                            original_row = df_ledger.iloc[idx]
                                            if row['Amount'] != original_row['Amount'] or row['Note'] != original_row['Note'] or row['Type'] != original_row['Type'] or row['Date'] != original_row['Date']:
                                                db.collection('ledgers').document(cust_name).collection('transactions').document(doc_id).update({
                                                    "Amount": row['Amount'],
                                                    "Note": row['Note'],
                                                    "Type": row['Type'],
                                                    "Date": row['Date']
                                                })
                                    else: 
                                        if not row.get('Delete', False) and not pd.isna(row.get('Amount')):
                                            new_entry = {
                                                "Date": str(row.get('Date', datetime.datetime.today().strftime("%Y-%m-%d"))), 
                                                "Type": str(row.get('Type', 'Bill')), 
                                                "Amount": float(row.get('Amount', 0)), 
                                                "Note": str(row.get('Note', '')),
                                                "Timestamp": firestore.SERVER_TIMESTAMP
                                            }
                                            # पैरेंट फोल्डर के साथ नई एंट्री
                                            db.collection('ledgers').document(cust_name).set({"active": True}, merge=True)
                                            db.collection('ledgers').document(cust_name).collection('transactions').add(new_entry)

                                st.success("✅ खाता सफलतापूर्वक अपडेट हो गया!")
                                time.sleep(1)
                                st.rerun()

            st.markdown("---")

            # --- 3. पुराने PDF बिल (Saved Invoices) ---
            st.markdown("### 📂 सेव किए गए बिल (Saved Invoices)")
            if not os.path.exists(INVOICE_FOLDER):
                os.makedirs(INVOICE_FOLDER)
            pdf_files = [f for f in os.listdir(INVOICE_FOLDER) if f.endswith('.pdf')]
            
            if pdf_files:
                parsed_files = []
                for pdf_f in pdf_files:
                    name_part = "Unknown"
                    date_part = "Unknown"
                    sort_key = "0"
                    try:
                        clean_name = pdf_f.replace("OURA_Bill_", "").replace(".pdf", "")
                        parts = clean_name.split("_")
                        if len(parts) >= 3:
                            time_str = parts[-1]
                            date_str = parts[-2]
                            name_str = "_".join(parts[:-2])
                            
                            formatted_date = f"{date_str[6:]}-{date_str[4:6]}-{date_str[:4]}"
                            formatted_time = f"{time_str[:2]}:{time_str[2:]}"
                            
                            name_part = name_str.replace("_", " ")
                            date_part = f"{formatted_date} | {formatted_time}"
                            sort_key = f"{date_str}{time_str}"
                        else:
                            name_part = clean_name
                    except:
                        pass
                    
                    parsed_files.append({
                        "filename": pdf_f,
                        "name": name_part,
                        "date": date_part,
                        "sort_key": sort_key
                    })
                    
                parsed_files.sort(key=lambda x: x["sort_key"], reverse=True)
                
                for item in parsed_files:
                    with st.container(border=True):
                        col_info, col_btn1, col_btn2 = st.columns([6, 2, 2])
                        with col_info:
                            st.markdown(f"👤 **{item['name']}** <br> 📅 <span style='color: gray; font-size: 14px;'>{item['date']}</span>", unsafe_allow_html=True)
                        with col_btn1:
                            with open(f"{INVOICE_FOLDER}/{item['filename']}", "rb") as f:
                                st.download_button(
                                    label="📥 डाउनलोड", 
                                    data=f.read(), 
                                    file_name=item['filename'], 
                                    mime="application/pdf", 
                                    key=f"dl_pdf_{item['filename']}",
                                    use_container_width=True
                                )
                        with col_btn2:
                            if st.button("🗑️ डिलीट", key=f"del_pdf_{item['filename']}", type="primary"):
                                try:
                                    os.remove(f"{INVOICE_FOLDER}/{item['filename']}")
                                    st.success("✅ बिल डिलीट हो गया!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error("⚠️ बिल डिलीट करने में समस्या आई।")
            else:
                st.info("ℹ️ अभी तक कोई PDF बिल जनरेट और सेव नहीं हुआ है।")

    st.markdown("---")

search_query = st.text_input(t("🔍 Search any product (e.g., Speaker, Watch...)", "🔍 कोई भी उत्पाद सर्च करें (जैसे: Speaker, Watch...)"), "")

def show_swipe_gallery(path_str, is_in_stock=True, wa_link="", first_img_link=""):
    if not path_str: return []
    paths = [p.strip() for p in path_str.split('|') if p.strip()]
    if not paths: return []
    
    html_code = '<div style="position: relative;">'
    
    if wa_link or first_img_link:
        html_code += '<div style="position: absolute; top: 10px; right: 10px; z-index: 10; display: flex; gap: 8px;">'
        if first_img_link:
            html_code += f'<a href="{first_img_link}" download="oura_product.jpg" target="_blank" style="background-color: #1877F2; color: white; padding: 6px 12px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">📥 Photo</a>'
        if wa_link:
            html_code += f'<a href="{wa_link}" target="_blank" style="background-color: #25D366; color: white; padding: 6px 12px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">💬 WA</a>'
        html_code += '</div>'
        
    html_code += '<div class="swipe-gallery">'
    img_style = "" if is_in_stock else "filter: grayscale(100%) opacity(60%);"
    for src in paths:
        if not src.startswith("http"):
            src = f"{GITHUB_RAW_URL}{urllib.parse.quote(src.replace('\\', '/'), safe='/')}"
        html_code += f'<a href="{src}" target="_blank"><img src="{src}" class="swipe-img" style="{img_style}" loading="lazy" alt="Product Image"></a>'
    
    html_code += '</div></div>'
    html_code += f'<div style="text-align:center; font-size:12px; color:gray; margin-top:-5px; margin-bottom:10px;">{t("Click photo to zoom 🔍", "ज़ूम करने के लिए फोटो पर क्लिक करें 🔍")}</div>'
    st.markdown(html_code, unsafe_allow_html=True)
    return paths

def show_product_card(row, idx, prefix):
    prefix_idx = f"{prefix}_{idx}"
    p_id = str(row.get('ID', prefix_idx)) 

    try: w_qty = int(float(row.get('Wholesale_Qty', 1)))
    except: w_qty = 1
    try: retail_price = float(row.get('Price', 0))
    except: retail_price = 0.0
    try: w_price = float(row.get('Wholesale_Price', retail_price))
    except: w_price = retail_price
    
    image_path_str = str(row.get("Image_Path", ""))
    paths_temp = [p.strip() for p in image_path_str.split('|') if p.strip()]
    img_link_for_wa = ""
    if paths_temp:
        img_link_for_wa = paths_temp[0]
        if not img_link_for_wa.startswith("http"):
            img_link_for_wa = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link_for_wa.replace('\\', '/'), safe='/')}"

    share_text = f"⚡ *OURA PRODUCTS - {row.get('Name', '')}* ⚡\n\n"
    share_text += f"💰 *{t('Wholesale Rate:', 'होलसेल रेट:')}* ₹{w_price} ({t('Min', 'कम से कम')} {w_qty} Pcs)\n"
    share_text += f"🛵 *{t('Retail Rate:', 'सिंगल पीस रेट:')}* ₹{retail_price}\n"
    share_text += f"🏭 *{t('Dispatch:', 'डिस्पैच:')}* Delhi (Oura Warehouse)\n"
    cat_url = urllib.parse.quote(str(row.get('Category', '')))
    app_link = f"https://ouraindia.streamlit.app/?cat={cat_url}"
    share_text += f"\n🛒 *{t('Book Order:', 'ऑर्डर बुक करें:')}* {app_link}\n"
    if img_link_for_wa:
        share_text += f"\n📷 *{t('Product Photo:', 'प्रोडक्ट फोटो:')}* {img_link_for_wa}"
    
    wa_link = f"https://wa.me/?text={urllib.parse.quote(share_text)}"

    with st.container(border=True):
        is_in_stock = row.get("In_Stock", True)
        
        all_paths = show_swipe_gallery(image_path_str, is_in_stock, wa_link, img_link_for_wa)
        
        st.write(f"**{row.get('Name', 'Unknown')}**")
        seller_val = row.get("Seller_Name")
        if pd.notna(seller_val) and str(seller_val).strip() != "":
            st.markdown(f"{t('🏪 Brand:', '🏪 सेलर / ब्रांड:')} <span style='color:#E65100; font-weight:bold;'>{str(seller_val).strip()}</span>", unsafe_allow_html=True)
            
        show_fd = current_config.get("free_delivery_tag", True)
        val_fd = row.get("Free_Delivery")
        if pd.notna(val_fd) and str(val_fd).strip() != "":
            show_fd = str(val_fd).lower() in ['true', 'yes', '1']
            
        t_sp_fd = t("🛵 **Single Piece (Free Delivery):**", "🛵 **सिंगल पीस (फ्री डिलीवरी):**")
        t_sp_ex = t("🛵 **Single Piece Rate:**", "🛵 **सिंगल पीस रेट:**")
        t_ws = t("📦 **Wholesale (Box Rate):**", "📦 **होलसेल (बॉक्स रेट):**")
        t_min = t(f"Min {w_qty} pieces", f"कम से कम {w_qty} पीस")
        t_ex = t("Extra Courier Charge", "कोरियर चार्ज एक्स्ट्रा")

        if w_qty > 1:
            if show_fd:
                st.markdown(f"{t_sp_fd} ₹{retail_price} <br> {t_ws} ₹{w_price} *({t_min}, <span style='color:#d32f2f;font-weight:bold;'>{t_ex}</span>)*", unsafe_allow_html=True)
            else:
                st.markdown(f"{t_sp_ex} ₹{retail_price} *(<span style='color:#d32f2f;font-weight:bold;'>{t_ex}</span>)* <br> {t_ws} ₹{w_price} *({t_min}, <span style='color:#d32f2f;font-weight:bold;'>{t_ex}</span>)*", unsafe_allow_html=True)
        else:
            if show_fd: st.markdown(f"{t_sp_ex} ₹{retail_price} *({t('Free Delivery','फ्री डिलीवरी')})*")
            else: st.markdown(f"{t_sp_ex} ₹{retail_price} *(<span style='color:#d32f2f;font-weight:bold;'>{t_ex}</span>)*", unsafe_allow_html=True)
            
        if is_in_stock:
            qty = st.number_input(t("Quantity (Pieces)", "मात्रा (पीस)"), min_value=1, value=1, key=f"q_{prefix_idx}")
            if st.button(t("🛒 Add to Cart", "🛒 कार्ट में डालें"), key=f"b_{prefix_idx}"):
                final_price = w_price if qty >= w_qty else retail_price
                if p_id in st.session_state.cart:
                    st.session_state.cart[p_id]["qty"] += qty
                    if st.session_state.cart[p_id]["qty"] >= w_qty:
                        st.session_state.cart[p_id]["price"] = w_price
                else:
                    st.session_state.cart[p_id] = {
                        "name": row.get('Name', 'Item'), 
                        "price": final_price, 
                        "qty": qty, 
                        "img_link": img_link_for_wa,
                        "seller": str(seller_val).strip() if pd.notna(seller_val) else ""
                    }
                save_cart_to_url()
                st.success(t("Added to Cart! 🛒", "कार्ट में जुड़ गया! 🛒"))
        else:
            st.markdown(f"<div style='background-color:#ffebee; color:#c62828; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border:1px solid #ef9a9a; margin-top:10px;'>🚫 {t('Out of Stock', 'आउट ऑफ स्टॉक')}</div>", unsafe_allow_html=True)
            
        can_edit = False
        if st.session_state.admin_logged_in: can_edit = True
        elif st.session_state.seller_logged_in and st.session_state.seller_logged_in == str(seller_val).strip(): can_edit = True
            
        can_market = False
        if st.session_state.admin_logged_in or st.session_state.seller_logged_in: can_market = True
            
        if can_edit or can_market: st.markdown("---")

        if can_edit:
            col_t1, col_t2, col_t3, col_t4 = st.columns([3, 2, 4, 3])
            with col_t1: st.markdown(f"**{t('Stock:', 'स्टॉक:')}**")
            with col_t2: st.toggle("✅" if is_in_stock else "🚫", value=is_in_stock, key=f"t_stk_{prefix_idx}", on_change=toggle_stock_callback, args=(str(row['ID']), f"t_stk_{prefix_idx}"))
            with col_t3: st.markdown(f"**{t('Delivery:', 'डिलीवरी:')}**")
            with col_t4: st.toggle("🆓" if show_fd else "🚚", value=show_fd, key=f"t_fd_{prefix_idx}", on_change=toggle_fd_callback, args=(str(row['ID']), f"t_fd_{prefix_idx}"), help=t("Turn on for Free Delivery", "फ्री डिलीवरी के लिए चालू करें"))

        if can_market:
            with st.expander(t("📘 Create Facebook / Instagram Post", "📘 Facebook / Instagram पर पोस्ट डालें")):
                fb_text_copy = f"🔥 OURA PRODUCTS - {row.get('Name')} 🔥\n\n📦 {t('Wholesale Rate:', 'होलसेल रेट:')} ₹{w_price} ({t('Min', 'कम से कम')} {w_qty} Pcs)\n🛵 {t('Single Piece Rate:', 'सिंगल पीस रेट:')} ₹{retail_price}\n🏭 {t('Direct from Manufacturer:', 'सीधा मैन्युफैक्चरर से:')} Delhi (Oura Products)\n\n👇 {t('Check rates and order online now:', 'अभी रेट चेक करें और ऑनलाइन ऑर्डर करें:')}\n{app_link}\n\n#OuraProducts #WholesaleMarket #DelhiWholesale #Electronics"
                st.info(t("💡 **Tip:** 1. Click '📥 Photo' on the image above to save it. \n2. Copy the text below. \n3. Paste on Facebook!", "💡 **टिप:** 1. ऊपर फोटो पर बने नीले '📥 Photo' बटन को दबाकर फोटो सेव करें। \n2. नीचे से टेक्स्ट Copy करें। \n3. फेसबुक पर जाकर पेस्ट कर दें!"))
                st.text_area(t("Text for Facebook Post:", "Facebook पोस्ट के लिए टेक्स्ट:"), value=fb_text_copy, height=200, key=f"fb_txt_{prefix_idx}")

        if can_edit:
            with st.expander(t("✏️ Edit Product (रेट, स्टॉक या फोटो बदलें)", "✏️ रेट, स्टॉक या डिलीवरी बदलें (Edit)")):
                with st.form(f"edit_form_{prefix_idx}"):
                    if st.session_state.admin_logged_in: e_name = st.text_input("Name (नाम)", value=str(row.get("Name", "")))
                    else:
                        st.text_input("Name (नाम) - Read Only", value=str(row.get("Name", "")), disabled=True)
                        e_name = str(row.get("Name", ""))
                        
                    col_x, col_y = st.columns(2)
                    with col_x:
                        e_price = st.number_input("Retail Price (सिंगल रेट)", value=float(retail_price), format="%.2f", step=0.50)
                        e_w_qty = st.number_input("Wholesale Qty (होलसेल पीस)", value=w_qty)
                    with col_y:
                        e_w_price = st.number_input("Wholesale Price (होलसेल रेट)", value=float(w_price), format="%.2f", step=0.50)
                        e_fd = st.selectbox(t("Delivery Option", "डिलीवरी ऑप्शन"), [t("Free Delivery", "फ्री डिलीवरी"), t("Extra Courier Charge", "एक्स्ट्रा कोरियर चार्ज")], index=0 if show_fd else 1)
                            
                    e_imgs = st.file_uploader(t("Upload New Photos (Optional)", "नयी फोटो डालें (अगर बदलनी हो)"), type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=f"e_img_up_{prefix_idx}")
                    update_btn = st.form_submit_button("✅ Update / सेव करें")
                    
                if update_btn:
                    target_id = str(row['ID'])
                    is_free_val = True if e_fd in ["फ्री डिलीवरी", "Free Delivery"] else False
                    update_dict = {
                        "Price": e_price, "Wholesale_Price": e_w_price, 
                        "Wholesale_Qty": e_w_qty, "Free_Delivery": is_free_val
                    }
                    if st.session_state.admin_logged_in: update_dict["Name"] = e_name
                    if e_imgs:
                        with st.spinner("Uploading new photos..."):
                            image_paths = []
                            for img in e_imgs:
                                compressed_bytes, _ = compress_image(img.getvalue())
                                img_url = upload_image_to_imgbb(compressed_bytes)
                                if img_url: image_paths.append(img_url)
                            if image_paths: update_dict["Image_Path"] = "|".join(image_paths)
                                
                    db.collection('products').document(target_id).update(update_dict)
                    load_products.clear()
                    st.rerun()

            st.markdown("---")
            if st.button(t("🗑️ Delete Product", "🗑️ यह उत्पाद हमेशा के लिए हटाएं (Delete)"), key=f"del_p_{prefix_idx}"):
                db.collection('products').document(str(row['ID'])).delete()
                load_products.clear()
                st.rerun()

if products_df.empty:
    st.info(t("New products coming soon!", "जल्द ही नए उत्पाद आएंगे!"))
else:
    if search_query:
        st.subheader(t(f"Search results for '{search_query}':", f"'{search_query}' के सर्च रिजल्ट:"))
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        if filtered_df.empty: st.warning(t("No product found with this name.", "इस नाम से कोई उत्पाद मिला।"))
        else:
            cols = st.columns(3)
            for idx, row in filtered_df.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "search")
    
    elif st.session_state.selected_category is None:
        st.subheader(t("🛍️ Categories", "🛍️ कैटेगरीज"))
        valid_categories = products_df['Category'].dropna().unique().tolist()
        
        if len(valid_categories) == 0: 
            st.write(t("No categories yet.", "अभी कोई कैटेगरी नहीं है।"))
        else:
            cat_container = st.container()
            with cat_container:
                st.markdown('<div id="safe-cat-grid"></div>', unsafe_allow_html=True)
                st.markdown("""
                <style>
                div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) {
                    display: flex !important;
                    flex-direction: row !important;
                    flex-wrap: wrap !important;
                    gap: 10px !important;
                    justify-content: flex-start !important;
                }
                div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"] {
                    width: calc(33.33% - 10px) !important; 
                }
                @media (min-width: 600px) {
                    div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"] {
                        width: calc(20% - 10px) !important; 
                    }
                }
                div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(#safe-cat-grid),
                div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(style) {
                    display: none !important;
                }
                div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button {
                    height: 85px !important;
                    min-height: 85px !important;
                    width: 100% !important;
                    border-radius: 12px !important;
                    background: linear-gradient(135deg, #ffffff, #f0f4f8) !important;
                    border: 1px solid #c5d4eb !important;
                    box-shadow: 2px 4px 8px rgba(0,0,0,0.06) !important;
                    color: #1a202c !important;
                    font-weight: 700 !important;
                    font-size: 13px !important;
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    line-height: 1.2 !important;
                    padding: 4px !important;
                    transition: all 0.2s ease-in-out !important;
                }
                div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button:hover {
                    transform: translateY(-3px) !important;
                    box-shadow: 2px 6px 12px rgba(0,0,0,0.12) !important;
                    border-color: #2b6cb0 !important;
                }
                div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button:active {
                    transform: scale(0.95) !important;
                }
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
        
        if st.button(t("🏠 All Categories", "🏠 सारी कैटेगरीज"), key="float_back_btn"):
            st.session_state.selected_category = None
            if "cat" in st.query_params: del st.query_params["cat"]
            save_cart_to_url()
            st.rerun()
            
        float_js = """
        <script>
        const parentDoc = window.parent.document;
        const buttons = parentDoc.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.innerText && (btn.innerText.includes('सारी कैटेगरीज') || btn.innerText.includes('All Categories'))) {
                btn.style.position = 'fixed';
                btn.style.bottom = '120px';
                btn.style.left = '15px';
                btn.style.zIndex = '999999';
                btn.style.background = '#2b6cb0'; 
                btn.style.color = 'white';
                btn.style.padding = '12px 18px';
                btn.style.borderRadius = '50px';
                btn.style.border = '2px solid white';
                btn.style.fontWeight = 'bold';
                btn.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
                btn.style.minHeight = 'auto'; 
                btn.style.width = 'auto';
                btn.style.animation = 'none';
            }
        });
        </script>
        """
        st_components.html(float_js, height=0, width=0)

        cat_products = products_df[products_df['Category'] == st.session_state.selected_category]
        if cat_products.empty: st.write(t("No products in this category yet.", "इस कैटेगरी में अभी कोई उत्पाद नहीं है।"))
        else:
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "cat_view")

st.markdown("<br><br><br>", unsafe_allow_html=True) 
st.markdown("---")
st.header(t("🛒 Your Basket", "🛒 आपकी बास्केट"))

if st.session_state.cart:
    total = 0
    count = 1
    
    for k, item in list(st.session_state.cart.items()):
        subtotal = item['price'] * item['qty']
        total += subtotal
        col_img, col_details = st.columns([2, 8])
        with col_img:
            if item.get('img_link'): st.image(item['img_link'], use_container_width=True)
            else: st.write("📷")
        with col_details:
            st.write(f"✔️ **{item['name']}**")
            c1, c2 = st.columns([7, 3])
            with c1: st.write(f"{t('Qty:', 'मात्रा:')} {item['qty']} x ₹{item['price']:.2f} = **₹{subtotal:.2f}**")
            with c2:
                if st.button("❌", key=f"del_item_{k}"):
                    del st.session_state.cart[k]
                    save_cart_to_url()
                    st.rerun()
        st.markdown("---")
        count += 1
    
    st.subheader(f"{t('Total Amount: ₹', 'कुल माल: ₹')}{total:.2f}")
    
    available_upis = {}
    if current_config.get("phonepe_upi"): available_upis["PhonePe"] = {"id": current_config["phonepe_upi"], "color": "#5e35b1", "icon": "🟣"}
    if current_config.get("paytm_upi"): available_upis["Paytm"] = {"id": current_config["paytm_upi"], "color": "#00baf2", "icon": "🔵"}
    if current_config.get("gpay_upi"): available_upis["Google Pay"] = {"id": current_config["gpay_upi"], "color": "#1a73e8", "icon": "🔴"}
    if current_config.get("bhim_upi"): available_upis["BHIM"] = {"id": current_config["bhim_upi"], "color": "#ff7043", "icon": "🟠"}

    if available_upis:
        st.markdown(f"### 💳 {t('Secure Online Payment', 'सुरक्षित online पेमेंट')}")
        with st.expander(t("Pay by Scanning (QR Code)", "स्कैन करके पेमेंट करें (QR Code)")):
            qr_tabs = st.tabs(list(available_upis.keys()))
            for idx, (name, data) in enumerate(available_upis.items()):
                with qr_tabs[idx]:
                    qr_data = f"upi://pay?pa={data['id']}&pn=Oura_Products&am={total:.2f}&cu=INR"
                    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(qr_data)}", width=150)
                    st.success(f"**{name} UPI ID:** `{data['id']}`")

    st.markdown("---")
    st.markdown(f"### 🤝 {t('100% Customer Satisfaction', '100% ग्राहक संतुष्टि (Customer Trust)')}")
    st.success(t("✅ **Live Packing Proof:** Video & photo of your package will be sent to WhatsApp before dispatch.", "✅ **लाइव पैकिंग प्रूफ:** आपकी पूरी संतुष्टि और भरोसे के लिए, आपके माल की **पैकिंग की लाइव वीडियो और फोटो** डिस्पैच (Dispatch) से पहले सीधे आपके WhatsApp पर भेजी जाएगी।"))

    st.markdown("---")
    st.markdown(f"### 📍 {t('Delivery & Billing Information', 'डिलीवरी और बिल की जानकारी')}")
    
    with st.form("billing_form"):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            cust_name = st.text_input(t("Your Name / Shop Name", "आपका नाम / दुकान का नाम"))
            st.info(t("💡 The system will automatically fetch the previous balance if the name matches an existing account.", "💡 पार्टी का नाम सही (सेम स्पेलिंग) डालें, सिस्टम पुराना बकाया अपने आप निकाल लेगा!"))
            cust_mobile = st.text_input(t("Mobile Number (10 digits)", "मोबाईल नंबर (10 अंक)"))
            cust_address = st.text_area(t("Full Address (with City, Pincode)", "पूरा पता (शहर, पिनकोड सहित)"))
        with col_d2:
            bill_date = st.date_input(t("Invoice Date", "बिल की तारीख"), datetime.date.today())
            gst_choice = st.selectbox(t("Select Bill Type:", "बिल का प्रकार चुनें:"), 
                                     [t("Without GST (Estimate)", "बिना GST (Estimate)"), "GST @ 5%", "GST @ 12%", "GST @ 18%", "GST @ 28%"])
            
            gst_percent = 0
            if "5%" in gst_choice: gst_percent = 5
            elif "12%" in gst_choice: gst_percent = 12
            elif "18%" in gst_choice: gst_percent = 18
            elif "28%" in gst_choice: gst_percent = 28
            
            cust_gst = st.text_input(t("Customer GST Number (15 chars)", "ग्राहक का GST नंबर (अगर है तो 15 अक्षर डालें)")) if gst_percent > 0 else ""
            shipping_cost = st.number_input(t("🚚 Courier / Packing Charge (₹)", "🚚 कोरियर / पैकिंग चार्ज (₹)"), min_value=0.0, value=0.0, step=10.0, format="%.2f")
            
            amount_paid = st.number_input(t("💸 Amount Paid Now (अभी कितने पैसे दिए / ₹)", "💸 अभी कितने पैसे जमा किए (Cash/Online)"), min_value=0.0, value=0.0, step=10.0, format="%.2f")

        submit_billing = st.form_submit_button(t("✅ Prepare Bill", "✅ बिल तैयार करें"))

    if submit_billing:
        is_valid = True
        if cust_mobile and (not cust_mobile.strip().isdigit() or len(cust_mobile.strip()) != 10):
            st.warning(t("⚠️ Enter valid 10 digit mobile.", "⚠️ कृपया सही 10 अंकों का मोबाईल नंबर डालें।"))
            is_valid = False

        if is_valid:
            if st.session_state.cart:
                auto_last_balance = 0.0
                safe_name = cust_name.strip().upper() if cust_name else ""
                
                if safe_name:
                    try:
                        docs = db.collection('ledgers').document(safe_name).collection('transactions').stream()
                        t_bill = 0
                        t_adv = 0
                        for doc in docs:
                            d = doc.to_dict()
                            if d.get("Type") == "Bill": t_bill += d.get("Amount", 0)
                            elif d.get("Type") == "Advance": t_adv += d.get("Amount", 0)
                        auto_last_balance = t_bill - t_adv
                    except: pass

                pdf_bytes = generate_pdf_bill(
                    st.session_state.cart, cust_name, cust_mobile, cust_address, 
                    cust_gst, gst_percent, shipping_cost, auto_last_balance, amount_paid, current_config, bill_date
                )
                
                # फिक्स: PDF के नाम में से गलत कैरेक्टर हटाना
                if safe_name:
                    safe_file_name = re.sub(r'[\\/*?:"<>|]', "", safe_name).replace(' ', '_')
                else:
                    safe_file_name = 'Cash'
                    
                date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                st.session_state.ready_filename = f"OURA_Bill_{safe_file_name}_{date_str}.pdf"
                st.session_state.ready_pdf = pdf_bytes

                # फिक्स: फोल्डर को चेक करना और न होने पर बनाना
                if not os.path.exists(INVOICE_FOLDER):
                    os.makedirs(INVOICE_FOLDER)

                pdf_path = f"{INVOICE_FOLDER}/{st.session_state.ready_filename}"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                item_details_list = []
                taxable_amount = 0
                for k, item in st.session_state.cart.items():
                    item_details_list.append(f"{item['name']} ({item['qty']}Pcs)")
                    taxable_amount += (item['qty'] * item['price'])
                
                taxable_amount += shipping_cost
                gst_amt = (taxable_amount * gst_percent) / 100
                current_bill_total = taxable_amount + gst_amt 
                full_item_details = " | ".join(item_details_list)
                
                if safe_name:
                    batch = db.batch()
                    parent_ref = db.collection('ledgers').document(safe_name)
                    # फिक्स: पैरेंट फोल्डर बनाना
                    batch.set(parent_ref, {"active": True}, merge=True)
                    ledger_ref = parent_ref.collection('transactions')
                    
                    bill_entry = {
                        "Date": bill_date.strftime("%Y-%m-%d"),
                        "Type": "Bill", 
                        "Amount": current_bill_total, 
                        "Note": full_item_details,
                        "Timestamp": firestore.SERVER_TIMESTAMP
                    }
                    batch.set(ledger_ref.document(), bill_entry)
                    
                    if amount_paid > 0:
                        adv_entry = {
                            "Date": bill_date.strftime("%Y-%m-%d"),
                            "Type": "Advance", 
                            "Amount": amount_paid, 
                            "Note": "Cash/Online paid with bill",
                            "Timestamp": firestore.SERVER_TIMESTAMP
                        }
                        batch.set(ledger_ref.document(), adv_entry)
                    
                    batch.commit()

                msg = f"🧾 *NEW ORDER RECEIVED* 🧾\n\n👤 *Cust:* {cust_name}\n📞 *Mob:* {cust_mobile}\n"
                st.session_state.ready_msg_for_admin = msg

    if 'ready_pdf' in st.session_state:
        st.success("✅ Bill is ready! Download PDF or send to WhatsApp below:")
        st.download_button(
            label="📄 Download Professional PDF Bill",
            data=st.session_state.ready_pdf,
            file_name=st.session_state.ready_filename,
            mime="application/pdf",
            use_container_width=True
        )

        st.markdown(f"### 📲 {t('Send Order on WhatsApp', 'WhatsApp पर ऑर्डर भेजें')}")
        admin_num = current_config.get("admin_whatsapp", "919891587437")
        wa_link = f"https://wa.me/{admin_num}?text={urllib.parse.quote(st.session_state.ready_msg_for_admin)}"
        st.markdown(f'''<a href="{wa_link}" target="_blank" style="display:block; text-align:center; background: #25D366; color:white; padding:15px; border-radius:10px; text-decoration:none; font-size:18px; font-weight:bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom:10px;">✅ {t("Send Bill", "बिल भेजो")}</a>''', unsafe_allow_html=True)

    if st.button(t("🗑️ Empty Basket", "🗑️ बास्केट खाली करें")):
        st.session_state.cart = {}
        if 'ready_pdf' in st.session_state: del st.session_state.ready_pdf
        if 'ready_msg_for_admin' in st.session_state: del st.session_state.ready_msg_for_admin
        save_cart_to_url()
        st.rerun()

admin_wa_number = current_config.get("admin_whatsapp", "919891587437")
st.markdown(f'''<a id="oura-wa-btn" href="https://wa.me/{admin_wa_number}" target="_blank" title="WhatsApp Us">💬 WhatsApp</a>''', unsafe_allow_html=True)

drag_js_code = """
<script>
const parentDoc = window.parent.document;
const btn = parentDoc.getElementById('oura-wa-btn');
if (btn && !btn.dataset.draggable) {
    btn.dataset.draggable = "true";
    let isDragging = false, startY, startTop;
    const onStart = (e) => {
        if(e.type === 'mousedown' || e.type === 'touchstart') {
            isDragging = true; startY = e.touches ? e.touches[0].clientY : e.clientY;
            startTop = btn.offsetTop; btn.style.transition = 'none';
        }
    };
    const onMove = (e) => {
        if (!isDragging) return;
        e.preventDefault(); 
        let currentY = e.touches ? e.touches[0].clientY : e.clientY;
        let newTop = startTop + (currentY - startY);
        if (newTop < 80) newTop = 80;
        if (newTop > parentDoc.documentElement.clientHeight - 80) newTop = parentDoc.documentElement.clientHeight - 80;
        btn.style.top = newTop + 'px'; btn.style.bottom = 'auto'; 
    };
    const onEnd = () => { isDragging = false; };
    btn.addEventListener('touchstart', onStart, {passive: false});
    parentDoc.addEventListener('touchmove', onMove, {passive: false});
    parentDoc.addEventListener('touchend', onEnd);
    btn.addEventListener('mousedown', onStart);
    parentDoc.addEventListener('mousemove', onMove);
    parentDoc.addEventListener('mouseup', onEnd);
    btn.addEventListener('click', (e) => { if (Math.abs(btn.offsetTop - startTop) > 10) e.preventDefault(); });
}
</script>
"""
st_components.html(drag_js_code, height=0, width=0)
