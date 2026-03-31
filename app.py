import streamlit as st
import docx
from pypdf import PdfReader
from fpdf import FPDF
import google.generativeai as genai
import re

# --- 1. Inställningar och Konfiguration ---
st.set_page_config(
    page_title="Hemkunskapens Inköpshjälp", 
    page_icon="🛒",
    layout="centered"
)

# --- 2. Hjälpfunktioner för PDF-export ---
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    # Vi använder Helvetica (standardfont)
    pdf.set_font("Helvetica", size=12)
    
    # Rensa bort Markdown (stjärnor)
    clean_text = text.replace("**", "")
    
    # Rensa bort emojis och tecken som inte finns i latin-1
    clean_text = re.sub(r'[^\x00-\x7F\x80-\xFF]', '', clean_text)
    
    # Skriv texten till PDF:en
    pdf.multi_cell(w=pdf.epw, h=10, txt=clean_text.encode('latin-1', 'replace').decode('latin-1'))
    
    # FIX: Konvertera bytearray till bytes för att Streamlit ska acceptera formatet
    return bytes(pdf.output())

# --- 3. Funktioner för att läsa uppladdade filer ---
def read_docx(file):
    doc = docx.Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])

def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content
    return text

# --- 4. Appens Gränssnitt (UI) ---
st.title("🛒 Hemkunskapens Inköpshjälp")
st.info("Ladda upp recept, ange antal elever och få en färdig inköpslista i KG/Liter.")

# Hämta API-nyckel säkert från Streamlit Secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Kunde inte hitta 'GEMINI_API_KEY' i dina Secrets.")
    st.stop()

# Inställningar för matlagningen
col1, col2 = st.columns(2)
with col1:
    students = st.number_input("Totalt antal elever:", min_value=1, value=20)
with col2:
    group_size = st.number_input("Elever per grupp (station):", min_value=1, value=2)

st.divider()

# Inmatningsmetoder
tab1, tab2 = st.tabs(["📁 Ladda upp filer", "📝 Klistra in text"])
all_text_content = ""

with tab1:
    uploaded_files = st.file_uploader(
        "Dra in recept (Word eller PDF)", 
        type=['docx', 'pdf'], 
        accept_multiple_files=True
    )
    if uploaded_files:
        for file in uploaded_files:
            if file.name.endswith('.docx'):
                all_text_content += f"\n--- FIL: {file.name} ---\n" + read_docx(file)
            elif file.name.endswith('.pdf'):
                all_text_content += f"\n--- FIL: {file.name} ---\n" + read_pdf(file)

with tab2:
    pasted_text = st.text_area("Klistra in recepttext direkt:", height=250)
    if pasted_text:
        all_text_content += "\n--- KLISTRAD TEXT ---\n" + pasted_text

# --- 5. Logik för beräkning ---
if st.button("Skapa Inköpslista 🚀", use_container_width=True):
    if not all_text_content:
        st.warning("Du måste ladda upp eller klistra in minst ett recept först!")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        with st.spinner('AI:n räknar ut mängder och enheter...'):
            stations = students / group_size
            prompt = f"""
            Roll: Expert på storkök och hemkunskap.
            Data: {all_text_content}
            
            Kontext: Recepten ska lagas av {students} elever i grupper om {group_size}. 
            Det innebär att varje recept ska multipliceras med {stations}.
            
            Uppdrag:
            1. Summera alla ingredienser.
            2. Omvandla småmått till kg/liter/st för inköp.
            3. Sortera efter butiksavdelning.
            Svara endast med den färdiga listan.
            """
            
            try:
                response = model.generate_content(prompt)
                st.session_state['result'] = response.text
            except Exception as e:
                st.error(f"Ett fel uppstod vid kontakt med AI:n: {e}")

# --- 6. Visa Resultat och Export ---
if 'result' in st.session_state:
    st.success("Här är veckans sammanställda inköpslista:")
    st.markdown(st.session_state['result'])
    
    st.divider()
    
    # Skapa PDF-filen
    try:
        # Nu skickar create_pdf tillbaka rätt format (bytes)
        pdf_bytes = create_pdf(st.session_state['result'])
        
        st.download_button(
            label="📥 Ladda ner listan som PDF",
            data=pdf_bytes,
            file_name="inkopslista_hemkunskap.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Kunde inte skapa PDF-filen: {e}")