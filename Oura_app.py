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

# --- FOLDER SETUP FOR INVOICES ---
INVOICE_FOLDER = "saved_invoices"
if not os.path.exists(INVOICE_FOLDER): os.makedirs(INVOICE_FOLDER)

# --- FIREBASE SYSTEM ---
import firebase_admin
from firebase_admin import credentials, firestore

try:
    import pytesseract
except ImportError:
    pass

GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# --- INITIALIZE FIREBASE ---
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
        st.error(f"🚨 Firebase Setup Error: {e}")

db = firestore.client()

def upload_image_to_imgbb(file_bytes):
    try:
        imgbb_key = st.secrets.get("IMGBB_API_KEY")
        if not imgbb_key:
            st.error("🚨 ImgBB API Key not found in Secrets!")
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
            st.error("Image upload failed.")
            return None
    except Exception as e:
        st.error(f"Error: {e}")
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
        "has_banner": False, "has_logo": False, "free_delivery_tag": True, "sellers": {},
        "cert1_url": "", "cert2_url": "", "cert3_url": "",
        "telegram_token": "", "telegram_chat_id": "",
        "bg_color": "#f4f6f9"
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

# --- LOAD CATEGORY IMAGES ---
@st.cache_data(ttl=300, show_spinner=False)
def load_category_images():
    try:
        doc = db.collection('settings').document('category_images').get()
        if doc.exists:
            return doc.to_dict()
    except: pass
    return {}

def send_telegram_alert(token, chat_id, text_msg, pdf_bytes=None, pdf_name="Invoice.pdf"):
    if not token or not chat_id:
        return False
    try:
        if pdf_bytes:
            url = f"https://api.telegram.org/bot{token}/sendDocument"
            files = {'document': (pdf_name, pdf_bytes, 'application/pdf')}
            data = {'chat_id': chat_id, 'caption': text_msg[:1000]}
            res = requests.post(url, data=data, files=files)
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {'chat_id': chat_id, 'text': text_msg, 'parse_mode': 'Markdown'}
            res = requests.post(url, data=data)
        return res.status_code == 200
    except Exception as e:
        return False

# --- PDF GENERATION ---
def generate_pdf_bill(cart, cust_name, cust_mobile, cust_address, cust_gst, gst_rate, shipping_charge, last_balance, amount_paid, config, invoice_date, total_savings):
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
    pdf.cell(30, 10, "Net Rate", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Amount", border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    subtotal = 0
    idx = 1
    
    for k, item in cart.items():
        orig_p = item['price']
        d_pct = item.get('discount_pct', 0.0)
        d_name = item.get('offer_name', '')
        net_p = orig_p - (orig_p * d_pct / 100)
        amt = net_p * item['qty']
        subtotal += amt
        
        clean_name = re.sub(r'[^\x00-\x7F]+', ' ', str(item['name'])) 
        
        if d_pct > 0:
            clean_name += f" ({d_name}: -{d_pct}%)"
            
        if len(clean_name) > 40: clean_name = clean_name[:37] + "..."
        
        pdf.cell(15, 10, str(idx), border=1, align='C')
        pdf.cell(90, 10, clean_name, border=1, align='L')
        
        unit_display = item.get('unit', 'Pcs')
        pdf.cell(25, 10, f"{item['qty']} {unit_display[:5]}", border=1, align='C')
        
        pdf.cell(30, 10, f"{net_p:.2f}", border=1, align='R')
        pdf.cell(30, 10, f"{amt:.2f}", border=1, align='R')
        pdf.ln()
        idx += 1
        
    pdf.ln(2)
    
    if total_savings > 0:
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(34, 139, 34)
        pdf.cell(190, 8, f"*** YAY! You saved Rs. {total_savings:.2f} with Special Offers! ***", ln=True, align='C')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

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
        pdf.cell(160, 10, "Add: Previous Balance", border=1, align='R')
        pdf.cell(30, 10, f"{last_balance:.2f}", border=1, align='R')
        pdf.ln()
        grand_total += last_balance
    elif last_balance < 0:
        pdf.cell(160, 10, "Less: Previous Advance", border=1, align='R')
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

            @keyframes shine {
                0% { background-position: -200% center; }
                100% { background-position: 200% center; }
            }
            .offer-tag {
                background: linear-gradient(90deg, #ff007f 0%, #ff0000 25%, #ff5e00 50%, #ff0000 75%, #ff007f 100%);
                background-size: 200% auto;
                color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 13px;
                animation: shine 2.5s linear infinite;
                text-align: center; margin-bottom: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                border: 1px solid #ffcc00; letter-spacing: 0.5px;
            }

            /* Custom Grid active state */
            .cat-card:active {
                transform: scale(0.92) !important;
                background-color: #f7fafc !important;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- GLOBAL BACKGROUND STYLING ---
global_bg_color = current_config.get("bg_color", "#f4f6f9")
st.markdown(f"""
<style>
.stApp {{ background-color: {global_bg_color} !important; }}
</style>
""", unsafe_allow_html=True)
# ---------------------------------

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

def safe_int(val, default=1):
    try:
        if pd.isna(val) or str(val).strip() == "": return default
        return int(float(val))
    except: return default

def safe_float(val, default=0.0):
    try:
        if pd.isna(val) or str(val).strip() == "": return default
        return float(val)
    except: return default

expected_columns = ["ID", "Name", "Retail_Qty", "Price", "Cash_Price", "Tier1_Price", "Tier1_Qty", "Tier2_Price", "Tier2_Qty", "Category", "Image_Path", "Free_Delivery", "Seller_Name", "In_Stock", "Unit_Base", "Unit_T1", "Unit_T2", "Offer_Name", "Discount_Percent"]

@st.cache_data(ttl=3600, show_spinner=False)
def load_products():
    try:
        docs = db.collection('products').stream()
        data = [doc.to_dict() for doc in docs]
        if data:
            df = pd.DataFrame(data)
            if 'Unit_Base' not in df.columns: df['Unit_Base'] = df.get('Unit_Type', 'Pcs')
            if 'Unit_T1' not in df.columns: df['Unit_T1'] = df.get('Unit_Type', 'Pcs')
            if 'Unit_T2' not in df.columns: df['Unit_T2'] = df.get('Unit_Type', 'Pcs')
            df['Unit_Base'].fillna('Pcs', inplace=True)
            df['Unit_T1'].fillna('Pcs', inplace=True)
            df['Unit_T2'].fillna('Pcs', inplace=True)
            return df
    except: pass
    return pd.DataFrame(columns=expected_columns)

@st.cache_data(ttl=300, show_spinner=False)
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
        cart_str = "_".join([f"{k}*{v['qty']}" for k, v in st.session_state.cart.items()])
        st.query_params["cart"] = cart_str
    else:
        if "cart" in st.query_params:
            del st.query_params["cart"]

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'seller_logged_in' not in st.session_state: st.session_state.seller_logged_in = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'share_msg' not in st.session_state: st.session_state.share_msg = None
if 'share_img_path' not in st.session_state: st.session_state.share_img_path = None
if 'wholesale_mode' not in st.session_state: st.session_state.wholesale_mode = False

if 'cart_loaded' not in st.session_state:
    st.session_state.cart = {}
    if "cart" in st.query_params and not products_df.empty:
        cart_str = st.query_params["cart"]
        items = cart_str.split("_")
        for item in items:
            try:
                if "*" in item:
                    k_part, qty_str = item.split("*", 1)
                    parts = k_part.split("|")
                    p_id = parts[0]
                    unit = parts[1] if len(parts) > 1 else "Pcs"
                    price = float(parts[2]) if len(parts) > 2 else 0.0
                    p_type = parts[3] if len(parts) > 3 else ""
                    qty = safe_int(qty_str, 1)
                    
                    match = products_df[products_df['ID'].astype(str) == p_id]
                    if not match.empty:
                        row = match.iloc[0]
                        image_path_str = str(row.get("Image_Path", ""))
                        paths = [p.strip() for p in image_path_str.split('|') if p.strip()]
                        img_link = paths[0] if paths else ""
                        if img_link and not img_link.startswith("http"):
                            img_link = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link.replace('\\', '/'), safe='/')}"
                            
                        disc_pct = safe_float(row.get('Discount_Percent'), 0.0)
                        offer_nm = str(row.get('Offer_Name', '')).strip()

                        base_name = row.get('Name', 'Item')
                        final_name = f"{base_name} ({p_type})" if p_type in ["Online", "Cash"] else base_name
                            
                        st.session_state.cart[k_part] = {
                            "name": final_name,
                            "price": price if price > 0 else safe_float(row.get('Price'), 0.0),
                            "qty": qty, "img_link": img_link,
                            "seller": str(row.get("Seller_Name", "")).strip(), "unit": unit,
                            "discount_pct": disc_pct, "offer_name": offer_nm
                        }
            except Exception as e:
                pass
    st.session_state.cart_loaded = True

if "cat" in st.query_params:
    st.session_state.selected_category = st.query_params["cat"]
else:
    st.session_state.selected_category = None

if st.session_state.seller_logged_in:
    seller_name = st.session_state.seller_logged_in
    valid_sellers = [v["name"] if isinstance(v, dict) else v for v in current_config.get("sellers", {}).values()]
    if seller_name not in valid_sellers:
        st.session_state.seller_logged_in = None
        st.error("⚠️ Your seller account has been closed by Admin!")
        time.sleep(2)
        st.rerun()

# --- HEADER LAYOUT ---
col_logo, col_login = st.columns([8, 2])
with col_logo:
    if current_config.get("has_banner", False) and current_config.get("banner_url"):
        try: st.image(current_config["banner_url"], use_container_width=True)
        except: st.title("🛍️ Oura Products - Wholesale")
    else:
        st.title("🛍️ Oura Products - Wholesale")

with col_login:
    if not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
        if st.button("🔒 Store Login"):
            st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button("🚪 Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.seller_logged_in = None
            st.session_state.show_login = False
            st.rerun()

en_marquee = "🏭 Are you a manufacturer or wholesaler? Let's take your business to new heights with Oura! 🚀"
multi_color_marquee = f"""
<div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; margin-bottom: 10px; margin-top: 10px; border: 1px solid #bbdefb;">
    <marquee behavior="scroll" direction="left" scrollamount="6" style="color: #0d47a1; font-size: 16px; font-weight: bold; font-family: sans-serif;">
        {en_marquee}
    </marquee>
</div>
"""
st.markdown(multi_color_marquee, unsafe_allow_html=True)


if 'ws_clicks' not in st.session_state: 
    st.session_state.ws_clicks = 0

if 'ws_toggle_widget' not in st.session_state:
    st.session_state.ws_toggle_widget = st.session_state.wholesale_mode

def handle_ws_toggle():
    if st.session_state.ws_toggle_widget: 
        st.session_state.ws_clicks += 1
        if st.session_state.ws_clicks >= 5:
            st.session_state.wholesale_mode = True
            st.session_state.ws_clicks = 0 
        else:
            st.session_state.ws_toggle_widget = False 
    else: 
        st.session_state.wholesale_mode = False
        st.session_state.ws_clicks = 0

st.toggle(
    "📦 ", 
    key="ws_toggle_widget",
    on_change=handle_ws_toggle
)


if st.session_state.show_login and not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    with st.container(border=True):
        st.subheader("Store Login")
        login_type = st.radio("Select Login Type:", ["Seller", "Admin"], horizontal=True)
        
        if login_type == "Admin":
            password = st.text_input("Enter Admin Password", type="password")
            if st.button("Login"):
                try: correct_password = st.secrets["ADMIN_PASSWORD"]
                except: correct_password = None
                    
                if correct_password and password == correct_password:
                    st.session_state.admin_logged_in = True
                    st.session_state.seller_logged_in = None
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("❌ Incorrect Password!")
        else:
            seller_token = st.text_input("Enter Seller Token", type="password")
            if st.button("Login"):
                sellers_dict = current_config.get("sellers", {})
                if seller_token in sellers_dict:
                    s_data = sellers_dict[seller_token]
                    st.session_state.seller_logged_in = s_data["name"] if isinstance(s_data, dict) else s_data
                    st.session_state.admin_logged_in = False
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("❌ Invalid Token! Contact Admin.")
            
            st.markdown("---")
            st.markdown(f"**Don't have a Seller Token?**")
            admin_wa = current_config.get("admin_whatsapp", "919891587437")
            req_msg = "Hello Admin, I want to become a seller on Oura Products. Please provide me a Seller Token.\n\nMy Brand Name is: \nMy Contact Number is: "
            encoded_req = urllib.parse.quote(req_msg)
            wa_req_link = f"https://wa.me/{admin_wa}?text={encoded_req}"
            
            st.markdown(f'''<a href="{wa_req_link}" target="_blank" style="display:block; text-align:center; background-color:#25D366; color:white; padding:10px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:14px; margin-top:5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">📲 Request Token via WhatsApp</a>''', unsafe_allow_html=True)

    st.markdown("---")

if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success("✅ Logged in as Admin. You have full control.")
        tab_add, tab_banner, tab_settings, tab_ledger = st.tabs([
            "➕ Add Product", 
            "🖼️ Banner & Logo", 
            "⚙️ Settings",
            "📒 Ledger / Invoices"
        ])
    else:
        st.success(f"🏪 Welcome: {st.session_state.seller_logged_in} (Seller)")
        tab_add, = st.tabs(["➕ Add Product"])
    
    with tab_add:
        if st.session_state.share_msg:
            st.success("✅ Great! Your new product is live on Oura.")
            if st.session_state.share_img_path:
                st.image(st.session_state.share_img_path, width=200)
            encoded_share = urllib.parse.quote(st.session_state.share_msg)
            wa_share_link = f"https://wa.me/?text={encoded_share}"
            st.markdown(f'''<a href="{wa_share_link}" target="_blank" style="display:inline-block; background-color:#25D366; color:white; padding:12px 25px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:16px; margin-bottom:15px;">📢 Share on WhatsApp</a>''', unsafe_allow_html=True)
            if st.button("➕ Add Another Product"):
                st.session_state.share_msg = None
                st.session_state.share_img_path = None
                st.rerun()
        else:
            with st.form("add_product", clear_on_submit=True):
                col_id, col_name = st.columns([1, 2])
                with col_id: new_id = st.text_input("ID (Keep Unique)")
                with col_name: new_name = st.text_input("Product Name")
                
                st.markdown("**🎁 Special Offer / Discount**")
                col_off1, col_off2 = st.columns(2)
                with col_off1: new_offer_name = st.text_input("Offer Name (e.g., Diwali Offer, 15 Aug Sale)", "")
                with col_off2: new_discount = st.number_input("Discount %", min_value=0.0, max_value=99.0, value=0.0, step=1.0)
                
                st.markdown("---")
                st.markdown("**💰 Pricing Tiers (Set Unit and Quantity for each tier)**")
                unit_options = ["Pcs", "Dozen", "Box", "Set"]
                
                st.markdown("**(1) Base / Sample (Online vs Cash)**")
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                with c1: new_u_base = st.selectbox("Unit", unit_options, key="ub")
                with c2: new_retail_qty = st.number_input("Min Qty", min_value=1, value=1, key="n_r_q")
                with c3: new_online_price = st.number_input("💳 Online Rate (₹)", min_value=0.0, value=0.0, step=0.50, format="%.2f")
                with c4: new_cash_price = st.number_input("💵 Cash Rate (₹)", min_value=0.0, value=0.0, step=0.50, format="%.2f")
                
                st.markdown("**(2) Tier 1 (Bulk) - Optional**")
                c4, c5, c6 = st.columns([1, 1, 1])
                with c4: new_u_t1 = st.selectbox("Unit", unit_options, index=1, key="ut1")
                with c5: new_t1_qty = st.number_input("Min Qty", min_value=0, value=0, key="n_t1_q")
                with c6: new_t1_price = st.number_input("Rate (₹)", min_value=0.0, value=0.0, step=0.50, format="%.2f", key="n_t1_p")
                
                st.markdown("**(3) Tier 2 (Super Bulk) - Optional**")
                c7, c8, c9 = st.columns([1, 1, 1])
                with c7: new_u_t2 = st.selectbox("Unit", unit_options, index=2, key="ut2")
                with c8: new_t2_qty = st.number_input("Min Qty", min_value=0, value=0, key="n_t2_q")
                with c9: new_t2_price = st.number_input("Rate (₹)", min_value=0.0, value=0.0, step=0.50, format="%.2f", key="n_t2_p")
                
                st.markdown("---")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    new_free_delivery = st.selectbox("Delivery", ["Free Delivery", "Extra Courier Charge"])
                with col_f2:
                    new_in_stock = st.checkbox("✅ Product is currently in stock?", value=True)
                
                if st.session_state.seller_logged_in:
                    st.info(f"🏪 Your Brand/Seller Name: **{st.session_state.seller_logged_in}**")
                    new_seller_name = st.session_state.seller_logged_in
                else:
                    new_seller_name = st.text_input("Seller/Brand Name (Leave blank to hide)")
                
                existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
                cat_options = ["Create New Category..."] + existing_cats
                selected_cat = st.selectbox("Select Category (Box)", cat_options)
                if selected_cat == "Create New Category...":
                    final_cat = st.text_input("Enter New Category Name (Emojis allowed 👕👟)")
                else:
                    final_cat = selected_cat
                
                uploaded_imgs = st.file_uploader("Upload Photos (Max 3)", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="add_imgs")
                submit_btn = st.form_submit_button("Save Product")
                
                if submit_btn and new_id and new_name and uploaded_imgs and final_cat:
                    if len(uploaded_imgs) > 3: st.error("⚠️ Please select max 3 photos.")
                    else:
                        with st.spinner("Saving..."):
                            image_paths = []
                            for img in uploaded_imgs:
                                compressed_bytes, pil_img = compress_image(img.getvalue())
                                img_url = upload_image_to_imgbb(compressed_bytes)
                                if img_url: image_paths.append(img_url)
                            
                            final_path_str = "|".join(image_paths)
                            is_free = True if new_free_delivery == "Free Delivery" else False
                            seller_val = new_seller_name.strip() if new_seller_name else ""
                            
                            data = {
                                "ID": new_id, "Name": new_name, 
                                "Retail_Qty": new_retail_qty, "Price": new_online_price, "Cash_Price": new_cash_price,
                                "Tier1_Price": new_t1_price, "Tier1_Qty": new_t1_qty, 
                                "Tier2_Price": new_t2_price, "Tier2_Qty": new_t2_qty,
                                "Category": final_cat, "Image_Path": final_path_str,
                                "Free_Delivery": is_free, "Seller_Name": seller_val, "In_Stock": new_in_stock,
                                "Unit_Base": new_u_base, "Unit_T1": new_u_t1, "Unit_T2": new_u_t2,
                                "Offer_Name": new_offer_name.strip(), "Discount_Percent": new_discount
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
                    
            st.markdown("---")
            st.subheader("📜 Trust Certificates (GST, Udyog Aadhaar, ISO)")
            st.info("Upload up to 3 certificates (GST, Udyog Aadhaar, ISO/ISI) to be displayed at the top for customer trust.")
            
            c_cert1, c_cert2, c_cert3 = st.columns(3)
            with c_cert1:
                st.markdown("**1. GST Certificate**")
                if current_config.get("cert1_url"):
                    st.image(current_config["cert1_url"], width=100)
                    if st.button("❌ Remove GST", key="rm_c1"):
                        current_config["cert1_url"] = ""
                        save_config(current_config)
                        st.rerun()
                else:
                    new_c1 = st.file_uploader("Upload GST", type=["jpg", "png", "jpeg"], key="up_c1")
                    if st.button("Save GST", key="sv_c1") and new_c1:
                        c_bytes, _ = compress_image(new_c1.getvalue())
                        c_url = upload_image_to_imgbb(c_bytes)
                        if c_url:
                            current_config["cert1_url"] = c_url
                            save_config(current_config)
                            st.rerun()

            with c_cert2:
                st.markdown("**2. Udyog Aadhaar**")
                if current_config.get("cert2_url"):
                    st.image(current_config["cert2_url"], width=100)
                    if st.button("❌ Remove Aadhaar", key="rm_c2"):
                        current_config["cert2_url"] = ""
                        save_config(current_config)
                        st.rerun()
                else:
                    new_c2 = st.file_uploader("Upload Aadhaar", type=["jpg", "png", "jpeg"], key="up_c2")
                    if st.button("Save Aadhaar", key="sv_c2") and new_c2:
                        c_bytes, _ = compress_image(new_c2.getvalue())
                        c_url = upload_image_to_imgbb(c_bytes)
                        if c_url:
                            current_config["cert2_url"] = c_url
                            save_config(current_config)
                            st.rerun()

            with c_cert3:
                st.markdown("**3. ISO/ISI Certificate**")
                if current_config.get("cert3_url"):
                    st.image(current_config["cert3_url"], width=100)
                    if st.button("❌ Remove ISO", key="rm_c3"):
                        current_config["cert3_url"] = ""
                        save_config(current_config)
                        st.rerun()
                else:
                    new_c3 = st.file_uploader("Upload ISO/ISI", type=["jpg", "png", "jpeg"], key="up_c3")
                    if st.button("Save ISO", key="sv_c3") and new_c3:
                        c_bytes, _ = compress_image(new_c3.getvalue())
                        c_url = upload_image_to_imgbb(c_bytes)
                        if c_url:
                            current_config["cert3_url"] = c_url
                            save_config(current_config)
                            st.rerun()
        
        with tab_settings:
            st.subheader("🤖 Telegram Bot Settings")
            col_tg1, col_tg2 = st.columns(2)
            with col_tg1:
                new_tg_token = st.text_input("Telegram Bot Token", value=current_config.get("telegram_token", ""))
            with col_tg2:
                new_tg_chat = st.text_input("Telegram Chat ID", value=current_config.get("telegram_chat_id", ""))
            
            st.markdown("---")
            st.subheader("👥 Seller Management")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                new_s_name = st.text_input("New Seller Brand Name")
            with col_s2:
                new_s_phone = st.text_input("Seller WhatsApp")
            with col_s3:
                new_s_token = st.text_input("Create Password/Token")
                
            if st.button("➕ Add Seller"):
                if new_s_name and new_s_token:
                    current_config["sellers"][new_s_token] = {"name": new_s_name, "phone": new_s_phone}
                    save_config(current_config)
                    st.success(f"✅ Added Seller: {new_s_name}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ Please fill Brand Name and Token.")
            
            if current_config.get("sellers"):
                st.markdown("**Current Active Sellers:**")
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
                            st.success(f"🚫 {s_name}'s account has been closed!")
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
            
            # --- CATEGORY IMAGES UPLOAD SECTION ---
            st.markdown("---")
            st.subheader("🖼️ Category Photos")
            st.info("Upload custom photos/icons to display above each category box on the home page.")
            
            cat_images_dict = load_category_images()
            cats_list_for_img = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
            
            if cats_list_for_img:
                col_ci1, col_ci2 = st.columns(2)
                with col_ci1:
                    sel_cat_for_img = st.selectbox("Select Category", cats_list_for_img)
                    if sel_cat_for_img in cat_images_dict:
                        st.image(cat_images_dict[sel_cat_for_img], width=100)
                        if st.button("❌ Remove Photo", key="rm_cat_img"):
                            del cat_images_dict[sel_cat_for_img]
                            db.collection('settings').document('category_images').set(cat_images_dict)
                            load_category_images.clear()
                            st.rerun()
                
                with col_ci2:
                    new_cat_img = st.file_uploader(f"Upload Photo for '{sel_cat_for_img}'", type=["jpg", "png", "jpeg"], key="up_cat_img")
                    if st.button("Save Category Photo") and new_cat_img:
                        with st.spinner("Uploading..."):
                            c_bytes, _ = compress_image(new_cat_img.getvalue())
                            c_url = upload_image_to_imgbb(c_bytes)
                            if c_url:
                                cat_images_dict[sel_cat_for_img] = c_url
                                db.collection('settings').document('category_images').set(cat_images_dict)
                                load_category_images.clear()
                                st.success("✅ Photo Saved!")
                                time.sleep(1)
                                st.rerun()
            else:
                st.warning("Please add some products to create categories first.")
            # ----------------------------------------

            st.markdown("---")
            st.subheader("🎨 App Background Color (Live Preview)")
            
            old_color = current_config.get("bg_color", "#f4f6f9")
            new_bg_color = st.color_picker("Click here and use the slider to choose your favorite background color:", value=old_color)
            
            if new_bg_color != old_color:
                st.markdown(f"""
                <style>
                .stApp {{ background-color: {new_bg_color} !important; }}
                </style>
                """, unsafe_allow_html=True)

            if st.button("⚙️ Save All Settings"):
                current_config["admin_whatsapp"] = new_wa
                current_config["admin_gst"] = new_admin_gst
                current_config["free_delivery_tag"] = show_free_delivery
                current_config["phonepe_upi"] = new_phonepe
                current_config["paytm_upi"] = new_paytm
                current_config["gpay_upi"] = new_gpay
                current_config["bhim_upi"] = new_bhim
                current_config["telegram_token"] = new_tg_token
                current_config["telegram_chat_id"] = new_tg_chat
                current_config["bg_color"] = new_bg_color
                
                save_config(current_config)
                st.success("✅ Saved!")
                time.sleep(1)
                st.rerun()

            st.markdown("---")
            st.subheader("📦 Bulk Move / Rename Categories")
            cats_list = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
            if cats_list:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    b_old_cat = st.selectbox("Old Category (To Move)", cats_list)
                with col_b2:
                    b_new_cat_choice = st.selectbox("Move To", cats_list + ["Create New..."])
                    if b_new_cat_choice == "Create New...":
                        b_new_cat = st.text_input("Type new name/emoji:", value=b_old_cat)
                    else:
                        b_new_cat = b_new_cat_choice

                if st.button("🚀 Move / Update All Products", type="primary"):
                    if b_new_cat:
                        with st.spinner("Moving..."):
                            prods_to_move = products_df[products_df['Category'] == b_old_cat]
                            batch = db.batch()
                            for idx, row in prods_to_move.iterrows():
                                doc_ref = db.collection('products').document(str(row['ID']))
                                batch.update(doc_ref, {"Category": b_new_cat.strip()})
                            batch.commit()
                            load_products.clear()
                            st.success(f"✅ All products successfully moved to '{b_new_cat}'!")
                            time.sleep(2)
                            st.rerun()

        with tab_ledger:
            st.subheader("📒 Smart Cloud Ledger")
            with st.expander("➕ Add New Entry", expanded=False):
                with st.form("firebase_ledger_entry", clear_on_submit=True):
                    col_l1, col_l2 = st.columns(2)
                    with col_l1:
                        ledger_customer = st.text_input("Customer Name*").strip().upper()
                        ledger_amount = st.number_input("Amount (₹)*", min_value=0.0, step=100.0)
                    with col_l2:
                        ledger_status = st.selectbox("Select Category", ["Bill (To Receive)", "Advance (Received)"])
                        ledger_note = st.text_input("Note (e.g., Cash from shop, Old balance)")
                        
                    ledger_date = st.date_input("Date", datetime.datetime.today())
                    save_ledger_btn = st.form_submit_button("Save Entry 💾")
                    
                    if save_ledger_btn and ledger_customer and ledger_amount > 0:
                        new_entry = {
                            "Date": ledger_date.strftime("%Y-%m-%d"), 
                            "Type": "Bill" if "Bill" in ledger_status else "Advance", 
                            "Amount": ledger_amount, 
                            "Note": ledger_note,
                            "Timestamp": firestore.SERVER_TIMESTAMP
                        }
                        db.collection('ledgers').document(ledger_customer).set({"active": True}, merge=True)
                        db.collection('ledgers').document(ledger_customer).collection('transactions').add(new_entry)
                        load_ledger_data.clear()
                        st.success(f"✅ Entry saved for {ledger_customer}!")
                        time.sleep(1)
                        st.rerun()

            st.markdown("---")
            st.markdown("### 👥 All Customer Ledgers")
            all_ledgers = load_ledger_data()
            if not all_ledgers:
                st.warning("ℹ️ No customer ledger records found.")
            else:
                for cust_name, df_ledger in all_ledgers.items():
                    with st.expander(f"👤 {cust_name}"):
                        total_bill = df_ledger[df_ledger["Type"] == "Bill"]["Amount"].sum()
                        total_advance = df_ledger[df_ledger["Type"] == "Advance"]["Amount"].sum()
                        net_balance = total_bill - total_advance
                        
                        lc1, lc2, lc3 = st.columns(3)
                        lc1.metric("Total Bill (To Receive)", f"₹ {total_bill:,.2f}")
                        lc2.metric("Total Advance (Received)", f"₹ {total_advance:,.2f}")
                        
                        if net_balance > 0: lc3.metric("🔴 Balance Due", f"₹ {net_balance:,.2f}")
                        elif net_balance < 0: lc3.metric("🟢 Extra Advance", f"₹ {abs(net_balance):,.2f}")
                        else: lc3.metric("⚪ Settled", "₹ 0.00")

                        display_df = df_ledger.drop(columns=['doc_id', 'Timestamp'], errors='ignore')
                        display_df['Delete'] = False 
                        
                        edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, key=f"ed_{cust_name}")
                        
                        if st.button(f"💾 Save Account for {cust_name}", key=f"save_ed_{cust_name}", type="primary"):
                            with st.spinner("Updating on cloud..."):
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
                                            db.collection('ledgers').document(cust_name).set({"active": True}, merge=True)
                                            db.collection('ledgers').document(cust_name).collection('transactions').add(new_entry)

                                load_ledger_data.clear()
                                st.success("✅ Account successfully updated!")
                                time.sleep(1)
                                st.rerun()

            st.markdown("---")
            st.markdown("### 📂 Saved Invoices")
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
                                    label="📥 Download", 
                                    data=f.read(), 
                                    file_name=item['filename'], 
                                    mime="application/pdf", 
                                    key=f"dl_pdf_{item['filename']}",
                                    use_container_width=True
                                )
                        with col_btn2:
                            if st.button("🗑️ Delete", key=f"del_pdf_{item['filename']}", type="primary"):
                                try:
                                    os.remove(f"{INVOICE_FOLDER}/{item['filename']}")
                                    st.success("✅ Bill deleted!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error("⚠️ Error deleting bill.")

    st.markdown("---")

search_query = st.text_input("🔍 Search "), "")

c1_url = current_config.get("cert1_url", "")
c2_url = current_config.get("cert2_url", "")
c3_url = current_config.get("cert3_url", "")

if c1_url or c2_url or c3_url:
    cert_html = '<div style="display: flex; justify-content: center; gap: 10px; align-items: center; margin-top: 5px; margin-bottom: 15px;">'
    cert_html += '<div style="font-size:12px; font-weight:bold; color:#2b6cb0;">🏆 Verified:</div>'
    if c1_url:
        cert_html += f'<img src="{c1_url}" style="height: 35px; width: auto; border: 1px solid #e2e8f0; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
    if c2_url:
        cert_html += f'<img src="{c2_url}" style="height: 35px; width: auto; border: 1px solid #e2e8f0; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
    if c3_url:
        cert_html += f'<img src="{c3_url}" style="height: 35px; width: auto; border: 1px solid #e2e8f0; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
    cert_html += '</div>'
    st.markdown(cert_html, unsafe_allow_html=True)


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
    html_code += '<div style="text-align:center; font-size:12px; color:gray; margin-top:-5px; margin-bottom:10px;">Click photo to zoom 🔍</div>'
    st.markdown(html_code, unsafe_allow_html=True)
    return paths

def show_product_card(row, idx, prefix):
    prefix_idx = f"{prefix}_{idx}"
    p_id = str(row.get('ID', prefix_idx)) 

    disc_pct = safe_float(row.get('Discount_Percent'), 0.0)
    offer_nm = str(row.get('Offer_Name', '')).strip()

    retail_qty = safe_int(row.get('Retail_Qty'), 1)
    retail_price = safe_float(row.get('Price'), 0.0)
    cash_price = safe_float(row.get('Cash_Price'), retail_price)
    
    t1_qty_default = safe_int(row.get('Wholesale_Qty'), 1)
    t1_qty = safe_int(row.get('Tier1_Qty'), t1_qty_default)
    t1_price_default = safe_float(row.get('Wholesale_Price'), retail_price)
    t1_price = safe_float(row.get('Tier1_Price'), t1_price_default)
    
    t2_qty = safe_int(row.get('Tier2_Qty'), 0)
    t2_price = safe_float(row.get('Tier2_Price'), t1_price)

    def apply_disc(price): return price - (price * disc_pct / 100) if price > 0 else 0.0
    
    net_retail = apply_disc(retail_price)
    net_cash = apply_disc(cash_price)
    net_t1 = apply_disc(t1_price)
    net_t2 = apply_disc(t2_price)
    
    u_base_full = str(row.get("Unit_Base", str(row.get("Unit_Type", "Pcs"))))
    u_base = u_base_full.split(" ")[0]
    u_t1_full = str(row.get("Unit_T1", u_base_full))
    u_t1 = u_t1_full.split(" ")[0]
    u_t2_full = str(row.get("Unit_T2", u_base_full))
    u_t2 = u_t2_full.split(" ")[0]
    
    image_path_str = str(row.get("Image_Path", ""))
    paths_temp = [p.strip() for p in image_path_str.split('|') if p.strip()]
    img_link_for_wa = ""
    if paths_temp:
        img_link_for_wa = paths_temp[0]
        if not img_link_for_wa.startswith("http"):
            img_link_for_wa = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link_for_wa.replace('\\', '/'), safe='/')}"

    show_wholesale = st.session_state.wholesale_mode

    share_text = f"⚡ *OURA PRODUCTS - {row.get('Name', '')}* ⚡\n\n"
    if disc_pct > 0:
        share_text += f"🎉 *{offer_nm} : FLAT {disc_pct}% OFF!* 🎉\n\n"
        
    share_text += f"📦 *Rates (After Discount):*\n"
    if show_wholesale:
        if t2_qty > 0 and t2_price > 0: share_text += f"🔹 {t2_qty}+ {u_t2}: ₹{net_t2:.2f} \n"
        if t1_qty > 0 and t1_price > 0: share_text += f"🔹 {t1_qty}+ {u_t1}: ₹{net_t1:.2f} \n"
    share_text += f"🔹 {retail_qty}+ {u_base}: Cash ₹{net_cash:.2f} | Online ₹{net_retail:.2f}\n\n"
    
    cat_url = urllib.parse.quote(str(row.get('Category', '')))
    app_link = f"https://ouraindia.streamlit.app/?cat={cat_url}"
    
    share_text += f"🛒 *Book Order:* {app_link}\n"
    if img_link_for_wa:
        share_text += f"📷 *Product Photo:* {img_link_for_wa}"
    wa_link = f"https://wa.me/?text={urllib.parse.quote(share_text)}"

    with st.container(border=True):
        is_in_stock = row.get("In_Stock", True)
        
        if disc_pct > 0:
            st.markdown(f'<div class="offer-tag">✨ {offer_nm} : {disc_pct}% OFF! ✨</div>', unsafe_allow_html=True)
            
        all_paths = show_swipe_gallery(image_path_str, is_in_stock, wa_link, img_link_for_wa)
        
        st.write(f"**{row.get('Name', 'Unknown')}**")
        seller_val = row.get("Seller_Name")
        if pd.notna(seller_val) and str(seller_val).strip() != "":
            st.markdown(f"🏪 Brand: <span style='color:#E65100; font-weight:bold;'>{str(seller_val).strip()}</span>", unsafe_allow_html=True)
            
        show_fd = current_config.get("free_delivery_tag", True)
        val_fd = row.get("Free_Delivery")
        if pd.notna(val_fd) and str(val_fd).strip() != "":
            show_fd = str(val_fd).lower() in ['true', 'yes', '1']
            
        del_tag = "(Free Delivery)" if show_fd else "<span style='color:#d32f2f;font-size:11px;'>(+ Courier Charge)</span>"

        def get_price_html(orig, net, color, lbl):
            if disc_pct > 0:
                return f'<span style="color:{color}; font-size:12px;">{lbl} <del style="color:#999;">₹{orig}</del> <b style="font-size:15px;">₹{net:.2f}</b></span>'
            else:
                return f'<span style="color:{color}; font-size:14px; font-weight:bold;">{lbl} ₹{orig}</span>'

        cash_html = get_price_html(cash_price, net_cash, "#e65100", "💵 Cash:")
        online_html = get_price_html(retail_price, net_retail, "#2b6cb0", "💳 Online:")
        t1_html = get_price_html(t1_price, net_t1, "#d32f2f", "")
        t2_html = get_price_html(t2_price, net_t2, "#d32f2f", "")

        if retail_price <= 0:
            st.markdown(f"""
            <div style="background-color:#fff3cd; padding:10px; border-radius:8px; border:1px solid #ffeeba; margin-bottom:10px; text-align:center;">
                <span style="color:#856404; font-size:15px; font-weight:bold;">🚨 Contact for Price</span>
            </div>
            """, unsafe_allow_html=True)
            if is_in_stock:
                ask_qty = st.number_input(f"How many {u_base} required?", min_value=1, value=1, key=f"ask_q_{prefix_idx}")
                admin_num = current_config.get("admin_whatsapp", "919891587437")
                wa_msg = urllib.parse.quote(f"Hello Oura Products,\nI need {ask_qty} {u_base} of *{row.get('Name', 'this product')}*. Please quote your best rate.")
                wa_btn_link = f"https://wa.me/{admin_num}?text={wa_msg}"
                st.markdown(f'<a href="{wa_btn_link}" target="_blank" style="display:block; text-align:center; background-color:#25D366; color:white; padding:10px; border-radius:8px; text-decoration:none; font-weight:bold; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">💬 Ask Rate on WhatsApp for {ask_qty} {u_base}</a>', unsafe_allow_html=True)
        else:
            if show_wholesale and t2_qty > 0 and t2_price > 0: 
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; background-color:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px;">
                    <div style="text-align:center; flex:1;"><b>{retail_qty}+ {u_base}</b><br>{cash_html}<br>{online_html}</div>
                    <div style="border-left:1px solid #ccc; height:30px;"></div>
                    <div style="text-align:center; flex:1;"><b>{t1_qty}+ {u_t1}</b><br>{t1_html}</div>
                    <div style="border-left:1px solid #ccc; height:30px;"></div>
                    <div style="text-align:center; flex:1;"><b>{t2_qty}+ {u_t2}</b><br>{t2_html}</div>
                </div>
                <div style="text-align:center; font-size:12px; margin-top:-5px; margin-bottom:10px;">🛵 {del_tag}</div>
                """, unsafe_allow_html=True)
            elif show_wholesale and t1_qty > 0 and t1_price > 0: 
                st.markdown(f"""
                <div style="display:flex; justify-content:space-around; align-items:center; background-color:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px;">
                    <div style="text-align:center; flex:1;"><b>{retail_qty}+ {u_base}</b><br>{cash_html}<br>{online_html}</div>
                    <div style="border-left:1px solid #ccc; height:30px;"></div>
                    <div style="text-align:center; flex:1;"><b>{t1_qty}+ {u_t1}</b><br>{t1_html}</div>
                </div>
                <div style="text-align:center; font-size:12px; margin-top:-5px; margin-bottom:10px;">🛵 {del_tag}</div>
                """, unsafe_allow_html=True)
            else: 
                st.markdown(f"""
                <div style="background-color:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px; text-align:center;">
                    <b>{retail_qty}+ {u_base} Rate:</b><br>
                    {cash_html} | {online_html} <br>
                    <span style="font-size:12px;">🛵 {del_tag}</span>
                </div>
                """, unsafe_allow_html=True)
                
            if is_in_stock:
                opts = {}
                if retail_price > 0:
                    lbl_on = f"{retail_qty} {u_base} (💳 Online: ₹{net_retail:.2f})" if disc_pct > 0 else f"{retail_qty} {u_base} (💳 Online Payment - ₹{retail_price})"
                    opts[lbl_on] = {"price": retail_price, "unit": u_base, "min_q": retail_qty, "type": "Online"}
                if cash_price > 0:
                    lbl_ca = f"{retail_qty} {u_base} (💵 Cash: ₹{net_cash:.2f})" if disc_pct > 0 else f"{retail_qty} {u_base} (💵 Cash / Offline - ₹{cash_price})"
                    opts[lbl_ca] = {"price": cash_price, "unit": u_base, "min_q": retail_qty, "type": "Cash"}
                
                if show_wholesale:
                    if t1_qty > 0 and t1_price > 0:
                        lbl_t1 = f"{t1_qty} {u_t1} (Wholesale: ₹{net_t1:.2f} / {u_t1})" if disc_pct > 0 else f"{t1_qty} {u_t1} (Wholesale: ₹{t1_price} / {u_t1})"
                        opts[lbl_t1] = {"price": t1_price, "unit": u_t1, "min_q": t1_qty, "type": "Wholesale"}
                    if t2_qty > 0 and t2_price > 0:
                        lbl_t2 = f"{t2_qty} {u_t2} (Super Bulk: ₹{net_t2:.2f} / {u_t2})" if disc_pct > 0 else f"{t2_qty} {u_t2} (Super Bulk: ₹{t2_price} / {u_t2})"
                        opts[lbl_t2] = {"price": t2_price, "unit": u_t2, "min_q": t2_qty, "type": "SuperBulk"}
                    
                selected_opt = st.selectbox("Select Payment Mode & Package:", list(opts.keys()), key=f"sel_{prefix_idx}")
                buy_price = opts[selected_opt]["price"] 
                buy_unit = opts[selected_opt]["unit"]
                min_q = opts[selected_opt]["min_q"]
                buy_type = opts[selected_opt]["type"]
                
                qty = st.number_input(f"Quantity ({buy_unit})", min_value=min_q, value=min_q, key=f"q_{prefix_idx}")
                
                if st.button("🛒 Add to Cart", key=f"b_{prefix_idx}"):
                    cart_key = f"{p_id}|{buy_unit}|{buy_price}|{buy_type}"
                    
                    if cart_key in st.session_state.cart:
                        st.session_state.cart[cart_key]["qty"] += qty
                    else:
                        base_nm = row.get('Name', 'Item')
                        final_nm = f"{base_nm} ({buy_type})" if buy_type in ["Online", "Cash"] else base_nm
                        st.session_state.cart[cart_key] = {
                            "name": final_nm, 
                            "price": buy_price, 
                            "qty": qty, 
                            "img_link": img_link_for_wa,
                            "seller": str(seller_val).strip() if pd.notna(seller_val) else "",
                            "unit": buy_unit,
                            "discount_pct": disc_pct,
                            "offer_name": offer_nm
                        }
                    save_cart_to_url()
                    st.success("Added to Cart! 🛒")
            else:
                st.markdown("<div style='background-color:#ffebee; color:#c62828; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border:1px solid #ef9a9a; margin-top:10px;'>🚫 Out of Stock</div>", unsafe_allow_html=True)
            
        can_edit = False
        if st.session_state.admin_logged_in: can_edit = True
        elif st.session_state.seller_logged_in and st.session_state.seller_logged_in == str(seller_val).strip(): can_edit = True
            
        can_market = False
        if st.session_state.admin_logged_in or st.session_state.seller_logged_in: can_market = True
            
        if can_edit or can_market: st.markdown("---")

        if can_market:
            with st.expander("📘 Create Facebook / Instagram Post"):
                fb_text_copy = share_text + "\n#OuraProducts #WholesaleMarket #DelhiWholesale #Electronics"
                st.info("💡 **Tip:** 1. Click '📥 Photo' above to save it. \n2. Copy the text below. \n3. Paste on Facebook!")
                st.text_area("Text for Facebook Post:", value=fb_text_copy, height=200, key=f"fb_txt_{prefix_idx}")

        if can_edit:
            col_t1, col_t2, col_t3, col_t4 = st.columns([3, 2, 4, 3])
            with col_t1: st.markdown("**Stock:**")
            with col_t2: st.toggle("✅" if is_in_stock else "🚫", value=is_in_stock, key=f"t_stk_{prefix_idx}", on_change=toggle_stock_callback, args=(str(row['ID']), f"t_stk_{prefix_idx}"))
            with col_t3: st.markdown("**Delivery:**")
            with col_t4: st.toggle("🆓" if show_fd else "🚚", value=show_fd, key=f"t_fd_{prefix_idx}", on_change=toggle_fd_callback, args=(str(row['ID']), f"t_fd_{prefix_idx}"))

        if can_edit:
            with st.expander("✏️ Edit & Move Product"):
                with st.form(f"edit_form_{prefix_idx}"):
                    if st.session_state.admin_logged_in: e_name = st.text_input("Name", value=str(row.get("Name", "")), key=f"enm_{prefix_idx}")
                    else:
                        st.text_input("Name - Read Only", value=str(row.get("Name", "")), disabled=True, key=f"enm_ro_{prefix_idx}")
                        e_name = str(row.get("Name", ""))
                    
                    st.markdown("**🔄 Move Product to another Category:**")
                    all_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
                    current_cat = str(row.get("Category", ""))
                    
                    if all_cats:
                        cat_idx = all_cats.index(current_cat) if current_cat in all_cats else 0
                        e_cat_choice = st.selectbox("Category", all_cats + ["Create New..."], index=cat_idx, key=f"ec_{prefix_idx}")
                        if e_cat_choice == "Create New...":
                            e_cat = st.text_input("Type new Category Name", value=current_cat, key=f"ec_text_{prefix_idx}")
                        else:
                            e_cat = e_cat_choice
                    else:
                        e_cat = st.text_input("Type new Category Name", value=current_cat, key=f"ec_text_alt_{prefix_idx}")
                        
                    st.markdown("---")
                    
                    st.markdown("**🎁 Edit Offers**")
                    col_eo1, col_eo2 = st.columns(2)
                    with col_eo1: e_off_name = st.text_input("Offer Name", value=str(row.get("Offer_Name", "")), key=f"eoff_{prefix_idx}")
                    with col_eo2: e_off_pct = st.number_input("Discount %", value=safe_float(row.get("Discount_Percent"), 0.0), key=f"eoffp_{prefix_idx}")
                    
                    st.markdown("**💰 Pricing Tiers**")
                    unit_opts = ["Pcs", "Dozen", "Box", "Set"]
                    
                    idx_b = next((i for i, opt in enumerate(unit_opts) if u_base in opt), 0)
                    idx_t1 = next((i for i, opt in enumerate(unit_opts) if u_t1 in opt), 0)
                    idx_t2 = next((i for i, opt in enumerate(unit_opts) if u_t2 in opt), 0)

                    st.markdown("**Tier 1 (Base):**")
                    c_e01, c_e02, c_e03, c_e04 = st.columns([1, 1, 1, 1])
                    with c_e01: e_u_base = st.selectbox("Unit", unit_opts, index=idx_b, key=f"eu_b_{prefix_idx}")
                    with c_e02: e_retail_qty = st.number_input("Min Qty", value=retail_qty, key=f"erq_{prefix_idx}")
                    with c_e03: e_online_price = st.number_input("💳 Online (₹)", value=float(retail_price), format="%.2f", step=0.50, key=f"ep_on_{prefix_idx}")
                    cash_val = safe_float(row.get('Cash_Price'), float(retail_price)) 
                    with c_e04: e_cash_price = st.number_input("💵 Cash (₹)", value=cash_val, format="%.2f", step=0.50, key=f"ep_ca_{prefix_idx}")
                    
                    st.markdown("**Tier 2 (Bulk):**")
                    c_e1, c_e2, c_e3 = st.columns([2, 1, 1])
                    with c_e1: e_u_t1 = st.selectbox("Unit", unit_opts, index=idx_t1, key=f"eu_t1_{prefix_idx}")
                    with c_e2: e_t1_qty = st.number_input("Min Qty", value=t1_qty, key=f"et1q_{prefix_idx}")
                    with c_e3: e_t1_price = st.number_input("Rate (₹)", value=float(t1_price), format="%.2f", step=0.50, key=f"et1p_{prefix_idx}")
                        
                    st.markdown("**Tier 3 (Super Bulk):**")
                    c_e4, c_e5, c_e6 = st.columns([2, 1, 1])
                    with c_e4: e_u_t2 = st.selectbox("Unit", unit_opts, index=idx_t2, key=f"eu_t2_{prefix_idx}")
                    with c_e5: e_t2_qty = st.number_input("Min Qty (0=off)", value=t2_qty, key=f"et2q_{prefix_idx}")
                    with c_e6: e_t2_price = st.number_input("Rate (₹)", value=float(t2_price), format="%.2f", step=0.50, key=f"et2p_{prefix_idx}")
                        
                    st.markdown("---")
                    e_fd = st.selectbox("Delivery Option", ["Free Delivery", "Extra Courier Charge"], index=0 if show_fd else 1, key=f"efd_{prefix_idx}")
                            
                    e_imgs = st.file_uploader("Upload New Photos (Optional)", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=f"e_img_up_{prefix_idx}")
                    update_btn = st.form_submit_button("✅ Update & Save")
                    
                if update_btn:
                    target_id = str(row['ID'])
                    is_free_val = True if e_fd == "Free Delivery" else False
                    update_dict = {
                        "Retail_Qty": e_retail_qty, "Price": e_online_price, "Cash_Price": e_cash_price,
                        "Tier1_Price": e_t1_price, "Tier1_Qty": e_t1_qty, 
                        "Tier2_Price": e_t2_price, "Tier2_Qty": e_t2_qty,
                        "Category": e_cat.strip(),
                        "Unit_Base": e_u_base, "Unit_T1": e_u_t1, "Unit_T2": e_u_t2,
                        "Free_Delivery": is_free_val,
                        "Offer_Name": e_off_name.strip(),
                        "Discount_Percent": e_off_pct
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
            if st.button("🗑️ Delete Product", key=f"del_p_{prefix_idx}"):
                db.collection('products').document(str(row['ID'])).delete()
                load_products.clear()
                st.rerun()

# --- MAIN PAGE: DISPLAY CATEGORIES OR SEARCH RESULTS ---
if products_df.empty:
    st.info("New products coming soon!")
else:
    if search_query:
        st.subheader(f"Search results for '{search_query}':")
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        if filtered_df.empty: st.warning("No product found with this name.")
        else:
            cols = st.columns(3)
            for idx, row in filtered_df.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "search")
    
    elif st.session_state.selected_category is None:
        st.subheader("🛍️ Categories")
        valid_categories = products_df['Category'].dropna().unique().tolist()
        
        if len(valid_categories) == 0: 
            st.write("No categories yet.")
        else:
            # --- FIXED 4-COLUMN GRID WITH PHOTOS ---
            st.markdown('<div id="hide-cats-marker"></div>', unsafe_allow_html=True)
            
            # 1. Render Buttons First (Using ID instead of Category Name for better stability)
            for idx, cat in enumerate(valid_categories):
                if st.button(f"HIDDEN_CAT_{idx}", key=f"hidden_cat_{idx}"):
                    st.session_state.selected_category = cat
                    st.query_params["cat"] = cat
                    save_cart_to_url()
                    st.rerun()
            
            # 2. Hide Buttons Function & Setup Click Event (OPTIMIZED FOR SPEED)
            js_code = """
            <script>
            const parentDoc = window.parent.document;
            
            function setupCategories() {
                // Hide Streamlit buttons
                const btns = parentDoc.querySelectorAll('button');
                btns.forEach(b => {
                    if(b.innerText && b.innerText.includes('HIDDEN_CAT_')) {
                        const container = b.closest('div[data-testid="stElementContainer"]');
                        if (container && container.style.display !== 'none') {
                            container.style.display = 'none';
                        }
                    }
                });

                // Attach clicks safely without intervals
                const cards = parentDoc.querySelectorAll('.cat-card:not(.click-ready)');
                cards.forEach(card => {
                    card.classList.add('click-ready');
                    card.addEventListener('click', function() {
                        const catIdx = this.getAttribute('data-cat-idx');
                        const targetText = 'HIDDEN_CAT_' + catIdx;
                        const allBtns = parentDoc.querySelectorAll('button');
                        for(let i = 0; i < allBtns.length; i++) {
                            if(allBtns[i].innerText && allBtns[i].innerText.includes(targetText)) {
                                allBtns[i].click();
                                break;
                            }
                        }
                    });
                });
            }

            setupCategories();
            setTimeout(setupCategories, 150);
            setTimeout(setupCategories, 500);
            setTimeout(setupCategories, 1000);
            </script>
            """
            st_components.html(js_code, height=0, width=0)
            
            # 3. Render 4-Column Grid
            cat_images = load_category_images()
            
            html_parts = []
            html_parts.append('<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 10px 0px;">')
            
            for idx, cat in enumerate(valid_categories):
                img_url = cat_images.get(cat, "https://img.icons8.com/color/96/000000/open-box.png")
                
                # --- UPDATED CARD DESIGN ---
                card = f'<div class="cat-card" data-cat-idx="{idx}" style="background: #ffffff; border-radius: 12px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; cursor: pointer; transition: transform 0.1s ease; display: flex; flex-direction: column; overflow: hidden; height: 100%;">'
                
                # loading="lazy" added for speed optimization
                card += f'<img src="{img_url}" loading="lazy" style="width: 100%; height: 75px; object-fit: cover; background-color: #f8f9fa; border-bottom: 1px solid #e2e8f0;">'
                
                card += f'<div style="padding: 8px 4px; flex-grow: 1; display: flex; align-items: center; justify-content: center;">'
                card += f'<span style="font-size: 11px; font-weight: 700; color: #1a202c; line-height: 1.2; word-wrap: break-word;">{cat}</span>'
                card += '</div></div>'
                
                html_parts.append(card)
                
            html_parts.append('</div>')
            
            st.markdown("\n".join(html_parts), unsafe_allow_html=True)
            # ---------------------------------------------------------------
            
    else:
        st.subheader(f"📂 {st.session_state.selected_category}")
        
        if st.button("🏠 All Categories", key="float_back_btn"):
            st.session_state.selected_category = None
            if "cat" in st.query_params: del st.query_params["cat"]
            save_cart_to_url()
            st.rerun()
            
        float_js = """
        <script>
        const parentWin = window.parent;
        const parentDoc = window.parent.document;
        
        const buttons = parentDoc.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.innerText && btn.innerText.includes('All Categories')) {
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

        if (!parentWin.ouraMobileBackConfigured) {
            parentWin.ouraMobileBackConfigured = true;
            parentWin.addEventListener('popstate', function(event) {
                const btns = parentWin.document.querySelectorAll('button');
                btns.forEach(b => {
                    if (b.innerText && (b.innerText.includes('All Categories'))) {
                        b.click(); 
                    }
                });
            });
        }

        if (!parentWin.history.state || parentWin.history.state.oura !== 'in_category') {
            parentWin.history.pushState({ oura: 'in_category' }, "Category", parentWin.location.href);
        }
        </script>
        """
        st_components.html(float_js, height=0, width=0)

        cat_products = products_df[products_df['Category'] == st.session_state.selected_category]
        if cat_products.empty: st.write("No products in this category yet.")
        else:
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "cat_view")

st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True) 

st.markdown('<div id="cart-section-anchor" style="position:relative; top:-50px;"></div>', unsafe_allow_html=True)

st.markdown("---")
st.header("🛒")

st.session_state.cart_total_savings = 0.0

if st.session_state.cart:
    total = 0
    total_savings = 0
    count = 1
    
    for k, item in list(st.session_state.cart.items()):
        orig_p = item['price']
        d_pct = item.get('discount_pct', 0.0)
        d_name = item.get('offer_name', '')
        
        net_p = orig_p - (orig_p * d_pct / 100)
        subtotal = net_p * item['qty']
        savings = (orig_p - net_p) * item['qty']
        
        total += subtotal
        total_savings += savings
        
        col_img, col_details = st.columns([2, 8])
        with col_img:
            if item.get('img_link'): st.image(item['img_link'], use_container_width=True)
            else: st.write("📷")
        with col_details:
            st.write(f"✔️ **{item['name']}**")
            c1, c2 = st.columns([8, 2])
            
            unit_display = item.get('unit', 'Pcs')
            with c1: 
                if d_pct > 0:
                    st.markdown(f"**Qty:** {item['qty']} {unit_display} x <del style='color:gray;'>₹{orig_p:.2f}</del> ₹{net_p:.2f} = **₹{subtotal:.2f}** <br><span style='color:green; font-weight:bold;'>🎉 Saved ₹{savings:.2f} ({d_name})</span>", unsafe_allow_html=True)
                else:
                    st.write(f"Qty: {item['qty']} {unit_display} x ₹{orig_p:.2f} = **₹{subtotal:.2f}**")
            with c2:
                if st.button("❌", key=f"del_item_{k}"):
                    del st.session_state.cart[k]
                    save_cart_to_url()
                    st.rerun()
        st.markdown("---")
        count += 1
    
    st.session_state.cart_total_savings = total_savings
    
    st.subheader(f"Total Amount: ₹{total:.2f}")
    if total_savings > 0:
        st.markdown(f"<h4 style='color:green;'>🎉 Savings: ₹{total_savings:.2f}</h4>", unsafe_allow_html=True)
    
    available_upis = {}
    if current_config.get("phonepe_upi"): available_upis["PhonePe"] = {"id": current_config["phonepe_upi"], "color": "#5e35b1", "icon": "🟣"}
    if current_config.get("paytm_upi"): available_upis["Paytm"] = {"id": current_config["paytm_upi"], "color": "#00baf2", "icon": "🔵"}
    if current_config.get("gpay_upi"): available_upis["Google Pay"] = {"id": current_config["gpay_upi"], "color": "#1a73e8", "icon": "🔴"}
    if current_config.get("bhim_upi"): available_upis["BHIM"] = {"id": current_config["bhim_upi"], "color": "#ff7043", "icon": "🟠"}

    if available_upis:
        st.markdown(f"### 💳  Online Payment")
        
        first_upi_id = list(available_upis.values())[0]["id"]
        merchant_name = urllib.parse.quote("Oura Products")
        pay_url = f"upi://pay?pa={first_upi_id}&pn={merchant_name}&am={total:.2f}&cu=INR"
        
        
        
        st.markdown(f'''
        <a href="{pay_url}" style="display:block; text-align:center; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color:white; padding:15px 20px; border-radius:12px; text-decoration:none; font-size:18px; font-weight:bold; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom:15px; transition: transform 0.2s;">
            ⚡ Pay UPI App ⚡
        </a>
        <div style="text-align:center; font-size:13px; color:gray; margin-top:-10px; margin-bottom:15px;">
            Opens GPay, PhonePe, Paytm automatically
        </div>
        ''', unsafe_allow_html=True)

        with st.expander("💻 Scanning QR "):
            qr_tabs = st.tabs(list(available_upis.keys()))
            for idx, (name, data) in enumerate(available_upis.items()):
                with qr_tabs[idx]:
                    qr_data = f"upi://pay?pa={data['id']}&pn=Oura_Products&am={total:.2f}&cu=INR"
                    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(qr_data)}", width=150)
                    st.success(f"**{name} UPI ID:** `{data['id']}`")

    st.markdown("---")
    
    
    with st.form("billing_form"):
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            cust_name = st.text_input("Your Name / Shop Name")
            
            cust_mobile = st.text_input("Mobile Number (10 digits)*")
            cust_address = st.text_area("Full Address (with City, Pincode)")
        with col_d2:
            bill_date = st.date_input("Invoice Date", datetime.date.today())
            gst_choice = st.selectbox("Select Bill Type:", ["Without GST (Estimate)", "GST @ 5%", "GST @ 12%", "GST @ 18%", "GST @ 28%"])
            
            gst_percent = 0
            if "5%" in gst_choice: gst_percent = 5
            elif "12%" in gst_choice: gst_percent = 12
            elif "18%" in gst_choice: gst_percent = 18
            elif "28%" in gst_choice: gst_percent = 28
            
            cust_gst = st.text_input("Customer GST Number (15 chars)") if gst_percent > 0 else ""
            shipping_cost = st.number_input("🚚 Courier / Packing Charge (₹)", min_value=0.0, value=0.0, step=10.0, format="%.2f")
            
            amount_paid = st.number_input("💸 Amount Paid Now (₹)", min_value=0.0, value=0.0, step=10.0, format="%.2f")

        submit_billing = st.form_submit_button("✅ Prepare Bill & Confirm Order")

    mobile_validation_js = """
    <script>
    const parentDoc = window.parent.document;
    
    function applyMobileValidation() {
        const labels = parentDoc.querySelectorAll('label');
        let mobileInput = null;
        let formContainer = null;
        
        labels.forEach(label => {
            if (label.innerText.includes('Mobile Number')) {
                const container = label.closest('div[data-testid="stTextInput"]');
                if (container) {
                    mobileInput = container.querySelector('input');
                    formContainer = label.closest('div[data-testid="stForm"]');
                }
            }
        });

        if (mobileInput && formContainer) {
            let submitBtn = formContainer.querySelector('button[data-testid="baseButton-formSubmit"]');
            if (!submitBtn) {
                const buttons = formContainer.querySelectorAll('button');
                buttons.forEach(b => {
                    if (b.innerText.includes('Prepare Bill')) {
                        submitBtn = b;
                    }
                });
            }
            
            function checkValid() {
                const val = mobileInput.value.trim();
                const isValid = /^\\d{10}$/.test(val); 
                
                if (!isValid) {
                    mobileInput.style.border = '2px solid #ff4b4b'; 
                    mobileInput.style.backgroundColor = '#fff0f0';
                    mobileInput.style.boxShadow = '0 0 5px rgba(255, 75, 75, 0.5)';
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        submitBtn.style.opacity = '0.4';
                        submitBtn.style.pointerEvents = 'none'; 
                    }
                } else {
                    mobileInput.style.border = '2px solid #28a745'; 
                    mobileInput.style.backgroundColor = 'white';
                    mobileInput.style.boxShadow = 'none';
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.style.opacity = '1';
                        submitBtn.style.pointerEvents = 'auto'; 
                    }
                }
            }
            
            if (!mobileInput.dataset.valAttached) {
                mobileInput.addEventListener('input', checkValid);
                mobileInput.dataset.valAttached = 'true';
            }
            checkValid();
        }
    }
    
    setTimeout(applyMobileValidation, 1000);
    const observer = new MutationObserver(applyMobileValidation);
    observer.observe(parentDoc.body, { childList: true, subtree: true });
    </script>
    """
    st_components.html(mobile_validation_js, height=0, width=0)

    if submit_billing:
        is_valid = True
        
        if not cust_mobile or not cust_mobile.strip().isdigit() or len(cust_mobile.strip()) != 10:
            st.error("⚠️ Please enter a valid 10-digit mobile number.")
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
                    cust_gst, gst_percent, shipping_cost, auto_last_balance, amount_paid, current_config, bill_date,
                    st.session_state.cart_total_savings
                )
                
                if safe_name:
                    safe_file_name = re.sub(r'[\\/*?:"<>|]', "", safe_name).replace(' ', '_')
                else:
                    safe_file_name = 'Cash'
                    
                date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                st.session_state.ready_filename = f"OURA_Bill_{safe_file_name}_{date_str}.pdf"
                st.session_state.ready_pdf = pdf_bytes

                if not os.path.exists(INVOICE_FOLDER):
                    os.makedirs(INVOICE_FOLDER)

                pdf_path = f"{INVOICE_FOLDER}/{st.session_state.ready_filename}"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                item_details_list = []
                whatsapp_items_text = ""
                taxable_amount = 0
                idx = 1
                for k, item in st.session_state.cart.items():
                    item_unit = item.get('unit', 'Pcs')
                    
                    orig_p = item['price']
                    d_pct = item.get('discount_pct', 0.0)
                    net_p = orig_p - (orig_p * d_pct / 100)
                    sub_amt = item['qty'] * net_p
                    
                    offer_txt = f" (Discount: {d_pct}%)" if d_pct > 0 else ""
                    
                    item_details_list.append(f"{item['name']} ({item['qty']} {item_unit})")
                    whatsapp_items_text += f"{idx}. {item['name']}{offer_txt}\n    Qty: {item['qty']} {item_unit} x ₹{net_p:.2f} = ₹{sub_amt:.2f}\n"
                    taxable_amount += sub_amt
                    idx += 1
                
                taxable_amount += shipping_cost
                gst_amt = (taxable_amount * gst_percent) / 100
                current_bill_total = taxable_amount + gst_amt 
                full_item_details = " | ".join(item_details_list)
                
                if safe_name:
                    batch = db.batch()
                    parent_ref = db.collection('ledgers').document(safe_name)
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
                    load_ledger_data.clear()

                msg = f"🛍️ *OURA PRODUCTS - NEW ORDER RECEIVED* 🛍️\n"
                msg += f"------------------------------------\n"
                msg += f"👤 *Customer:* {cust_name if cust_name else 'Walk-in Customer'}\n"
                msg += f"📞 *Mobile:* {cust_mobile if cust_mobile else 'N/A'}\n"
                if cust_address:
                    msg += f"📍 *Address:* {cust_address}\n"
                msg += f"------------------------------------\n"
                msg += f"📦 *Ordered Items:*\n\n{whatsapp_items_text}"
                msg += f"------------------------------------\n"
                if st.session_state.cart_total_savings > 0:
                    msg += f"🎉 *TOTAL SAVINGS:* ₹{st.session_state.cart_total_savings:.2f}\n"
                    msg += f"------------------------------------\n"
                    
                if shipping_cost > 0:
                    msg += f"🚚 *Courier Charge:* ₹{shipping_cost:.2f}\n"
                if gst_percent > 0:
                    msg += f"📊 *GST ({gst_percent}%):* ₹{gst_amt:.2f}\n"
                msg += f"💰 *Total Bill Amount:* ₹{current_bill_total:.2f}\n"
                
                if amount_paid > 0:
                    msg += f"\n✅ *Amount Paid Now:* ₹{amount_paid:.2f} 💸\n"
                    msg += f"🔴 *Net Balance Due:* ₹{current_bill_total - amount_paid:.2f}\n"
                else:
                    msg += f"\n❌ *No Advance Payment Received.* (₹0.00)\n"
                
                msg += f"------------------------------------\n"
                msg += f"📱 *Date:* {bill_date.strftime('%d-%m-%Y')}\n"
                
                st.session_state.ready_msg_for_admin = msg

                tg_token = current_config.get("telegram_token", "")
                tg_chat = current_config.get("telegram_chat_id", "")
                if tg_token and tg_chat:
                    send_telegram_alert(tg_token, tg_chat, st.session_state.ready_msg_for_admin, pdf_bytes, st.session_state.ready_filename)

                st.balloons()
                st.success(f"🎉 **Order Confirmed!** total bill **₹{current_bill_total:.2f}** ")
                
                admin_num = current_config.get("admin_whatsapp", "919891587437")
                wa_link_auto = f"https://wa.me/{admin_num}?text={urllib.parse.quote(st.session_state.ready_msg_for_admin)}"
                
                js_redirect = f"""
                <script>
                window.open("{wa_link_auto}", "_blank");
                </script>
                """
                st_components.html(js_redirect, height=0, width=0)

    if 'ready_pdf' in st.session_state:
        st.markdown("### 📥 Download")
        st.download_button(
            label="📄 Download Professional PDF Bill",
            data=st.session_state.ready_pdf,
            file_name=st.session_state.ready_filename,
            mime="application/pdf",
            use_container_width=True
        )

        st.markdown("### 📲  WhatsApp")
        admin_num = current_config.get("admin_whatsapp", "919891587437")
        wa_link = f"https://wa.me/{admin_num}?text={urllib.parse.quote(st.session_state.ready_msg_for_admin)}"
        st.markdown(f'''<a href="{wa_link}" target="_blank" style="display:block; text-align:center; background: #25D366; color:white; padding:15px; border-radius:10px; text-decoration:none; font-size:18px; font-weight:bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom:10px;">✅ Send Bill Details on WhatsApp</a>''', unsafe_allow_html=True)

    if st.button("🗑️ Empty Basket"):
        st.session_state.cart = {}
        if 'ready_pdf' in st.session_state: del st.session_state.ready_pdf
        if 'ready_msg_for_admin' in st.session_state: del st.session_state.ready_msg_for_admin
        save_cart_to_url()
        st.rerun()

admin_wa_number = current_config.get("admin_whatsapp", "919891587437")

if len(st.session_state.cart) > 0:
    unique_items_count = len(st.session_state.cart)
    
    basket_js = f"""
    <script>
    const parentDoc = window.parent.document;
    
    let existingWidget = parentDoc.getElementById('oura-basket-widget');
    if (existingWidget) {{
        existingWidget.remove();
    }}

    const widgetDiv = parentDoc.createElement('div');
    widgetDiv.id = 'oura-basket-widget';
    widgetDiv.innerHTML = `
    <style>
    #basket-float-btn {{
        position: fixed; 
        bottom: 130px; 
        right: 20px; 
        z-index: 9999999;
        width: 65px; 
        height: 65px; 
        background-color: #2b6cb0; 
        border-radius: 50%; 
        display: flex; 
        justify-content: center; 
        align-items: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        cursor: pointer;
        transition: transform 0.2s, background-color 0.2s;
    }}
    #basket-float-btn:hover {{
        transform: scale(1.05);
        background-color: #1a4a79;
    }}
    #basket-float-btn img {{
        width: 35px;
        height: 35px;
        filter: brightness(0) invert(1);
    }}
    .cart-badge {{
        position: absolute;
        top: -3px;
        right: -3px;
        background-color: #e53e3e; 
        color: white;
        border-radius: 50%;
        width: 26px;
        height: 26px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 14px;
        font-weight: bold;
        border: 2px solid white;
        font-family: sans-serif;
    }}
    </style>
    
    <div id="basket-float-btn">
        <span class="cart-badge">{unique_items_count}</span>
        <img src="https://img.icons8.com/ios-filled/50/000000/shopping-cart.png" alt="Cart"/>
    </div>
    `;
    parentDoc.body.appendChild(widgetDiv);

    parentDoc.getElementById('basket-float-btn').addEventListener('click', function() {{
        const target = parentDoc.getElementById('cart-section-anchor');
        if(target) {{
            target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }} else {{
            window.parent.scrollTo({{ top: parentDoc.body.scrollHeight, behavior: 'smooth' }});
        }}
    }});
    </script>
    """
    st_components.html(basket_js, height=0, width=0)
else:
    remove_js = """
    <script>
    const parentDoc = window.parent.document;
    let existingWidget = parentDoc.getElementById('oura-basket-widget');
    if (existingWidget) {
        existingWidget.remove();
    }
    </script>
    """
    st_components.html(remove_js, height=0, width=0)
