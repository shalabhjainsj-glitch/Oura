import streamlit as st
import streamlit.components.v1 as st_components
import pandas as pd
import urllib.parse
import os
import datetime
from database import db, load_config, save_config, load_products, load_ledger_data
from utils import t, safe_int, safe_float, upload_image_to_imgbb, compress_image
from pdf_generator import generate_pdf_bill
from ui_components import hide_streamlit_style, get_ai_js_code

# --- Setup ---
GITHUB_RAW_URL = "https://raw.githubusercontent.com/shalabhjainsj-glitch/Oura/main/"
current_config = load_config()
st.set_page_config(page_title="9 Class - Wholesale", layout="wide")
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- Cart Logic with Refresh Protection ---
if 'cart' not in st.session_state:
    st.session_state.cart = {}
    if "cart" in st.query_params:
        try:
            # URL से कार्ट वापस लोड करना
            cart_data = st.query_params["cart"].split("_")
            for item in cart_data:
                p_id, unit, price, qty = item.split("*")
                st.session_state.cart[f"{p_id}|{unit}|{price}"] = {
                    "name": "Item", "price": float(price), "qty": int(qty), "unit": unit, "img_link": ""
                }
        except: pass

def save_cart_to_url():
    if st.session_state.cart:
        items = [f"{k.replace('|', '*') if '|' in k else k}*{v['qty']}" for k, v in st.session_state.cart.items()]
        st.query_params["cart"] = "_".join(items)
    else:
        st.query_params.clear()

# --- UI Functions ---
def show_product_card(row, idx):
    p_id = str(row.get('ID'))
    name = row.get('Name')
    
    # Pricing Tiers
    r_price = safe_float(row.get('Price'))
    r_unit = row.get('Unit_Base', 'Pcs')
    t1_price = safe_float(row.get('Tier1_Price'))
    t1_qty = safe_int(row.get('Tier1_Qty'), 0)
    t1_unit = row.get('Unit_T1', 'Pcs')
    t2_price = safe_float(row.get('Tier2_Price'))
    t2_qty = safe_int(row.get('Tier2_Qty'), 0)
    t2_unit = row.get('Unit_T2', 'Pcs')

    # Images & Sharing
    img_str = str(row.get("Image_Path", ""))
    paths = [p.strip() for p in img_str.split('|') if p.strip()]
    first_img = ""
    if paths:
        first_img = paths[0] if paths[0].startswith("http") else f"{GITHUB_RAW_URL}{urllib.parse.quote(paths[0])}"

    with st.container(border=True):
        if first_img:
            st.image(first_img, use_container_width=True)
            # Photo Sharing Buttons
            c1, c2 = st.columns(2)
            c1.markdown(f'<a href="{first_img}" download target="_blank" style="text-decoration:none;"><button style="width:100%; background:#1877F2; color:white; border:none; padding:5px; border-radius:5px;">📥 Photo</button></a>', unsafe_allow_html=True)
            wa_text = urllib.parse.quote(f"⚡ *{name}*\nRate: ₹{r_price}\nOrder here: https://ouraindia.streamlit.app/")
            c2.markdown(f'<a href="https://wa.me/?text={wa_text}" target="_blank" style="text-decoration:none;"><button style="width:100%; background:#25D366; color:white; border:none; padding:5px; border-radius:5px;">💬 WA</button></a>', unsafe_allow_html=True)

        st.subheader(name)
        
        # Display Rates
        opts = {f"1 {r_unit} (₹{r_price})": (r_price, r_unit, 1)}
        if t1_qty > 0: opts[f"{t1_qty} {t1_unit} (₹{t1_price})"] = (t1_price, t1_unit, t1_qty)
        if t2_qty > 0: opts[f"{t2_qty} {t2_unit} (₹{t2_price})"] = (t2_price, t2_unit, t2_qty)
        
        sel_opt = st.selectbox("रेट चुनें (Price List)", list(opts.keys()), key=f"sel_{idx}")
        buy_p, buy_u, min_q = opts[sel_opt]
        
        qty = st.number_input("मात्रा", min_value=min_q, value=min_q, key=f"q_{idx}")
        
        if st.button("🛒 Add to Cart", key=f"btn_{idx}"):
            st.session_state.cart[f"{p_id}|{buy_u}|{buy_p}"] = {
                "name": name, "price": buy_p, "qty": qty, "unit": buy_u, "img_link": first_img
            }
            save_cart_to_url()
            st.success("कार्ट में जुड़ गया!")

# --- Main App ---
st.title("🛍️ 9 CLASS - WHOLESALE")
products_df = load_products()

if not products_df.empty:
    valid_cats = products_df['Category'].dropna().unique().tolist()
    
    # 4-Box Category Grid
    if not st.session_state.get('selected_category'):
        st.markdown('<div id="safe-cat-grid"></div>', unsafe_allow_html=True)
        # (CSS already in ui_components)
        cols = st.columns(4)
        for i, cat in enumerate(valid_cats):
            if cols[i % 4].button(cat, key=f"cat_{i}", use_container_width=True):
                st.session_state.selected_category = cat
                st.rerun()
    else:
        if st.button("🏠 Back to Categories"):
            st.session_state.selected_category = None
            st.rerun()
            
        cat_prods = products_df[products_df['Category'] == st.session_state.selected_category]
        cols = st.columns(3)
        for i, row in cat_prods.reset_index().iterrows():
            with cols[i % 3]: show_product_card(row, i)

# --- Basket & Billing ---
st.divider()
st.header("🛒 आपकी बास्केट")
if st.session_state.cart:
    for k, item in list(st.session_state.cart.items()):
        st.write(f"✔️ {item['name']} ({item['qty']} {item['unit']}) - ₹{item['price'] * item['qty']}")
    
    if st.button("🗑️ बास्केट खाली करें"):
        st.session_state.cart = {}
        save_cart_to_url()
        st.rerun()
        
    with st.form("bill_form"):
        c_name = st.text_input("Customer Name")
        if st.form_submit_button("✅ बिल तैयार करें"):
            pdf = generate_pdf_bill(st.session_state.cart, c_name, "", "", "", 0, 0, 0, 0, current_config, datetime.date.today())
            st.download_button("📄 Download Bill with Photos", data=pdf, file_name="Bill.pdf", mime="application/pdf")
