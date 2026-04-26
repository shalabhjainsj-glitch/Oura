import streamlit as st
import pandas as pd
import json
import firebase_admin
from firebase_admin import credentials, firestore

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

@st.cache_data(ttl=3600, show_spinner=False)
def load_products():
    expected_columns = ["ID", "Name", "Retail_Qty", "Price", "Tier1_Price", "Tier1_Qty", "Tier2_Price", "Tier2_Qty", "Category", "Image_Path", "Free_Delivery", "Seller_Name", "In_Stock", "Unit_Base", "Unit_T1", "Unit_T2"]
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
    except: pass
    return ledger_data
