import streamlit as st
import docx
from pypdf import PdfReader
from fpdf import FPDF
import google.generativeai as genai

# --- Inställningar ---
st.set_page_config(page_title="Hemkunskapens Inköpshjälp", page_icon="🛒")

# --- Funktion för att skapa PDF ---
def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    # Vi använder en standardfont som hanterar latin-1 (åäö)
    pdf.set_font("Helvetica", size=12)
    
    # AI:ns svar kan innehålla stjärnor för fetstil (**), vi rensar dem för PDF:en
    clean_text = text.replace("**", "")
    
    # Dela upp texten i rader och skriv till PDF
    for line in clean_text.split('\n'):
        # encode('latin-1', 'replace') ser till att åäö fungerar i standard-PDF
        pdf.multi_cell(0, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'))
    
    return pdf.output()

# --- Funktioner för att läsa filer ---
def read_docx(file):
    doc = docx.Document(file)
    return '\n'.join([para.text for para in doc.paragraphs])

def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# --- Appens Gränssnitt ---
st.title("🛒 Hemkunskapens Inköpshjälp")

api_key = st.secrets["GEMINI_API_KEY"]

col1, col2 = st.columns(2)
with col1:
    students = st.number_input("Antal elever:", min_value=1, value=20)
with col2:
    group_size = st.number_input("Elever per grupp:", min_value=1, value=2)

st.divider()

tab1, tab2 = st.tabs(["📁 Ladda upp filer", "📝 Klistra in text"])
all_text_content = ""

with tab1:
    uploaded_files = st.file_uploader("Ladda upp recept (Word eller PDF)", type=['docx', 'pdf'], accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            if file.name.endswith('.docx'):
                all_text_content += f"\n--- {file.name} ---\n" + read_docx(file)
            elif file.name.endswith('.pdf'):
                all_text_content += f"\n--- {file.name} ---\n" + read_pdf(file)

with tab2:
    pasted_text = st.text_area("Klistra in recepttext här:", height=200)
    if pasted_text:
        all_text_content += "\n--- Klistrad text ---\n" + pasted_text

# --- Beräkning ---
if st.button("Skapa Inköpslista 🚀", use_container_width=True):
    if not all_text_content:
        st.error("Hittade inget recept!")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        with st.spinner('Beräknar mängder...'):
            portions = students / group_size
            prompt = f"""
            Här är recept: {all_text_content}
            Antal elever: {students}, Gruppstorlek: {group_size}.
            Skapa en inköpslista med mängder i kg/liter/st. Gruppera efter butiksavdelning.
            Var tydlig och strukturerad.
            """
            try:
                response = model.generate_content(prompt)
                result_text = response.text
                
                # Spara resultatet i "session_state" så det finns kvar när man klickar på ladda ner
                st.session_state['shopping_list'] = result_text
                
            except Exception as e:
                st.error(f"Ett fel uppstod: {e}")

# Visa resultat och ladda ner-knapp om listan finns
if 'shopping_list' in st.session_state:
    st.success("Inköpslistan är klar!")
    st.markdown(st.session_state['shopping_list'])
    
    # Skapa PDF-filen i minnet
    pdf_data = create_pdf(st.session_state['shopping_list'])
    
    st.download_button(
        label="📥 Ladda ner som PDF",
        data=pdf_data,
        file_name="inkopslista.pdf",
        mime="application/pdf",
        use_container_width=True
    )