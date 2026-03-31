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

def dummy_delete_image(url):
    pass

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
        "admin_gst": "", 
        "phonepe_upi": "", "paytm_upi": "", "gpay_upi": "", "bhim_upi": "", "upi_id": "",
        "has_banner": False, "has_logo": False, "free_delivery_tag": True, "sellers": {},
        "banner_url": "", "logo_url": ""
    }

def save_config(config):
    db.collection('settings').document('config').set(config)

current_config = load_config()
if "sellers" not in current_config:
    current_config["sellers"] = {}

# 🚀 PDF जनरेट करने का अपडेटेड फंक्शन (Shipping & GST Bifurcation) 🚀
def generate_pdf_bill(cart, cust_name, cust_mobile, cust_address, cust_gst, gst_rate, shipping_charge, config):
    pdf = FPDF()
    pdf.add_page()
    
    # --- हैडर (कंपनी का नाम और एड्रेस) ---
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(43, 108, 176) # नीला रंग
    pdf.cell(0, 10, "OURA PRODUCTS", ln=True, align='C') 
    
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(100, 100, 100)
    admin_phone = config.get("admin_whatsapp", "9891587437")
    admin_gst_number = config.get("admin_gst", "").strip().upper()
    
    pdf.cell(0, 6, f"Delhi, India | Ph: +91 {admin_phone}", ln=True, align='C')
    
    if gst_rate > 0 and admin_gst_number:
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, f"GSTIN: {admin_gst_number}", ln=True, align='C')
        
    pdf.ln(5)
    
    # --- इनवॉइस की जानकारी ---
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 0, 0)
    title = "TAX INVOICE" if gst_rate > 0 else "ESTIMATE / QUOTATION"
    pdf.cell(0, 8, title, ln=True, align='C')
    pdf.ln(5)
    
    # --- ग्राहक की जानकारी ---
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(20, 6, "Billed To:")
    pdf.set_font("Arial", '', 10)
    c_name = cust_name if cust_name else "Cash/Walk-in Customer"
    pdf.cell(100, 6, c_name)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 6, "Invoice Date: ")
    pdf.set_font("Arial", '', 10)
    pdf.cell(40, 6, str(datetime.date.today()), ln=True)
    
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
    
    # --- टेबल का हैडर ---
    pdf.set_fill_color(230, 240, 255) 
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(15, 10, "S.No", border=1, align='C', fill=True)
    pdf.cell(90, 10, "Item Description", border=1, align='L', fill=True)
    pdf.cell(25, 10, "Qty", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Rate (Rs)", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Amount", border=1, align='C', fill=True)
    pdf.ln()
    
    # --- टेबल का डेटा ---
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
        
    # --- टोटल्स (Totals) ---
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(160, 10, "Subtotal", border=1, align='R')
    pdf.cell(30, 10, f"{subtotal:.2f}", border=1, align='R')
    pdf.ln()
    
    taxable_amount = subtotal
    
    # 🚀 शिपिंग चार्ज जोड़ना 🚀
    if shipping_charge > 0:
        pdf.cell(160, 10, "Add: Shipping / Courier Charges", border=1, align='R')
        pdf.cell(30, 10, f"{shipping_charge:.2f}", border=1, align='R')
        pdf.ln()
        taxable_amount += shipping_charge # GST शिपिंग के बाद वाले अमाउंट पर लगेगा
    
    gst_amt = 0
    # 🚀 GST का विभाजन (CGST/SGST vs IGST) 🚀
    if gst_rate > 0:
        admin_state = admin_gst_number[:2] if len(admin_gst_number) >= 2 else "07" # डिफ़ॉल्ट 07 (दिल्ली)
        cust_state = cust_gst[:2] if cust_gst and len(cust_gst) >= 2 else admin_state
        
        if admin_state != cust_state:
            # IGST (दूसरे राज्य के लिए)
            gst_amt = (taxable_amount * gst_rate) / 100
            pdf.cell(160, 10, f"Add: IGST @ {gst_rate}%", border=1, align='R')
            pdf.cell(30, 10, f"{gst_amt:.2f}", border=1, align='R')
            pdf.ln()
        else:
            # CGST & SGST (अपने राज्य के लिए)
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
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 255, 220) # हल्का हरा
    pdf.cell(160, 12, "GRAND TOTAL (Rs)", border=1, align='R', fill=True)
    pdf.cell(30, 12, f"{grand_total:.2f}", border=1, align='R', fill=True)
    pdf.ln(20)
    
    # --- फुटर (Footer) ---
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

            /* 🚀 Oura Categories Grid Fix 🚀 */
            div[data-testid="stContainer"]:has(.custom-cat-grid) div[data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 10px;
            }
            div[data-testid="stContainer"]:has(.custom-cat-grid) div[data-testid="column"] {
                min-width: calc(50% - 10px) !important; 
                flex: 1 1 calc(50% - 10px) !important;
                margin-bottom: 5px;
            }
            @media (min-width: 600px) {
                div[data-testid="stContainer"]:has(.custom-cat-grid) div[data-testid="column"] {
                    min-width: calc(25% - 10px) !important; 
                    flex: 1 1 calc(25% - 10px) !important;
                }
            }

            @media (max-width: 600px) {
                div[data-testid="stHorizontalBlock"] { display: flex !important; flex-wrap: wrap !important; }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)):not(:has(.custom-cat-grid)) > div[data-testid="column"] {
                    min-width: 23% !important; max-width: 25% !important; flex: 1 1 23% !important;
                    padding: 0 2px !important; margin-bottom: 5px;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(4)):not(:has(.custom-cat-grid)) div.stButton > button {
                    font-size: 11px !important; padding: 5px !important; min-height: 60px !important;
                    word-wrap: break-word !important; white-space: normal !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(2)):not(:has(> div:nth-child(3))) > div[data-testid="column"]:first-child {
                    min-width: 25% !important; flex: 1 1 25% !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(2)):not(:has(> div:nth-child(3))) > div[data-testid="column"]:nth-child(2) {
                    min-width: 70% !important; flex: 1 1 70% !important;
                }
                div[data-testid="stHorizontalBlock"]:has(> div:nth-child(3)):not(:has(> div:nth-child(4))) > div[data-testid="column"] {
                    min-width: 100% !important; flex: 1 1 100% !important; margin-bottom: 15px;
                }
            }

            .swipe-gallery {
                display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding-bottom: 5px;
                -webkit-overflow-scrolling: touch; scrollbar-width: none;
            }
            .swipe-gallery::-webkit-scrollbar { display: none; }
            .swipe-gallery a { scroll-snap-align: center; flex: 0 0 100%; max-width: 100%; text-decoration: none; }
            .swipe-img { width: 100%; height: 300px; object-fit: contain; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }

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

expected_columns = ["ID", "Name", "Price", "Wholesale_Price", "Wholesale_Qty", "Category", "Image_Path", "Free_Delivery", "Seller_Name", "In_Stock"]

@st.cache_data(ttl=180)
def load_products():
    try:
        docs = db.collection('products').stream()
        data = [doc.to_dict() for doc in docs]
        if data:
            return pd.DataFrame(data)
    except: pass
    return pd.DataFrame(columns=expected_columns)

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
                        w_price = int(float(row.get('Wholesale_Price', retail_price)))
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
                            "img_link": img_link
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
    valid_sellers = current_config.get("sellers", {}).values()
    if seller_name not in valid_sellers:
        st.session_state.seller_logged_in = None
        st.error("⚠️ आपका सेलर टोकन एडमिन द्वारा ब्लॉक या डिलीट कर दिया गया है!")
        st.rerun()

if current_config.get("has_banner", False) and current_config.get("banner_url"):
    try: st.image(current_config["banner_url"], use_container_width=True)
    except: st.title("🛍️ Oura Products - Wholesale")
else:
    st.title("🛍️ Oura Products - Wholesale")

multi_color_marquee = """
<div style="background-color: #e3f2fd; padding: 12px; border-radius: 8px; margin-bottom: 20px; margin-top: 10px; border: 1px solid #bbdefb;">
    <marquee behavior="scroll" direction="left" scrollamount="6" style="color: #0d47a1; font-size: 16px; font-weight: bold; font-family: sans-serif;">
        🏭 क्या आप भी एक मैन्युफैक्चरर या होलसेलर हैं? आइए, Oura के साथ मिलकर अपने बिज़नेस को नई ऊंचाइयों पर ले जाएं! 🚀
    </marquee>
</div>
"""
st.markdown(multi_color_marquee, unsafe_allow_html=True)

col1, col2 = st.columns([8, 2])
with col2:
    if not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
        if st.button("🔒 एडमिन / सेलर लॉगिन"):
            st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button("🚪 लॉगआउट"):
            st.session_state.admin_logged_in = False
            st.session_state.seller_logged_in = None
            st.session_state.show_login = False
            st.rerun()

if st.session_state.show_login and not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    with st.container(border=True):
        st.subheader("दुकान में लॉगिन करें")
        login_type = st.radio("लॉगिन का प्रकार चुनें:", ["सेलर (Seller)", "मालिक / एडमिन (Admin)"], horizontal=True)
        
        if login_type == "मालिक / एडमिन (Admin)":
            password = st.text_input("एडमिन पासवर्ड डालें", type="password")
            if st.button("लॉगिन करें"):
                try: correct_password = st.secrets["ADMIN_PASSWORD"]
                except: correct_password = None
                    
                if correct_password and password == correct_password:
                    st.session_state.admin_logged_in = True
                    st.session_state.seller_logged_in = None
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("❌ गलत पासवर्ड!")
        else:
            seller_token = st.text_input("अपना सेलर टोकन (Token) डालें", type="password")
            if st.button("लॉगिन करें"):
                sellers_dict = current_config.get("sellers", {})
                if seller_token in sellers_dict:
                    st.session_state.seller_logged_in = sellers_dict[seller_token]
                    st.session_state.admin_logged_in = False
                    st.session_state.show_login = False
                    st.rerun()
                else: st.error("❌ गलत टोकन! कृपया एडमिन से संपर्क करें।")
    st.markdown("---")

if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success("✅ आप एडमिन (मालिक) के रूप में लॉगिन हैं। आपके पास पूरे ऐप का कंट्रोल है।")
        tab_add, tab_banner, tab_settings = st.tabs(["➕ नया उत्पाद", "🖼️ बैनर व लोगो", "⚙️ सेटिंग्स"])
    else:
        st.success(f"🏪 स्वागत है: {st.session_state.seller_logged_in} (Seller)")
        tab_add, = st.tabs(["➕ नया उत्पाद"])
    
    with tab_add:
        if st.session_state.share_msg:
            st.success("✅ शानदार! आपका नया उत्पाद Oura पर लाइव है।")
            if st.session_state.share_img_path:
                st.image(st.session_state.share_img_path, width=200)
                st.info("💡 **टिप:** इस फोटो को WhatsApp पर भेजने के लिए, फोटो पर उंगली दबाए रखें और **'Copy Image'** चुनें, फिर WhatsApp में Paste कर दें।")
            encoded_share = urllib.parse.quote(st.session_state.share_msg)
            wa_share_link = f"https://wa.me/?text={encoded_share}"
            st.markdown(f'''<a href="{wa_share_link}" target="_blank" style="display:inline-block; background-color:#25D366; color:white; padding:12px 25px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:16px; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">📢 WhatsApp पर शेयर करें</a>''', unsafe_allow_html=True)
            if st.button("➕ एक और नया उत्पाद जोड़ें"):
                st.session_state.share_msg = None
                st.session_state.share_img_path = None
                st.rerun()
        else:
            with st.form("add_product", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    new_id = st.text_input("ID (यूनिक रखें)")
                    new_name = st.text_input("नाम")
                    new_price = st.number_input("सिंगल पीस रेट", min_value=1)
                with col_b:
                    new_w_qty = st.number_input("होलसेल कम से कम पीस", min_value=1, value=10)
                    new_w_price = st.number_input("होलसेल / बॉक्स रेट (प्रति पीस)", min_value=1)
                    new_free_delivery = st.selectbox("सिंगल पीस डिलीवरी", ["फ्री डिलीवरी", "कोरियर चार्ज एक्स्ट्रा"])
                
                new_in_stock = st.checkbox("✅ उत्पाद अभी स्टॉक में उपलब्ध है?", value=True)
                
                if st.session_state.seller_logged_in:
                    st.info(f"🏪 आपका ब्रांड/सेलर नाम: **{st.session_state.seller_logged_in}**")
                    new_seller_name = st.session_state.seller_logged_in
                else:
                    new_seller_name = st.text_input("सेलर / ब्रांड का नाम (अगर खाली छोड़ेंगे तो कुछ नहीं दिखेगा)")
                existing_cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
                cat_options = ["नयी केटेगरी बनाएं..."] + existing_cats
                selected_cat = st.selectbox("केटेगरी चुनें", cat_options)
                if selected_cat == "नयी केटेगरी बनाएं...":
                    final_cat = st.text_input("नई केटेगरी का नाम लिखें (इमोजी 👕👟 भी लगा सकते हैं)")
                else:
                    final_cat = selected_cat
                uploaded_imgs = st.file_uploader("फोटो अपलोड करें (अधिकतम 3)", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="add_imgs")
                submit_btn = st.form_submit_button("उत्पाद सेव करें")
                if submit_btn and new_id and new_name and uploaded_imgs and final_cat:
                    if len(uploaded_imgs) > 3: st.error("⚠️ कृपया अधिकतम 3 फोटो ही चुनें।")
                    else:
                        with st.spinner("AI फोटो चेक कर रहा है और सेव कर रहा है..."):
                            has_violation = False
                            violation_type = ""
                            violation_img_name = ""
                            image_paths = []
                            for img in uploaded_imgs:
                                compressed_bytes, pil_img = compress_image(img.getvalue())
                                try:
                                    if pil_img:
                                        text_in_image = pytesseract.image_to_string(pil_img).lower()
                                        clean_text = re.sub(r'[\s\-\(\)\+]+', '', text_in_image)
                                        if re.search(r'\d{10}', clean_text):
                                            has_violation = True; violation_type = "मोबाईल नंबर"; violation_img_name = img.name; break
                                        if re.search(r'(https?://|www\.)[^\s]+', text_in_image) or re.search(r'\b[a-z0-9\-]+\.(com|in|org|net|co|store|shop)\b', text_in_image):
                                            has_violation = True; violation_type = "वेबसाइट लिंक"; violation_img_name = img.name; break
                                except Exception as e: pass 
                                if not has_violation:
                                    img_url = upload_image_to_imgbb(compressed_bytes)
                                    if img_url: image_paths.append(img_url)
                            if has_violation:
                                st.error(f"🚨 **अपलोड फेल:** फोटो ('{violation_img_name}') में **{violation_type}** मिला है! Oura की पॉलिसी के अनुसार ऐसी फोटो नहीं डाल सकते।")
                            else:
                                final_path_str = "|".join(image_paths)
                                is_free = True if new_free_delivery == "फ्री डिलीवरी" else False
                                seller_val = new_seller_name.strip() if new_seller_name else ""
                                data = {
                                    "ID": new_id, "Name": new_name, "Price": new_price, "Wholesale_Price": new_w_price,
                                    "Wholesale_Qty": new_w_qty, "Category": final_cat, "Image_Path": final_path_str,
                                    "Free_Delivery": is_free, "Seller_Name": seller_val,
                                    "In_Stock": new_in_stock
                                }
                                db.collection('products').document(str(new_id)).set(data)
                                load_products.clear()
                                st.session_state.share_msg = f"⚡ *मार्केट का सबसे हॉट आइटम अब Oura पर!* ⚡\n\n🎁 *उत्पाद:* {new_name}\n"
                                if seller_val: st.session_state.share_msg += f"🏪 *ब्रांड/सेलर:* {seller_val}\n"
                                st.session_state.share_msg += "\n👇 *तुरंत रेट देखें और अपना माल बुक करें:*\nhttps://ouraindia.streamlit.app/"
                                st.session_state.share_img_path = image_paths[0] if image_paths else None
                                st.rerun()

    if st.session_state.admin_logged_in:
        with tab_banner:
            st.subheader("🖼️ ऐप का बैनर (Top Banner)")
            new_banner = st.file_uploader("नया बैनर चुनें", type=["jpg", "png", "jpeg"], key="banner_upload")
            if st.button("बैनर सेव करें") and new_banner:
                with st.spinner("बैनर सेव हो रहा है..."):
                    dummy_delete_image(current_config.get("banner_url", ""))
                    compressed_bytes, _ = compress_image(new_banner.getvalue())
                    b_url = upload_image_to_imgbb(compressed_bytes)
                    if b_url:
                        current_config["has_banner"] = True
                        current_config["banner_url"] = b_url
                        save_config(current_config)
                        st.success("✅ बैनर लग गया!")
                        time.sleep(1)
                        st.rerun()
            if current_config.get("has_banner", False):
                if st.button("❌ बैनर हटाएं"):
                    dummy_delete_image(current_config.get("banner_url", ""))
                    current_config["has_banner"] = False
                    current_config["banner_url"] = ""
                    save_config(current_config)
                    st.rerun()
            st.markdown("---")
            st.subheader("📱 ऐप का लोगो (App Icon)")
            new_logo = st.file_uploader("नया लोगो चुनें (Square)", type=["jpg", "png", "jpeg"], key="logo_upload")
            if st.button("लोगो सेव करें") and new_logo:
                with st.spinner("लोगो सेव हो रहा है..."):
                    dummy_delete_image(current_config.get("logo_url", ""))
                    compressed_bytes, _ = compress_image(new_logo.getvalue())
                    l_url = upload_image_to_imgbb(compressed_bytes)
                    if l_url:
                        current_config["has_logo"] = True
                        current_config["logo_url"] = l_url
                        save_config(current_config)
                        st.success("✅ आपका लोगो सेट हो गया!")
                        time.sleep(1)
                        st.rerun()
            if current_config.get("has_logo", False):
                if st.button("❌ लोगो हटाएं"):
                    dummy_delete_image(current_config.get("logo_url", ""))
                    current_config["has_logo"] = False
                    current_config["logo_url"] = ""
                    save_config(current_config)
                    st.rerun()
        
        with tab_settings:
            st.subheader("📱 संपर्क और बिज़नेस सेटिंग्स")
            new_wa = st.text_input("WhatsApp नंबर", value=current_config.get("admin_whatsapp", "919891587437"))
            new_admin_gst = st.text_input("आपका GST नंबर (Oura Products)", value=current_config.get("admin_gst", ""))
            st.markdown("---")
            st.subheader("🚚 डिफॉल्ट डिलीवरी सेटिंग्स")
            show_free_delivery = st.checkbox("✅ बाय डिफ़ॉल्ट 'फ्री डिलीवरी' दिखाएं?", value=current_config.get("free_delivery_tag", True))
            st.markdown("---")
            st.subheader("👥 सेलर पार्टनर (Seller Management)")
            col_s1, col_s2 = st.columns([3, 1])
            with col_s1: new_seller_brand = st.text_input("नये सेलर / ब्रांड का नाम")
            with col_s2:
                st.write("")
                st.write("")
                if st.button("➕ नया टोकन बनाएं"):
                    if new_seller_brand:
                        new_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                        current_config["sellers"][new_token] = new_seller_brand.strip()
                        save_config(current_config)
                        st.success(f"टोकन बन गया: {new_token}")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("नाम डालें")
            if current_config.get("sellers"):
                st.write("**मौजूदा सेलर्स:**")
                for tkn, s_name in list(current_config["sellers"].items()):
                    col_list1, col_list2 = st.columns([8, 2])
                    with col_list1: st.write(f"🏪 **{s_name}** (टोकन: `{tkn}`)")
                    with col_list2:
                        if st.button("❌ हटाएं", key=f"del_seller_{tkn}"):
                            del current_config["sellers"][tkn]
                            save_config(current_config)
                            st.rerun()
            st.markdown("---")
            st.subheader("💳 मल्टी UPI सेटिंग्स")
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                new_phonepe = st.text_input("PhonePe UPI ID", value=current_config.get("phonepe_upi", ""))
                new_paytm = st.text_input("Paytm UPI ID", value=current_config.get("paytm_upi", ""))
            with col_u2:
                new_gpay = st.text_input("Google Pay (GPay) UPI ID", value=current_config.get("gpay_upi", ""))
                new_bhim = st.text_input("BHIM UPI ID", value=current_config.get("bhim_upi", ""))
            if st.button("⚙️ सभी सेटिंग्स सेव करें"):
                current_config["admin_whatsapp"] = new_wa
                current_config["admin_gst"] = new_admin_gst
                current_config["free_delivery_tag"] = show_free_delivery
                current_config["phonepe_upi"] = new_phonepe
                current_config["paytm_upi"] = new_paytm
                current_config["gpay_upi"] = new_gpay
                current_config["bhim_upi"] = new_bhim
                save_config(current_config)
                st.success("✅ सेटिंग्स सेव हो गईं!")
                time.sleep(1)
                st.rerun()

    st.markdown("---")

search_query = st.text_input("🔍 कोई भी उत्पाद सर्च करें (जैसे: Speaker, Watch...)", "")

def show_swipe_gallery(path_str):
    if not path_str: return []
    paths = [p.strip() for p in path_str.split('|') if p.strip()]
    if not paths: return []
    html_code = '<div class="swipe-gallery">'
    for src in paths:
        if not src.startswith("http"):
            src = f"{GITHUB_RAW_URL}{urllib.parse.quote(src.replace('\\', '/'), safe='/')}"
        html_code += f'<a href="{src}" target="_blank"><img src="{src}" class="swipe-img" loading="lazy" alt="Product Image"></a>'
    html_code += '</div>'
    html_code += f'<div style="text-align:center; font-size:12px; color:gray; margin-top:-5px; margin-bottom:10px;">ज़ूम करने के लिए फोटो पर क्लिक करें 🔍</div>'
    st.markdown(html_code, unsafe_allow_html=True)
    return paths

def show_product_card(row, idx, prefix):
    prefix_idx = f"{prefix}_{idx}"
    p_id = str(row.get('ID', prefix_idx)) 

    with st.container(border=True):
        image_path_str = str(row.get("Image_Path", ""))
        all_paths = show_swipe_gallery(image_path_str)
        img_link_for_wa = all_paths[0] if all_paths else ""
        if img_link_for_wa and not img_link_for_wa.startswith("http"):
            img_link_for_wa = f"{GITHUB_RAW_URL}{urllib.parse.quote(img_link_for_wa.replace('\\', '/'), safe='/')}"
        st.write(f"**{row.get('Name', 'Unknown')}**")
        seller_val = row.get("Seller_Name")
        if pd.notna(seller_val) and str(seller_val).strip() != "":
            st.markdown(f"🏪 **सेलर / ब्रांड:** <span style='color:#E65100; font-weight:bold;'>{str(seller_val).strip()}</span>", unsafe_allow_html=True)
        try: w_qty = int(float(row.get('Wholesale_Qty', 1)))
        except: w_qty = 1
        try: retail_price = row.get('Price', 0)
        except: retail_price = 0
        try: w_price = int(float(row.get('Wholesale_Price', retail_price)))
        except: w_price = retail_price
        show_fd = current_config.get("free_delivery_tag", True)
        val_fd = row.get("Free_Delivery")
        if pd.notna(val_fd) and str(val_fd).strip() != "":
            show_fd = str(val_fd).lower() in ['true', 'yes', '1']
            
        is_in_stock = row.get("In_Stock", True)
        
        if w_qty > 1:
            if show_fd:
                st.markdown(f"🛵 **सिंगल पीस (फ्री डिलीवरी):** ₹{retail_price} <br> 📦 **होलसेल (बॉक्स रेट):** ₹{w_price} *(कम से कम {w_qty} पीस, <span style='color:#d32f2f;font-weight:bold;'>कोरियर चार्ज एक्स्ट्रा</span>)*", unsafe_allow_html=True)
            else:
                st.markdown(f"🛵 **सिंगल पीस रेट:** ₹{retail_price} *(<span style='color:#d32f2f;font-weight:bold;'>कोरियर चार्ज एक्स्ट्रा</span>)* <br> 📦 **होलसेल (बॉक्स रेट):** ₹{w_price} *(कम से कम {w_qty} पीस, <span style='color:#d32f2f;font-weight:bold;'>कोरियर चार्ज एक्स्ट्रा</span>)*", unsafe_allow_html=True)
        else:
            if show_fd: st.markdown(f"🛵 **सिंगल पीस रेट:** ₹{retail_price} *(फ्री डिलीवरी)*")
            else: st.markdown(f"🛵 **सिंगल पीस रेट:** ₹{retail_price} *(<span style='color:#d32f2f;font-weight:bold;'>कोरियर चार्ज एक्स्ट्रा</span>)*", unsafe_allow_html=True)
            
        if is_in_stock:
            qty = st.number_input("मात्रा (पीस)", min_value=1, value=1, key=f"q_{prefix_idx}")
            if st.button("🛒 कार्ट में डालें", key=f"b_{prefix_idx}"):
                final_price = w_price if qty >= w_qty else retail_price
                
                if p_id in st.session_state.cart:
                    st.session_state.cart[p_id]["qty"] += qty
                    if st.session_state.cart[p_id]["qty"] >= w_qty:
                        st.session_state.cart[p_id]["price"] = w_price
                else:
                    st.session_state.cart[p_id] = {"name": row.get('Name', 'Item'), "price": final_price, "qty": qty, "img_link": img_link_for_wa}
                
                save_cart_to_url()
                st.success("कार्ट में जुड़ गया! 🛒")
        else:
            st.markdown("<div style='background-color:#ffebee; color:#c62828; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border:1px solid #ef9a9a; margin-top:10px;'>🚫 आउट ऑफ स्टॉक</div>", unsafe_allow_html=True)
            
        show_edit_delete = False
        if st.session_state.admin_logged_in: show_edit_delete = True
        elif st.session_state.seller_logged_in and st.session_state.seller_logged_in == str(seller_val).strip(): show_edit_delete = True
            
        if show_edit_delete:
            st.markdown("---")
            with st.expander("✏️ रेट, स्टॉक या फोटो बदलें (Edit)"):
                with st.form(f"edit_form_{prefix_idx}"):
                    e_name = st.text_input("नया नाम", value=str(row.get("Name", "")))
                    col_x, col_y = st.columns(2)
                    with col_x:
                        e_price = st.number_input("सिंगल पीस रेट", value=retail_price)
                        e_w_qty = st.number_input("होलसेल मात्रा", value=w_qty)
                    with col_y:
                        e_w_price = st.number_input("होलसेल (बॉक्स रेट)", value=w_price)
                        fd_index = 0 if show_fd else 1
                        e_free_delivery = st.selectbox("सिंगल पीस डिलीवरी", ["फ्री डिलीवरी", "कोरियर चार्ज एक्स्ट्रा"], index=fd_index)
                    
                    e_in_stock = st.checkbox("✅ स्टॉक में उपलब्ध है?", value=is_in_stock)

                    e_seller_name = st.text_input("सेलर / ब्रांड का नाम", value=str(seller_val) if pd.notna(seller_val) else "") if st.session_state.admin_logged_in else st.session_state.seller_logged_in
                    existing_cats_edit = products_df['Category'].dropna().unique().tolist()
                    current_cat = str(row.get("Category", ""))
                    if current_cat not in existing_cats_edit: existing_cats_edit.insert(0, current_cat)
                    e_cat = st.selectbox("केटेगरी", existing_cats_edit, index=existing_cats_edit.index(current_cat))
                    e_uploaded_imgs = st.file_uploader("नई फोटो (Optional, max 3)", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=f"edit_imgs_{prefix_idx}")
                    update_btn = st.form_submit_button("✅ अपडेट करें")
                if update_btn:
                    if e_uploaded_imgs and len(e_uploaded_imgs) > 3: st.error("⚠️ अधिकतम 3 फोटो ही चुनें।")
                    else:
                        with st.spinner("अपडेट हो रहा है..."):
                            target_id = str(row['ID'])
                            final_path_str = str(row.get("Image_Path", ""))
                            if e_uploaded_imgs:
                                dummy_delete_image(final_path_str)
                                new_image_paths = []
                                for img in e_uploaded_imgs:
                                    compressed_bytes, _ = compress_image(img.getvalue())
                                    img_url = upload_image_to_imgbb(compressed_bytes)
                                    if img_url: new_image_paths.append(img_url)
                                final_path_str = "|".join(new_image_paths)
                            e_is_free = True if e_free_delivery == "फ्री डिलीवरी" else False
                            data = {
                                "ID": target_id, "Name": e_name, "Price": e_price, "Wholesale_Price": e_w_price,
                                "Wholesale_Qty": e_w_qty, "Category": e_cat, "Image_Path": final_path_str,
                                "Free_Delivery": e_is_free, "Seller_Name": str(e_seller_name).strip(),
                                "In_Stock": e_in_stock
                            }
                            db.collection('products').document(target_id).set(data)
                            load_products.clear()
                            st.success("✅ अपडेट हो गया!")
                            time.sleep(1)
                            st.rerun()
                if st.button("❌ पक्का डिलीट करें", key=f"del_{prefix_idx}"):
                    with st.spinner("डिलीट हो रहा है..."):
                        target_id = str(row['ID'])
                        dummy_delete_image(image_path_str) 
                        db.collection('products').document(target_id).delete()
                        load_products.clear()
                        st.success("डिलीट हो गया!")
                        time.sleep(1)
                        st.rerun()

if not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    st.markdown("---")
    with st.expander("💼 Oura पर अपना माल बेचें (Become a Seller)"):
        st.info("क्या आप भी मैन्युफैक्चरर या होलसेलर हैं? Oura प्लैटफॉर्म पर जुड़ें और अपने उत्पादों को हज़ारों ग्राहकों तक पहुँचाएं।")
        s_name = st.text_input("आपकी दुकान / कंपनी का नाम")
        s_items = st.text_input("आप क्या माल बेचते हैं?")
        s_city = st.text_input("शहर")
        if st.button("पार्टनरशिप के लिए संपर्क करें"):
            if s_name and s_items:
                s_msg = f"💼 *Oura Seller Partnership*\n\nनमस्ते, मैं Oura पर अपना माल बेचना चाहता हूँ।\n\n🏪 *दुकान:* {s_name}\n📦 *माल:* {s_items}\n📍 *शहर:* {s_city}\n\nकृपया मुझे सेलर बनने की जानकारी दें।"
                encoded_s_msg = urllib.parse.quote(s_msg)
                wa_seller_link = f"https://wa.me/{current_config.get('admin_whatsapp', '')}?text={encoded_s_msg}"
                st.markdown(f'<a href="{wa_seller_link}" target="_blank" style="background: linear-gradient(135deg, #FF9800, #F57C00); color: white !important; padding: 10px 15px; border-radius: 8px; text-decoration: none !important; font-weight: bold; display: inline-block; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">✅ WhatsApp पर अपनी डिटेल भेजें</a>', unsafe_allow_html=True)
            else:
                st.error("कृपया अपनी दुकान का नाम और माल की जानकारी ज़रूर भरें।")

if products_df.empty:
    st.info("जल्द ही नए उत्पाद आएंगे!")
else:
    if search_query:
        st.subheader(f"'{search_query}' के सर्च रिजल्ट:")
        filtered_df = products_df[products_df['Name'].str.contains(search_query, case=False, na=False)]
        if filtered_df.empty: st.warning("इस नाम से कोई उत्पाद नहीं मिला।")
        else:
            cols = st.columns(3)
            for idx, row in filtered_df.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "search")
    
    elif st.session_state.selected_category is None:
        st.subheader("🛍️ कैटेगरीज")
        valid_categories = products_df['Category'].dropna().unique().tolist()
        
        if len(valid_categories) == 0: 
            st.write("अभी कोई कैटेगरी नहीं है।")
        else:
            cat_container = st.container()
            with cat_container:
                st.markdown('<div class="custom-cat-grid"></div>', unsafe_allow_html=True)
                for i in range(0, len(valid_categories), 4):
                    cols = st.columns(4)
                    for j in range(4):
                        if i + j < len(valid_categories):
                            cat = valid_categories[i + j]
                            with cols[j]:
                                if st.button(cat, key=f"cat_btn_{i+j}", use_container_width=True):
                                    st.session_state.selected_category = cat
                                    st.query_params["cat"] = cat
                                    save_cart_to_url()
                                    st.rerun()
            
    else:
        st.subheader(f"📂 {st.session_state.selected_category}")
        
        if st.button("🏠 सारी कैटेगरीज", key="float_back_btn"):
            st.session_state.selected_category = None
            if "cat" in st.query_params:
                del st.query_params["cat"]
            save_cart_to_url()
            st.rerun()
            
        float_js = """
        <script>
        const parentDoc = window.parent.document;
        const buttons = parentDoc.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.innerText && btn.innerText.includes('सारी कैटेगरीज')) {
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
        
        if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
            with st.expander(f"✏️ इस कैटेगरी का नाम/आइकॉन बदलें"):
                new_cat_name = st.text_input("नया नाम या इमोजी डालें:", value=st.session_state.selected_category)
                if st.button("✅ सेव करें", key="rename_cat_btn"):
                    if new_cat_name and new_cat_name != st.session_state.selected_category:
                        with st.spinner("नाम बदला जा रहा है..."):
                            old_cat = st.session_state.selected_category
                            docs = db.collection('products').where('Category', '==', old_cat).stream()
                            for doc in docs:
                                db.collection('products').document(doc.id).update({'Category': new_cat_name})
                            load_products.clear()
                            st.session_state.selected_category = new_cat_name
                            st.query_params["cat"] = new_cat_name
                            st.success("✅ नाम बदल गया!")
                            time.sleep(1)
                            st.rerun()

        cat_products = products_df[products_df['Category'] == st.session_state.selected_category]
        if cat_products.empty: st.write("इस कैटेगरी में अभी कोई उत्पाद नहीं है।")
        else:
            cols = st.columns(3)
            for idx, row in cat_products.reset_index().iterrows():
                with cols[idx % 3]: show_product_card(row, idx, "cat_view")

st.markdown("<br><br><br>", unsafe_allow_html=True) 
st.markdown("---")
st.header("🛒 आपकी बास्केट")

if st.session_state.cart:
    total = 0
    msg = "🧾 *Oura - Order Summary* 🧾\n\n"
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
            with c1: st.write(f"मात्रा: {item['qty']} x ₹{item['price']} = **₹{subtotal}**")
            with c2:
                if st.button("❌", key=f"del_item_{k}"):
                    del st.session_state.cart[k]
                    save_cart_to_url()
                    st.rerun()
        st.markdown("---")
        msg += f"{count}. {item['name']} ({item['qty']} x ₹{item['price']}) = ₹{subtotal}\n"
        if item.get('img_link'): msg += f"👉 फोटो देखें: {item['img_link']}\n"
        count += 1
    
    show_fd = current_config.get("free_delivery_tag", True)
    if show_fd: msg += f"\n💰 *कुल माल:* ₹{total}\n⚠️ *होलसेल (बॉक्स) ऑर्डर पर कोरियर/ट्रांसपोर्ट चार्ज एक्स्ट्रा लगेगा। सिंगल पीस पर डिलीवरी फ्री है।*\n"
    else: msg += f"\n💰 *कुल माल:* ₹{total}\n⚠️ *ट्रांसपोर्ट, पैकिंग और कोरियर चार्ज एक्स्ट्रा लगेगा।*\n"
        
    st.subheader(f"कुल माल: ₹{total}")
    
    available_upis = {}
    if current_config.get("phonepe_upi"): available_upis["PhonePe"] = {"id": current_config["phonepe_upi"], "color": "#5e35b1", "icon": "🟣"}
    if current_config.get("paytm_upi"): available_upis["Paytm"] = {"id": current_config["paytm_upi"], "color": "#00baf2", "icon": "🔵"}
    if current_config.get("gpay_upi"): available_upis["Google Pay"] = {"id": current_config["gpay_upi"], "color": "#1a73e8", "icon": "🔴"}
    if current_config.get("bhim_upi"): available_upis["BHIM"] = {"id": current_config["bhim_upi"], "color": "#ff7043", "icon": "🟠"}

    if available_upis:
        st.markdown("### 💳 सुरक्षित online पेमेंट")
        for name, data in available_upis.items():
            qr_data = f"upi://pay?pa={data['id']}&pn=Oura_Products&am={total}&cu=INR" 
            st.markdown(f'''<a href="{qr_data}" style="display:block; text-align:center; background:{data['color']}; color:white !important; padding:12px; border-radius:10px; text-decoration:none; font-size:16px; font-weight:bold; margin-bottom:10px;">{data['icon']} {name} से ₹{total} पे करें</a>''', unsafe_allow_html=True)
            msg += f"\n💳 *{name} UPI:* {data['id']}"
        
        with st.expander("स्कैन करके पेमेंट करें (QR Code)"):
            qr_tabs = st.tabs(list(available_upis.keys()))
            for idx, (name, data) in enumerate(available_upis.items()):
                with qr_tabs[idx]:
                    qr_data = f"upi://pay?pa={data['id']}&pn=Oura_Products&am={total}&cu=INR"
                    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(qr_data)}", width=150)
                    st.success(f"**{name} UPI ID:** `{data['id']}`")

    st.markdown("---")
    st.markdown("### 🤝 100% ग्राहक संतुष्टि (Customer Trust)")
    st.success("✅ **लाइव पैकिंग प्रूफ:** आपकी पूरी संतुष्टि और भरोसे के लिए, आपके माल की **पैकिंग की लाइव वीडियो और फोटो** डिस्पैच (Dispatch) से पहले सीधे आपके WhatsApp पर भेजी जाएगी। आप बिल्कुल बेफिक्र होकर ऑर्डर करें!")
    msg += "\n\n🤝 *भरोसा:* आपके माल की पैकिंग की लाइव वीडियो और फोटो डिस्पैच से पहले आपको WhatsApp पर भेजी जाएगी。\n"

    st.markdown("---")
    st.markdown("### 📜 रिफंड और रिटर्न पॉलिसी")
    st.warning("⚠️ **ध्यान दें:**\n1. रिफंड या वापसी सिर्फ **'खराब उत्पाद' (Manufacturing Defect)** पर होगी।\n2. ट्रांसपोर्ट में **'माल टूटने' (Transit Damage)** की कोई जिम्मेदारी नहीं।\n3. **इम्पोर्टेड आइटम की custom ड्यूटी की कोई गारंटी नहीं।**")
    msg += "\n📜 *पॉलिसी:*\n- रिफंड सिर्फ 'खराब उत्पाद' पर मिलेगा।\n- ट्रांसपोर्ट में 'माल टूटने' पर कोई रिफंड नहीं।\n- इम्पोर्टेड आइटम की कोई गारंटी नहीं।"

    st.markdown("---")
    st.markdown("### 📍 डिलीवरी और बिल की जानकारी")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        cust_name = st.text_input("आपका नाम / दुकान का नाम")
        cust_mobile = st.text_input("मोबाईल नंबर (10 अंक)")
        cust_address = st.text_area("पूरा पता (शहर, पिनकोड सहित)")
    with col_d2:
        gst_choice = st.selectbox("बिल का प्रकार चुनें:", 
                                 ["बिना GST (Estimate)", "GST @ 5%", "GST @ 12%", "GST @ 18%", "GST @ 28%"])
        
        gst_percent = 0
        if "5%" in gst_choice: gst_percent = 5
        elif "12%" in gst_choice: gst_percent = 12
        elif "18%" in gst_choice: gst_percent = 18
        elif "28%" in gst_choice: gst_percent = 28
        
        cust_gst = ""
        if gst_percent > 0:
            st.info("💡 **बिना GST नंबर वाले ग्राहक भी टैक्स देकर पक्का बिल ले सकते हैं।**")
            cust_gst = st.text_input("ग्राहक का GST नंबर (अगर है तो 15 अक्षर डालें)")
            
        shipping_cost = st.number_input("🚚 कोरियर / पैकिंग चार्ज (₹)", min_value=0, value=0, step=50)

    # 🚀 इनपुट वैलिडेशन चेक (नंबर 6) 🚀
    is_valid = True
    if cust_mobile:
        cust_mobile = cust_mobile.strip()
        if not cust_mobile.isdigit() or len(cust_mobile) != 10:
            st.warning("⚠️ कृपया सही 10 अंकों का मोबाईल नंबर डालें।")
            is_valid = False
            
    if cust_gst:
        cust_gst = cust_gst.strip().upper()
        if len(cust_gst) != 15 or not cust_gst.isalnum():
            st.warning("⚠️ कृपया सही 15 अक्षरों का GST नंबर डालें।")
            is_valid = False

    if is_valid:
        if st.session_state.cart:
            pdf_bytes = generate_pdf_bill(st.session_state.cart, cust_name, cust_mobile, cust_address, cust_gst, gst_percent, shipping_cost, current_config)
            
            pdf_file_name = f"Oura_Invoice_{cust_name.replace(' ', '_') if cust_name else 'Bill'}.pdf"
            
            st.download_button(
                label="📄 प्रोफेशनल PDF बिल डाउनलोड करें",
                data=pdf_bytes,
                file_name=pdf_file_name,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

    final_msg = msg + f"\n\n📍 *डिलीवरी की जानकारी:*\n👤 नाम: {cust_name if cust_name else 'WhatsApp पर बताएंगे'}\n📞 मोबाईल: {cust_mobile if cust_mobile else 'WhatsApp पर बताएंगे'}\n🏠 पता: {cust_address if cust_address else 'WhatsApp पर बताएंगे'}\n🚚 *शिपिंग चार्ज:* ₹{shipping_cost}\n📄 *बिल:* {gst_choice}\n"
    if cust_gst: final_msg += f"🏢 *ग्राहक GST:* {cust_gst}\n"

    wa_link = f"https://wa.me/{current_config.get('admin_whatsapp', '')}?text={urllib.parse.quote(final_msg)}"
    st.markdown(f'''<br><a href="{wa_link}" target="_blank" style="display:block; text-align:center; background: #25D366; color:white; padding:15px; border-radius:10px; text-decoration:none; font-size:18px; font-weight:bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom:10px;">✅ सीधा WhatsApp पर ऑर्डर भेजें</a>''', unsafe_allow_html=True)
    
    if st.button("🗑️ बास्केट खाली करें"):
        st.session_state.cart = {}
        save_cart_to_url()
        st.rerun()

admin_wa_number = current_config.get("admin_whatsapp", "919891587437")
st.markdown(f'''<a id="oura-wa-btn" href="https://wa.me/{admin_wa_number}" target="_blank" title="WhatsApp Us">📞 {admin_wa_number}</a>''', unsafe_allow_html=True)

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
