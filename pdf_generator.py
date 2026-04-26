from fpdf import FPDF
import datetime
import re

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
