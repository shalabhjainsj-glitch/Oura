import requests
import io
from fpdf import FPDF
import datetime
import re

def generate_pdf_bill(cart, cust_name, cust_mobile, cust_address, cust_gst, gst_rate, shipping_charge, last_balance, amount_paid, config, invoice_date):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(43, 108, 176)
    pdf.cell(0, 10, "9 CLASS - WHOLESALE", ln=True, align='C') 
    
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(100, 100, 100)
    admin_phone = config.get("admin_whatsapp", "9891587437")
    pdf.cell(0, 6, f"Delhi, India | Ph: +91 {admin_phone}", ln=True, align='C')
    
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(230, 240, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(20, 10, "Photo", border=1, align='C', fill=True) # फोटो कॉलम
    pdf.cell(85, 10, "Item Description", border=1, align='L', fill=True)
    pdf.cell(25, 10, "Qty", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Rate (Rs)", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Amount", border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    subtotal = 0
    
    for k, item in cart.items():
        amt = item['price'] * item['qty']
        subtotal += amt
        y_before = pdf.get_y()
        
        # फोटो डालने का लॉजिक
        if item.get('img_link'):
            try:
                res = requests.get(item['img_link'], timeout=5)
                img_data = io.BytesIO(res.content)
                pdf.image(img_data, x=11, y=y_before+1, w=18, h=8)
            except:
                pdf.text(12, y_before+6, "No Pic")
        
        pdf.cell(20, 10, "", border=1) # फोटो के लिए खाली सेल
        pdf.cell(85, 10, str(item['name'])[:40], border=1)
        pdf.cell(25, 10, f"{item['qty']} {item.get('unit', 'Pcs')}", border=1, align='C')
        pdf.cell(30, 10, f"{item['price']:.2f}", border=1, align='R')
        pdf.cell(30, 10, f"{amt:.2f}", border=1, align='R')
        pdf.ln()
        
    # Totals
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(160, 10, "Subtotal", border=1, align='R')
    pdf.cell(30, 10, f"{subtotal:.2f}", border=1, align='R')
    pdf.ln()
    
    grand_total = subtotal + shipping_charge + last_balance - amount_paid
    pdf.set_fill_color(220, 255, 220)
    pdf.cell(160, 10, "NET BALANCE DUE (Rs)", border=1, align='R', fill=True)
    pdf.cell(30, 10, f"{grand_total:.2f}", border=1, align='R', fill=True)
    
    return pdf.output(dest='S').encode('latin1')
