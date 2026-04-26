import streamlit as st
import streamlit.components.v1 as st_components
import pandas as pd
import urllib.parse
import json
import time
import re
import io
import os
import requests
import base64
from PIL import Image
import datetime
from fpdf import FPDF
import firebase_admin
from firebase_admin import credentials, firestore

# --- फोल्डर सेटअप (PDF सेव करने के लिए) ---
INVOICE_FOLDER = "saved_invoices"
if not os.path.exists(INVOICE_FOLDER): os.makedirs(INVOICE_FOLDER)

GITHUB_REPO = "shalabhjainsj-glitch/Oura"
GITHUB_BRANCH = "main"
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/"

# --- Firebase सेटअप ---
if not firebase_admin._apps:
    try:
        key_dict = dict(st.secrets["FIREBASE_JSON"])
        if 'private_key' in key_dict: key_dict['private_key'] = key_dict['private_key'].replace('\\n', '\n')
        firebase_admin.initialize_app(credentials.Certificate(key_dict))
    except Exception as e: st.error(f"🚨 Firebase Error: {e}")

db = firestore.client()

# --- यूटिलिटी फंक्शन & AI गार्ड ---
def ai_spam_check(text):
    """AI गार्ड: सेलर को नंबर या लिंक डालने से रोकता है"""
    text_str = str(text).lower()
    if re.search(r'\b\d{10}\b', text_str): return True 
    if re.search(r'(https?://|www\.|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text_str): return True 
    return False

def upload_image_to_imgbb(file_bytes):
    try:
        key = st.secrets.get("IMGBB_API_KEY")
        if not key: return None
        res = requests.post("https://api.imgbb.com/1/upload", data={"key": key, "image": base64.b64encode(file_bytes).decode('utf-8')})
        if res.status_code == 200: return res.json()["data"]["url"]
        return None
    except: return None

def compress_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB': img = img.convert('RGB')
        if img.width > 800:
            img = img.resize((800, int((float(img.height) * (800 / float(img.width))))), Image.Resampling.LANCZOS)
        comp_io = io.BytesIO()
        img.save(comp_io, format='JPEG', quality=75)
        return comp_io.getvalue(), img
    except: return image_bytes, None

def load_config():
    try:
        doc = db.collection('settings').document('config').get()
        if doc.exists: return doc.to_dict()
    except: pass
    return {"admin_whatsapp": "919891587437", "admin_gst": "07AKWPB1315K", "sellers": {}}

current_config = load_config()
if "sellers" not in current_config: current_config["sellers"] = {}

@st.cache_data(ttl=3600, show_spinner=False)
def load_products():
    try:
        docs = db.collection('products').stream()
        data = [d.to_dict() for d in docs]
        if data:
            df = pd.DataFrame(data)
            for c in ['Unit_Base', 'Unit_T1', 'Unit_T2']:
                if c not in df.columns: df[c] = df.get('Unit_Type', 'Pcs')
                df[c].fillna('Pcs', inplace=True)
            return df
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_ledger_data():
    ledger_data = {}
    try:
        for cust in db.collection('ledgers').stream():
            if cust.id == "config": continue
            docs = db.collection('ledgers').document(cust.id).collection('transactions').order_by("Date").stream()
            txns = [d.to_dict() | {'doc_id': d.id} for d in docs]
            if txns: ledger_data[cust.id] = pd.DataFrame(txns)
    except: pass
    return ledger_data

products_df = load_products()

def save_cart_to_url():
    if st.session_state.cart:
        st.query_params["cart"] = "_".join([f"{k}*{v['qty']}" for k, v in st.session_state.cart.items()])
    else:
        if "cart" in st.query_params: del st.query_params["cart"]

# --- PDF जेनरेटर (फोटो के साथ) ---
def generate_pdf_bill(cart, cust_name, cust_mobile, cust_address, cust_gst, gst_rate, shipping, last_bal, paid, config, inv_date):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 20); pdf.set_text_color(43, 108, 176)
    pdf.cell(0, 10, "9 CLASS PRODUCTS", ln=True, align='C') 
    pdf.set_font("Arial", '', 10); pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Delhi, India | Ph: +91 {config.get('admin_whatsapp', '9891587437')}", ln=True, align='C'); pdf.ln(5)
    pdf.set_font("Arial", 'B', 14); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, "TAX INVOICE" if gst_rate > 0 else "ESTIMATE / QUOTATION", ln=True, align='C'); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10); pdf.cell(20, 6, "Billed To:"); pdf.set_font("Arial", '', 10)
    pdf.cell(100, 6, cust_name if cust_name else "Cash Customer")
    pdf.set_font("Arial", 'B', 10); pdf.cell(30, 6, "Date: "); pdf.set_font("Arial", '', 10)
    pdf.cell(40, 6, str(inv_date), ln=True); pdf.ln(5)
    
    pdf.set_fill_color(230, 240, 255); pdf.set_font("Arial", 'B', 9)
    pdf.cell(10, 10, "S.No", border=1, align='C', fill=True)
    pdf.cell(15, 10, "Pic", border=1, align='C', fill=True) 
    pdf.cell(80, 10, "Item Description", border=1, align='L', fill=True)
    pdf.cell(25, 10, "Qty", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Rate", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Amount", border=1, align='C', fill=True); pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    subtotal = 0; idx = 1
    for k, item in cart.items():
        amt = item['price'] * item['qty']; subtotal += amt; y_before = pdf.get_y()
        pdf.cell(10, 10, str(idx), border=1, align='C')
        if item.get('img_link'):
            try:
                res = requests.get(item['img_link'], timeout=3)
                pdf.image(io.BytesIO(res.content), x=22, y=y_before+1, w=11, h=8)
            except: pass
        pdf.cell(15, 10, "", border=1)
        pdf.cell(80, 10, str(item['name'])[:35], border=1, align='L')
        pdf.cell(25, 10, f"{item['qty']} {item.get('unit', 'Pcs')}", border=1, align='C')
        pdf.cell(30, 10, f"{item['price']:.2f}", border=1, align='R')
        pdf.cell(30, 10, f"{amt:.2f}", border=1, align='R'); pdf.ln(); idx += 1
        
    pdf.set_font("Arial", 'B', 10); pdf.cell(160, 10, "Subtotal", border=1, align='R')
    pdf.cell(30, 10, f"{subtotal:.2f}", border=1, align='R'); pdf.ln()
    
    tax = subtotal + shipping; gst_amt = (tax * gst_rate) / 100 if gst_rate > 0 else 0
    g_total = tax + gst_amt + last_bal - paid
    pdf.set_fill_color(220, 255, 220); pdf.cell(160, 12, "NET BALANCE DUE (Rs)", border=1, align='R', fill=True)
    pdf.cell(30, 12, f"{g_total:.2f}", border=1, align='R', fill=True)
    return pdf.output(dest='S').encode('latin1'), g_total

# --- पेज सेटअप & CSS ---
st.set_page_config(page_title="9 Class - Wholesale", page_icon="🛍️", layout="wide")
st.markdown("""<style>
#MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
div.stButton > button { background-color: #2b6cb0; color: white !important; border-radius: 8px !important; font-weight: 600 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; }
div[data-testid="stContainer"] { background-color: #ffffff; border-radius: 10px !important; border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 15px; }
.swipe-gallery { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding-bottom: 5px; } .swipe-gallery::-webkit-scrollbar { display: none; }
.swipe-img { width: 100%; height: 250px; object-fit: contain; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; }
</style>""", unsafe_allow_html=True)

# --- सेशन स्टेट ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'seller_logged_in' not in st.session_state: st.session_state.seller_logged_in = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if "cat" in st.query_params: st.session_state.selected_category = st.query_params["cat"]
else: st.session_state.selected_category = None

# --- हैडर और लॉगिन ---
c_log, c_btn = st.columns([8, 2])
c_log.title("🛍️ 9 Class - Wholesale Market")
with c_btn:
    if not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
        if st.button("🔒 लॉगिन"): st.session_state.show_login = not st.session_state.show_login
    else:
        if st.button("🚪 लॉगआउट"): st.session_state.admin_logged_in = False; st.session_state.seller_logged_in = None; st.session_state.show_login = False; st.rerun()

# --- फ्लोटिंग WhatsApp ---
admin_wa = current_config.get("admin_whatsapp", "919891587437")
st_components.html(f'<a href="https://wa.me/{admin_wa}" target="_blank" style="position:fixed; bottom:20px; left:15px; z-index:999999;"><img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="55" style="filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.3));"></a>', height=0, width=0)

if st.session_state.show_login and not (st.session_state.admin_logged_in or st.session_state.seller_logged_in):
    with st.container(border=True):
        l_type = st.radio("लॉगिन का प्रकार चुनें:", ["सेलर", "एडमिन"], horizontal=True)
        if l_type == "एडमिन":
            pwd = st.text_input("एडमिन पासवर्ड", type="password")
            if st.button("लॉगिन करें"):
                if pwd == st.secrets.get("ADMIN_PASSWORD", ""): st.session_state.admin_logged_in = True; st.session_state.show_login = False; st.rerun()
                else: st.error("❌ गलत पासवर्ड!")
        else:
            tok = st.text_input("सेलर टोकन", type="password")
            if st.button("लॉगिन करें"):
                if tok in current_config.get("sellers", {}):
                    s_data = current_config["sellers"][tok]
                    st.session_state.seller_logged_in = s_data["name"] if isinstance(s_data, dict) else s_data
                    st.session_state.show_login = False; st.rerun()
                else: st.error("❌ गलत टोकन!")

# --- एडमिन और सेलर पैनल ---
if st.session_state.admin_logged_in or st.session_state.seller_logged_in:
    if st.session_state.admin_logged_in:
        st.success("✅ आप एडमिन के रूप में लॉगिन हैं।")
        tab_add, tab_set, tab_ledger = st.tabs(["➕ नया उत्पाद", "⚙️ सेटिंग्स", "📒 खाते और बिल (Edit/Delete)"])
    else:
        st.success(f"🏪 Welcome: {st.session_state.seller_logged_in}")
        tab_add, = st.tabs(["➕ नया उत्पाद"])
    
    with tab_add:
        with st.form("add_product", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            new_id = c1.text_input("ID (यूनिक रखें)"); new_name = c2.text_input("Product Name")
            
            c3, c4, c5 = st.columns(3)
            u_base = c3.selectbox("इकाई (Base)", ["Pcs", "Dozen", "Box", "Set"])
            r_qty = c4.number_input("मात्रा (Base)", min_value=1, value=1)
            r_price = c5.number_input("रेट (₹)", min_value=0.0, format="%.2f")
            
            c6, c7, c8 = st.columns(3)
            u_t1 = c6.selectbox("इकाई (Tier 1)", ["Pcs", "Dozen", "Box", "Set"], index=1)
            t1_qty = c7.number_input("Tier 1 मात्रा", min_value=0, value=0)
            t1_price = c8.number_input("Tier 1 रेट (₹)", min_value=0.0, format="%.2f")
            
            up_imgs = st.file_uploader("Upload Photos", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
            img_urls = st.text_input("या सीधे Image URL डालें (| लगाकर)")
            
            cats = products_df['Category'].dropna().unique().tolist() if not products_df.empty else []
            sel_cat = st.selectbox("Category (बॉक्स)", ["नयी केटेगरी बनाएं..."] + cats)
            fin_cat = st.text_input("नयी केटेगरी का नाम") if sel_cat == "नयी केटेगरी बनाएं..." else sel_cat
            
            if st.form_submit_button("Save Product") and new_id and new_name and fin_cat:
                # --- AI स्पैम चेक (सिर्फ सेलर के लिए) ---
                if not st.session_state.admin_logged_in and (ai_spam_check(new_name) or (img_urls and ai_spam_check(img_urls))):
                    st.error("🚨 AI अलर्ट: सुरक्षा कारणों से सेलर प्रोडक्ट के नाम या लिंक में फोन नंबर या वेबसाइट URL नहीं डाल सकते!")
                else:
                    paths = []
                    if up_imgs:
                        for img in up_imgs:
                            c_bytes, _ = compress_image(img.getvalue())
                            url = upload_image_to_imgbb(c_bytes)
                            if url: paths.append(url)
                    if img_urls: paths.extend([u.strip() for u in img_urls.split("|") if u.strip()])
                    
                    db.collection('products').document(str(new_id)).set({
                        "ID": new_id, "Name": new_name, "Category": fin_cat, "Image_Path": "|".join(paths),
                        "Retail_Qty": r_qty, "Price": r_price, "Unit_Base": u_base,
                        "Tier1_Qty": t1_qty, "Tier1_Price": t1_price, "Unit_T1": u_t1,
                        "In_Stock": True, "Seller_Name": st.session_state.seller_logged_in or ""
                    })
                    load_products.clear(); st.success("✅ Saved!"); st.rerun()

    if st.session_state.admin_logged_in:
        with tab_set:
            st.subheader("👥 सेलर मैनेजमेंट (Seller Tokens)")
            c_s1, c_s2, c_s3 = st.columns(3)
            new_s_name = c_s1.text_input("सेलर का नाम"); new_s_phone = c_s2.text_input("WhatsApp नंबर"); new_s_tok = c_s3.text_input("नया टोकन (Password)")
            if st.button("➕ सेलर जोड़ें"):
                if new_s_name and new_s_tok:
                    current_config["sellers"][new_s_tok] = {"name": new_s_name, "phone": new_s_phone}
                    db.collection('settings').document('config').set(current_config); st.success("जुड़ गया!"); st.rerun()
            if current_config.get("sellers"):
                for tok, sdata in list(current_config["sellers"].items()):
                    nm = sdata["name"] if isinstance(sdata, dict) else sdata
                    col_a, col_b = st.columns([8, 2])
                    col_a.info(f"🏪 {nm} (Token: {tok})")
                    if col_b.button("❌ डिलीट", key=f"del_{tok}"):
                        del current_config["sellers"][tok]; db.collection('settings').document('config').set(current_config); st.rerun()
                        
        with tab_ledger:
            st.subheader("📒 पार्टियों का खाता (Smart Ledger)")
            st.info("खाते में पुरानी एंट्री बदलें या 'Delete' पर टिक लगाकर उसे हमेशा के लिए हटा दें।")
            ledgers = load_ledger_data()
            if not ledgers: st.warning("कोई खाता नहीं है।")
            for c_name, df in ledgers.items():
                with st.expander(f"👤 {c_name} का खाता"):
                    disp_df = df.drop(columns=['doc_id', 'Timestamp'], errors='ignore')
                    disp_df['Delete'] = False 
                    ed_df = st.data_editor(disp_df, num_rows="dynamic", key=f"ed_{c_name}")
                    if st.button(f"💾 {c_name} का खाता सेव करें", key=f"s_{c_name}"):
                        for idx, row in ed_df.iterrows():
                            if idx < len(df): 
                                doc_id = df.iloc[idx]['doc_id']
                                if row.get('Delete', False): db.collection('ledgers').document(c_name).collection('transactions').document(doc_id).delete()
                                else: db.collection('ledgers').document(c_name).collection('transactions').document(doc_id).update({"Amount": row['Amount'], "Note": row['Note'], "Type": row['Type'], "Date": row['Date']})
                            else: 
                                if not row.get('Delete', False) and not pd.isna(row.get('Amount')):
                                    db.collection('ledgers').document(c_name).collection('transactions').add({"Date": str(row.get('Date', datetime.date.today())), "Type": str(row.get('Type', 'Bill')), "Amount": float(row['Amount']), "Note": str(row.get('Note', '')), "Timestamp": firestore.SERVER_TIMESTAMP})
                        load_ledger_data.clear(); st.success("अपडेट हो गया!"); st.rerun()
            
            st.markdown("---")
            st.subheader("📂 सेव किए गए PDF बिल")
            pdfs = [f for f in os.listdir(INVOICE_FOLDER) if f.endswith('.pdf')]
            for p in pdfs:
                c1, c2, c3 = st.columns([6, 2, 2])
                c1.write(f"📄 **{p}**")
                with open(f"{INVOICE_FOLDER}/{p}", "rb") as f: c2.download_button("📥 डाउनलोड", f.read(), p, "application/pdf", key=f"dl_{p}")
                if c3.button("🗑️ डिलीट", key=f"rm_{p}"): os.remove(f"{INVOICE_FOLDER}/{p}"); st.rerun()

st.markdown("---")

# --- प्रोडक्ट ग्रिड ---
def show_product_card(row, idx):
    p_id = str(row.get('ID')); name = row.get('Name')
    r_p = float(row.get('Price', 0.0)); r_q = int(float(row.get('Retail_Qty', 1))); u_b = row.get('Unit_Base', 'Pcs')
    t1_p = float(row.get('Tier1_Price', r_p)); t1_q = int(float(row.get('Tier1_Qty', 0))); u_t1 = row.get('Unit_T1', u_b)
    
    img_str = str(row.get("Image_Path", "")); paths = [p.strip() for p in img_str.split('|') if p.strip()]
    f_img = paths[0] if paths else ""
    if f_img and not f_img.startswith("http"): f_img = f"{GITHUB_RAW_URL}{urllib.parse.quote(f_img)}"

    with st.container(border=True):
        if f_img:
            st.markdown(f'<div style="position:relative;"><div style="position:absolute; top:10px; right:10px; z-index:10; display:flex; gap:8px;"><a href="{f_img}" download target="_blank" style="background:#1877F2; color:white; padding:6px 12px; border-radius:20px; text-decoration:none; font-weight:bold;">📥 Photo</a><a href="https://wa.me/?text={urllib.parse.quote(f"⚡ *{name}* Rates: ₹{r_p}")}" target="_blank" style="background:#25D366; color:white; padding:6px 12px; border-radius:20px; text-decoration:none; font-weight:bold;">💬 WA</a></div><div class="swipe-gallery">{"".join([f"<a href={s} target=_blank><img src={s} class=swipe-img></a>" for s in (paths if paths else [])])}</div></div>', unsafe_allow_html=True)
            
        st.subheader(name)
        if t1_q > 0: st.markdown(f"""<div style="display:flex; justify-content:space-around; text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px;"><div style="flex:1;"><b>{r_q}+ {u_b}</b><br><span style="color:#2b6cb0; font-weight:bold;">₹{r_p}</span></div><div style="border-left:1px solid #ccc;"></div><div style="flex:1;"><b>{t1_q}+ {u_t1}</b><br><span style="color:#d32f2f; font-weight:bold;">₹{t1_p}</span></div></div>""", unsafe_allow_html=True)
        else: st.markdown(f"<div style='text-align:center; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:10px;'><b>{r_q}+ {u_b} रेट:</b> <span style='color:#2b6cb0; font-size:18px; font-weight:bold;'>₹{r_p}</span></div>", unsafe_allow_html=True)
        
        opts = {f"{r_q} {u_b} (₹{r_p})": (r_p, u_b, r_q)}
        if t1_q > 0: opts[f"{t1_q} {u_t1} (₹{t1_p})"] = (t1_p, u_t1, t1_q)
        
        sel_opt = st.selectbox("क्या खरीदना है?", list(opts.keys()), key=f"sel_{idx}")
        b_p, b_u, m_q = opts[sel_opt]
        qty = st.number_input("मात्रा", min_value=m_q, value=m_q, key=f"q_{idx}")
        if st.button("🛒 Add to Cart", key=f"btn_{idx}"):
            c_key = f"{p_id}|{b_u}|{b_p}"
            if c_key in st.session_state.cart: st.session_state.cart[c_key]["qty"] += qty
            else: st.session_state.cart[c_key] = {"name": name, "price": b_p, "qty": qty, "unit": b_u, "img_link": f_img}
            save_cart_to_url(); st.success("जुड़ गया!")

if not products_df.empty:
    if st.session_state.selected_category is None:
        st.subheader("🛍️ कैटेगरीज")
        cats = products_df['Category'].dropna().unique().tolist()
        if cats:
            st.markdown('<div id="safe-cat-grid"></div><style>div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; } div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"] { width: calc(25% - 8px) !important; } div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(#safe-cat-grid), div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) > div[data-testid="stElementContainer"]:has(style) { display: none !important; } div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button { height: 90px !important; width: 100% !important; border-radius: 12px !important; background: #ffffff !important; border: 2px solid #e2e8f0 !important; box-shadow: 0 4px 8px rgba(0,0,0,0.08) !important; color: #1a202c !important; font-weight: 700 !important; font-size: 13px !important; white-space: normal !important; padding: 4px !important; } div[data-testid="stVerticalBlock"]:has(#safe-cat-grid) button:hover { border-color: #2b6cb0 !important; color: #2b6cb0 !important;}</style>', unsafe_allow_html=True)
            for idx, c in enumerate(cats):
                if st.button(c, key=f"c_{idx}"): st.session_state.selected_category = c; st.query_params["cat"] = c; save_cart_to_url(); st.rerun()
    else:
        st.subheader(f"📂 {st.session_state.selected_category}")
        if st.button("🏠 वापस सारे बॉक्स पर जाएं"): st.session_state.selected_category = None; del st.query_params["cat"]; save_cart_to_url(); st.rerun()
        st_components.html("""<script>document.querySelectorAll('button').forEach(b => { if(b.innerText.includes('वापस सारे बॉक्स')) { b.style.position='fixed'; b.style.bottom='100px'; b.style.left='20px'; b.style.zIndex='999999'; b.style.background='#2b6cb0'; b.style.color='white'; b.style.padding='10px 20px'; b.style.borderRadius='50px'; b.style.width='auto'; b.style.minHeight='auto'; b.style.boxShadow='0 4px 8px rgba(0,0,0,0.2)';} });</script>""", height=0)
        
        cat_prods = products_df[products_df['Category'] == st.session_state.selected_category]
        cols = st.columns(3)
        for idx, row in cat_prods.reset_index().iterrows():
            with cols[idx % 3]: show_product_card(row, idx)

# --- कार्ट और बिलिंग ---
st.markdown("<br><br><br><br>", unsafe_allow_html=True); st.markdown("---")
st.header("🛒 आपकी बास्केट")
if st.session_state.cart:
    total = 0
    for k, item in list(st.session_state.cart.items()):
        sub = item['price'] * item['qty']; total += sub
        c1, c2 = st.columns([8, 2])
        c1.write(f"✔️ **{item['name']}** - {item['qty']} {item.get('unit','Pcs')} x ₹{item['price']} = **₹{sub}**")
        if c2.button("❌", key=f"d_{k}"): del st.session_state.cart[k]; save_cart_to_url(); st.rerun()
    st.subheader(f"कुल माल: ₹{total:.2f}")
    
    with st.form("bill_form"):
        c1, c2 = st.columns(2)
        c_name = c1.text_input("Customer Name (बिल का नाम)"); c_mob = c1.text_input("Mobile"); c_add = c1.text_area("Address")
        gst_choice = c2.selectbox("GST Type", ["Estimate", "5%", "12%", "18%", "28%"])
        gst_rate = 5 if "5" in gst_choice else (12 if "12" in gst_choice else (18 if "18" in gst_choice else (28 if "28" in gst_choice else 0)))
        ship = c2.number_input("Shipping (₹)", min_value=0.0); paid = c2.number_input("Advance Paid (₹)", min_value=0.0)
        submit_bill = st.form_submit_button("✅ बिल तैयार करें (और खाते में जोड़ें)")

    if submit_bill:
        last_b = 0.0; safe_name = c_name.strip().upper() if c_name else ""
        if safe_name:
            try:
                t_b, t_a = 0, 0
                for d in db.collection('ledgers').document(safe_name).collection('transactions').stream():
                    data = d.to_dict()
                    if data.get("Type")=="Bill": t_b += data.get("Amount",0)
                    elif data.get("Type")=="Advance": t_a += data.get("Amount",0)
                last_b = t_b - t_a
            except: pass
            
        pdf_bytes, final_total = generate_pdf_bill(st.session_state.cart, c_name, c_mob, c_add, "", gst_rate, ship, last_b, paid, current_config, datetime.date.today())
        st.session_state.ready_pdf = pdf_bytes
        
        # ऑटोमैटिक PDF सेव
        d_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        s_file = f"OURA_Bill_{safe_name.replace(' ', '_') if safe_name else 'Cash'}_{d_str}.pdf"
        with open(f"{INVOICE_FOLDER}/{s_file}", "wb") as f: f.write(pdf_bytes)
        
        # ऑटोमैटिक खाता एंट्री
        if safe_name:
            db.collection('ledgers').document(safe_name).set({"active": True}, merge=True)
            db.collection('ledgers').document(safe_name).collection('transactions').add({"Date": datetime.date.today().strftime("%Y-%m-%d"), "Type": "Bill", "Amount": final_total + paid - last_b, "Note": "Auto-Generated Bill", "Timestamp": firestore.SERVER_TIMESTAMP})
            if paid > 0: db.collection('ledgers').document(safe_name).collection('transactions').add({"Date": datetime.date.today().strftime("%Y-%m-%d"), "Type": "Advance", "Amount": paid, "Note": "Paid with Bill", "Timestamp": firestore.SERVER_TIMESTAMP})
            load_ledger_data.clear()
            
        st.session_state.cart = {}; save_cart_to_url()
        st.success("✅ बिल तैयार है! PDF सेव हो गया और अमाउंट पार्टी के खाते में जुड़ गया।")
        
    if 'ready_pdf' in st.session_state:
        st.download_button("📄 Download PDF Bill (With Photos)", data=st.session_state.ready_pdf, file_name="Bill.pdf", mime="application/pdf")
    if st.session_state.cart:
        if st.button("🗑️ बास्केट खाली करें"): st.session_state.cart = {}; save_cart_to_url(); st.rerun()

# --- AI हेल्प डेस्क ---
ai_js = """<script>const d=window.parent.document; if(!d.getElementById('ai-w')){const w=d.createElement('div');w.id='ai-w';w.innerHTML=`<style>@keyframes floatDoll { 0% { transform: translateY(0px); } 50% { transform: translateY(-15px); } 100% { transform: translateY(0px); } } #ai-btn { position: fixed; bottom: 90px; right: 15px; z-index: 9999999; cursor: pointer; animation: floatDoll 3s ease-in-out infinite; } #ai-btn img { width: 70px; height: 70px; border-radius: 50%; border: 3px solid #2b6cb0; background: white; box-shadow: 0 4px 8px rgba(0,0,0,0.1); } #ai-box { position: fixed; bottom: 170px; right: 15px; z-index: 9999999; width: 320px; height: 400px; background: #ffffff; border-radius: 15px; box-shadow: 0 15px 30px rgba(0,0,0,0.2); display: none; flex-direction: column; border: 2px solid #e2e8f0; } .ai-hdr { background: linear-gradient(135deg, #2b6cb0 0%, #4299e1 100%); color: white; padding: 12px 15px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; } .ai-msgs { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; } .msg-ai { background: #f1f3f5; padding: 10px 15px; border-radius: 0 15px 15px 15px; align-self: flex-start; max-width: 85%; font-size: 13px; color: #333; } .msg-u { background: #2b6cb0; color: white; padding: 10px 15px; border-radius: 15px 0 15px 15px; align-self: flex-end; max-width: 85%; font-size: 13px; } .ai-in { display: flex; border-top: 1px solid #eee; padding: 10px; background: white; } .ai-in input { flex: 1; padding: 10px 12px; border: 1px solid #ccc; border-radius: 20px; outline: none; } .ai-in button { background: #25D366; color: white; border: none; padding: 10px 16px; margin-left: 8px; border-radius: 20px; cursor: pointer; font-weight: bold; }</style><div id="ai-box"><div class="ai-hdr"><span>👩‍💻 9 Class Helpline</span><span id="ai-cl" style="cursor:pointer; font-size:20px;">×</span></div><div class="ai-msgs" id="msgs"><div class="msg-ai">नमस्ते! 🙏 मैं असिस्टेंट हूँ। बताइए, मैं आपकी क्या मदद कर सकती हूँ?</div></div><div class="ai-in"><input type="text" id="ai-i" placeholder="मैसेज लिखें..."/><button id="ai-s">Send</button></div></div><div id="ai-btn"><img src="https://img.icons8.com/color/256/customer-support.png"/></div>`;d.body.appendChild(w);let c=0;const aw="__WA__";function snd(){let i=d.getElementById('ai-i');let txt=i.value.trim();if(!txt)return;let m=d.getElementById('msgs');m.innerHTML+=`<div class="msg-u">${txt}</div>`;i.value='';m.scrollTop=m.scrollHeight;c++;setTimeout(()=>{let r=`📲 <a href="https://wa.me/${aw}?text=Hello" target="_blank" style="color:#25D366; font-weight:bold; text-decoration:none;">यहाँ क्लिक करके WhatsApp करें</a><br><br>📞 या कॉल करें: <b>+91-${aw}</b>`;m.innerHTML+=`<div class="msg-ai">${r}</div>`;m.scrollTop=m.scrollHeight;},800);}d.getElementById('ai-s').addEventListener('click',snd);d.getElementById('ai-i').addEventListener('keypress',e=>{if(e.key==='Enter')snd();});d.getElementById('ai-cl').addEventListener('click',()=>d.getElementById('ai-box').style.display='none');d.getElementById('ai-btn').addEventListener('click',()=>{let b=d.getElementById('ai-box');b.style.display=b.style.display==='flex'?'none':'flex';});}</script>"""
st_components.html(ai_js.replace("__WA__", current_config.get("admin_whatsapp", "919891587437")), height=0)
