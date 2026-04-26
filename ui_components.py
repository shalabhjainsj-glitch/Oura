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

.multi-upi-btn { transition: transform 0.1s; }
.multi-upi-btn:active { transform: scale(0.96); }
</style>
"""

def get_ai_js_code(admin_wa_number):
    return """
    <script>
    const parentWin = window.parent;
    const parentDoc = parentWin.document;

    if (!parentDoc.getElementById('oura-ai-widget')) {
        const widgetDiv = parentDoc.createElement('div');
        widgetDiv.id = 'oura-ai-widget';
        widgetDiv.innerHTML = `
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        @keyframes floatDoll {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-15px); }
            100% { transform: translateY(0px); }
        }
        #oura-ai-btn {
            position: fixed; bottom: 90px; right: 15px; z-index: 9999999;
            cursor: pointer; animation: floatDoll 3s ease-in-out infinite;
            filter: drop-shadow(0px 8px 10px rgba(0,0,0,0.3));
        }
        #oura-ai-btn img { width: 70px; height: 70px; border-radius: 50%; border: 3px solid #2b6cb0; background: white; object-fit: cover; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        
        #ai-chat-box {
            position: fixed; bottom: 170px; right: 15px; z-index: 9999999;
            width: 320px; max-width: 90vw; height: 400px; max-height: 60vh; background: #ffffff; border-radius: 15px;
            box-shadow: 0 15px 30px rgba(0,0,0,0.2); display: none;
            flex-direction: column; overflow: hidden; border: 2px solid #e2e8f0;
            font-family: 'Poppins', sans-serif; box-sizing: border-box;
        }
        #ai-chat-box * { box-sizing: border-box; }
        
        .ai-header {
            background: linear-gradient(135deg, #2b6cb0 0%, #4299e1 100%);
            color: white; padding: 12px 15px; font-weight: 600; font-size: 16px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .ai-messages {
            flex: 1; padding: 15px; overflow-y: auto; background: #fdfdfd;
            display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth;
        }
        .msg-ai {
            background: #f1f3f5; padding: 10px 15px; border-radius: 0 15px 15px 15px;
            align-self: flex-start; max-width: 85%; font-size: 13px; border: 1px solid #e9ecef;
            color: #333;
        }
        .msg-user {
            background: #2b6cb0; color: white; padding: 10px 15px; border-radius: 15px 0 15px 15px;
            align-self: flex-end; max-width: 85%; font-size: 13px;
        }
        .ai-input-area {
            display: flex; border-top: 1px solid #eee; padding: 10px; background: white; align-items: center; width: 100%;
        }
        .ai-input-area input {
            flex: 1; padding: 10px 12px; border: 1px solid #ccc; border-radius: 20px;
            outline: none; font-size: 14px; min-width: 0;
        }
        .ai-input-area button {
            background: #25D366; color: white; border: none; padding: 10px 16px;
            margin-left: 8px; border-radius: 20px; cursor: pointer; font-weight: bold; font-size: 14px;
        }
        </style>
        
        <div id="ai-chat-box">
            <div class="ai-header">
                <span>👩‍💻 Oura Helpline</span>
                <span id="close-ai-btn" style="cursor:pointer; font-size:20px; line-height: 1;">×</span>
            </div>
            <div class="ai-messages" id="ai-msgs">
                <div class="msg-ai">नमस्ते! 🙏 मैं असिस्टेंट हूँ। बताइए, मैं आपकी क्या मदद कर सकती हूँ?</div>
            </div>
            <div class="ai-input-area">
                <input type="text" id="ai-input" placeholder="मैसेज लिखें..."/>
                <button id="ai-send-btn">Send</button>
            </div>
        </div>
        
        <div id="oura-ai-btn">
            <img src="https://img.icons8.com/color/256/customer-support.png" alt="AI Girl"/>
        </div>
        `;
        parentDoc.body.appendChild(widgetDiv);

        let msgCount = 0;
        const adminWA = "__ADMIN_WA__";

        function handleSend() {
            let input = parentDoc.getElementById('ai-input');
            let text = input.value.trim();
            if(!text) return;
            
            let msgs = parentDoc.getElementById('ai-msgs');
            msgs.innerHTML += `<div class="msg-user">${text}</div>`;
            input.value = '';
            msgs.scrollTop = msgs.scrollHeight;
            msgCount++;
            
            setTimeout(() => {
                let reply = "";
                let t = text.toLowerCase();
                
                if(msgCount >= 4 || t.includes("call") || t.includes("admin") || t.includes("owner") || t.includes("मालिक") || t.includes("whatsapp") || t.includes("bat") || t.includes("बात") || t.includes("number") || t.includes("संपर्क") || t.includes("contact")) {
                    reply = `मुझे लगता है इस विषय पर आपको सीधे एडमिन (Shalabh Sir) से बात करनी चाहिए।<br><br>📲 <a href="https://wa.me/${adminWA}?text=Hello" target="_blank" style="color:#25D366; font-weight:bold; text-decoration:none;">यहाँ क्लिक करके WhatsApp करें</a><br><br>📞 या कॉल करें: <b>+91-${adminWA}</b>`;
                } 
                else if(t.includes("rate") || t.includes("price") || t.includes("रेट") || t.includes("प्राइस") || t.includes("कितने")) {
                    reply = "हर प्रोडक्ट के नीचे आपको 3 रेट (सिंगल, होलसेल, और सुपर बल्क) दिखेंगे। आप कार्ट में जितनी ज्यादा मात्रा डालेंगे, सबसे कम वाला रेट अपने आप लग जाएगा! 🛍️";
                } 
                else if(t.includes("delivery") || t.includes("डिलीवरी") || t.includes("shipping") || t.includes("पहुंचेगा") || t.includes("चार्ज")) {
                    reply = "छोटे आर्डर पर कुछ प्रोडक्ट्स पर 'फ्री डिलीवरी' है। बल्क आर्डर का कोरियर चार्ज आपके बिल में जुड़ता है। सारा माल हमारी दिल्ली वेयरहाउस से डिस्पैच होता है। 🚚";
                } 
                else if(t.includes("seller") || t.includes("सेलर") || t.includes("अकाउंट") || t.includes("दुकान") || t.includes("बेचना")) {
                    reply = "सेलर बनने के लिए आपको एडमिन से एक 'टोकन' (Password) लेना होगा। फिर आप ऊपर 'लॉगिन' करके अपने रेट और प्रोडक्ट्स खुद डाल सकते हैं! 🏪";
                } 
                else if(t.includes("hi") || t.includes("hello") || t.includes("नमस्ते")) {
                    reply = "हेलो जी! 🙋‍♀️ बताइए मैं आपको कौन से प्रोडक्ट या रेट की जानकारी दूँ?";
                }
                else {
                    reply = "मैं अभी नई हूँ और सीख रही हूँ! 👩‍💻 आप होलसेल रेट, डिलीवरी या सेलर अकाउंट के बारे में पूछ सकते हैं। <br><br>मुझसे नहीं, सीधे मालिक से बात करने के लिए बस '<b>Call</b>' या '<b>Admin</b>' लिखें।";
                }
                
                msgs.innerHTML += `<div class="msg-ai">${reply}</div>`;
                msgs.scrollTop = msgs.scrollHeight;
            }, 800);
        }

        parentDoc.getElementById('ai-send-btn').addEventListener('click', handleSend);
        
        parentDoc.getElementById('ai-input').addEventListener('keypress', function(e) {
            if(e.key === 'Enter') handleSend();
        });
        
        parentDoc.getElementById('close-ai-btn').addEventListener('click', function() {
            parentDoc.getElementById('ai-chat-box').style.display = 'none';
        });

        parentDoc.getElementById('oura-ai-btn').addEventListener('click', function() {
            let box = parentDoc.getElementById('ai-chat-box');
            box.style.display = box.style.display === 'flex' ? 'none' : 'flex';
        });
    }
    </script>
    """.replace("__ADMIN_WA__", str(admin_wa_number))
