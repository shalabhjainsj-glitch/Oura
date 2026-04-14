import streamlit as st
import pandas as pd
import os
from datetime import datetime

# पेज की सेटिंग (अगर इसे मेन फाइल में चला रहे हैं तो इसे सबसे ऊपर रखें)
st.set_page_config(page_title="Ledger & Billing System", layout="wide")

# डेटा सेव करने के लिए फोल्डर बनाना (ताकि सब कुछ एक जगह रहे और स्पीड कम न हो)
SAVE_FOLDER = "billing_records"
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

# साइडबार मेन्यू
st.sidebar.title("🛠️ Oura मैनेजमेंट")
menu = ["नया बिल / पेमेंट एंट्री", "खाता और फाइलें (Save/Delete)"]
choice = st.sidebar.radio("ऑप्शन चुनें:", menu)

# --- सेक्शन 1: नई एंट्री ---
if choice == "नया बिल / पेमेंट एंट्री":
    st.title("📝 नया बिल या पेमेंट दर्ज करें")
    st.markdown("यहाँ से आप किसी भी पार्टी का नया बिल या उनसे आए हुए एडवांस की एंट्री कर सकते हैं।")
    
    with st.form("billing_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            customer = st.text_input("पार्टी का नाम (Customer Name)*").strip().upper()
            amount = st.number_input("अमाउंट (₹)*", min_value=0.0, step=100.0)
        
        with col2:
            status = st.selectbox("कैटेगरी चुनें", ["Bill (मार्केट से लेना है)", "Payment/Advance (पार्टी से आ गया)"])
            # प्रोडक्ट का नाम या कोई अन्य रिमार्क
            note = st.text_input("विवरण / रिमार्क (जैसे: 12-inch Speakers, Cable, etc.)")
            
        date = st.date_input("तारीख", datetime.today())
        
        save_btn = st.form_submit_button("एंट्री सेव करें 💾")
        
        if save_btn:
            if customer == "":
                st.error("⚠️ कृपया पार्टी का नाम जरूर लिखें!")
            elif amount == 0:
                st.error("⚠️ कृपया अमाउंट भरें!")
            else:
                # हर पार्टी के लिए अलग फाइल बनेगी
                filename = f"{SAVE_FOLDER}/{customer}_ledger.csv"
                
                # नया डेटा तैयार करना
                new_entry = pd.DataFrame([{
                    "Date": date.strftime("%Y-%m-%d"), 
                    "Type": "Bill" if "Bill" in status else "Advance", 
                    "Amount": amount, 
                    "Note": note
                }])
                
                # अगर फाइल पहले से है तो उसमें जोड़ें, नहीं तो नई बनाएं
                if os.path.exists(filename):
                    existing_df = pd.read_csv(filename)
                    updated_df = pd.concat([existing_df, new_entry], ignore_index=True)
                else:
                    updated_df = new_entry
                
                # फाइल सेव करना
                updated_df.to_csv(filename, index=False)
                st.success(f"✅ {customer} के खाते में ₹ {amount} की एंट्री सफलतापूर्वक सेव हो गई!")

# --- सेक्शन 2: फाइलें मैनेज करना (देखना, डाउनलोड करना और डिलीट करना) ---
elif choice == "खाता और फाइलें (Save/Delete)":
    st.title("📂 पार्टियों का खाता और फाइल मैनेजमेंट")
    
    # फोल्डर में मौजूद सभी CSV फाइलों को खोजना
    files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith('.csv')]
    
    if files:
        st.markdown("आप यहाँ से किसी भी पार्टी की फाइल को देख सकते हैं, डाउनलोड कर सकते हैं या हमेशा के लिए डिलीट कर सकते हैं।")
        
        for file in files:
            customer_name = file.replace("_ledger.csv", "")
            
            # एक पार्टी के लिए बॉक्स बनाना
            with st.expander(f"👤 {customer_name} का खाता"):
                file_path = f"{SAVE_FOLDER}/{file}"
                df = pd.read_csv(file_path)
                
                # बैलेंस कैलकुलेट करना
                total_bill = df[df["Type"] == "Bill"]["Amount"].sum()
                total_advance = df[df["Type"] == "Advance"]["Amount"].sum()
                net_balance = total_bill - total_advance
                
                # हिसाब दिखाना
                c1, c2, c3 = st.columns(3)
                c1.metric("कुल बिल (लेना है)", f"₹ {total_bill:,.2f}")
                c2.metric("कुल जमा (आ गया)", f"₹ {total_advance:,.2f}")
                
                if net_balance > 0:
                    c3.metric("🔴 बकाया (Balance)", f"₹ {net_balance:,.2f}")
                elif net_balance < 0:
                    c3.metric("🟢 एक्स्ट्रा जमा (Advance)", f"₹ {abs(net_balance):,.2f}")
                else:
                    c3.metric("⚪ हिसाब चुकता", "₹ 0.00")

                st.dataframe(df, use_container_width=True)
                
                # डाउनलोड और डिलीट बटन
                col_btn1, col_btn2 = st.columns([1, 4])
                with col_btn1:
                    # डाउनलोड बटन
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 फाइल डाउनलोड करें", 
                        data=csv_data, 
                        file_name=file, 
                        mime="text/csv", 
                        key=f"dl_{file}"
                    )
                with col_btn2:
                    # डिलीट बटन
                    if st.button("🗑️ फाइल डिलीट करें", key=f"del_{file}"):
                        os.remove(file_path)
                        st.warning(f"🚨 {customer_name} की फाइल सिस्टम से पूरी तरह डिलीट कर दी गई है।")
                        st.rerun()
    else:
        st.info("ℹ️ अभी तक किसी भी पार्टी का कोई खाता या फाइल नहीं बनी है। पहले 'नया बिल एंट्री' में जाकर डेटा भरें।")
