import streamlit as st
import pandas as pd
import os
import datetime
from database import db, load_ledger_data
from firebase_admin import firestore

INVOICE_FOLDER = "saved_invoices"

def render_admin_ledger():
    st.subheader("📒 पार्टियों का खाता (Smart Ledger)")
    st.info("💡 खाते में पुरानी एंट्री बदलें या 'Delete' पर टिक लगाकर उसे हमेशा के लिए हटा दें।")
    
    all_ledgers = load_ledger_data()
    if not all_ledgers:
        st.warning("ℹ️ अभी तक किसी पार्टी का खाता नहीं बना है।")
    else:
        for cust_name, df_ledger in all_ledgers.items():
            with st.expander(f"👤 {cust_name} का खाता"):
                display_df = df_ledger.drop(columns=['doc_id', 'Timestamp'], errors='ignore')
                display_df['Delete'] = False # डिलीट करने का नया बॉक्स
                
                edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, key=f"ed_{cust_name}")
                
                if st.button(f"💾 {cust_name} का खाता सेव करें", key=f"save_ed_{cust_name}", type="primary"):
                    for idx, row in edited_df.iterrows():
                        if idx < len(df_ledger): 
                            doc_id = df_ledger.iloc[idx]['doc_id']
                            if row.get('Delete', False):
                                db.collection('ledgers').document(cust_name).collection('transactions').document(doc_id).delete()
                            else:
                                db.collection('ledgers').document(cust_name).collection('transactions').document(doc_id).update({
                                    "Amount": row['Amount'], "Note": row['Note'], "Type": row['Type'], "Date": row['Date']
                                })
                        else: 
                            if not row.get('Delete', False) and not pd.isna(row.get('Amount')):
                                db.collection('ledgers').document(cust_name).collection('transactions').add({
                                    "Date": str(row.get('Date', datetime.date.today())), 
                                    "Type": str(row.get('Type', 'Bill')), 
                                    "Amount": float(row['Amount']), "Note": str(row.get('Note', '')),
                                    "Timestamp": firestore.SERVER_TIMESTAMP
                                })
                    load_ledger_data.clear()
                    st.success("✅ खाता सफलतापूर्वक अपडेट हो गया!")
                    st.rerun()

    st.markdown("---")
    st.subheader("📂 सेव किए गए PDF बिल")
    if not os.path.exists(INVOICE_FOLDER): os.makedirs(INVOICE_FOLDER)
    pdf_files = [f for f in os.listdir(INVOICE_FOLDER) if f.endswith('.pdf')]
    
    if pdf_files:
        for pdf_f in pdf_files:
            c1, c2, c3 = st.columns([6, 2, 2])
            c1.write(f"📄 **{pdf_f}**")
            with c2:
                with open(f"{INVOICE_FOLDER}/{pdf_f}", "rb") as f:
                    st.download_button("📥 डाउनलोड", data=f.read(), file_name=pdf_f, mime="application/pdf", key=f"dl_{pdf_f}")
            with c3:
                if st.button("🗑️ डिलीट", key=f"del_{pdf_f}"):
                    os.remove(f"{INVOICE_FOLDER}/{pdf_f}")
                    st.success("✅ बिल डिलीट हो गया!")
                    st.rerun()
    else:
        st.info("अभी तक कोई PDF बिल सेव नहीं हुआ है।")
