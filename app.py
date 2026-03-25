import streamlit as st
import docx
import google.generativeai as genai
import os

# --- Inställningar för appen ---
st.set_page_config(page_title="Hemkunskapens Inköpshjälp", page_icon="🛒")

st.title("🛒 Hemkunskapens Inköpshjälp")
st.write("Ladda upp veckans recept och få en färdig inköpslista i rätt enheter!")

# --- Funktion för att läsa Word-filer ---
def read_docx(file):
    doc = docx.Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# --- Användargränssnitt i Streamlit ---
api_key = st.secrets["GEMINI_API_KEY"]

# Uppladdning av recept
uploaded_files = st.file_uploader("Ladda upp recept (Word-format)", type=['docx'], accept_multiple_files=True)

# Inställningar för elever
students = st.number_input("Hur många elever ska laga maten?", min_value=1, value=20)
group_size = st.number_input("Hur stora är grupperna? (T.ex. 2 elever per recept)", min_value=1, value=2)

# --- Själva uträkningen ---
if st.button("Beräkna inköpslista 🚀"):
    if not api_key:
        st.warning("Du måste ange en API-nyckel för att fortsätta.")
    elif not uploaded_files:
        st.warning("Vänligen ladda upp minst ett recept.")
    else:
        # Konfigurera AI
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        with st.spinner('Läser recept och räknar om enheter...'):
            all_recipes_text = ""
            for file in uploaded_files:
                all_recipes_text += f"\n\n--- Recept: {file.name} ---\n"
                all_recipes_text += read_docx(file)
            
            portions = students / group_size
            
            # Här är "magin" – instruktionen till AI:n
            prompt = f"""
            Du är en smart assistent för en hemkunskapslärare. 
            Här är texten från ett eller flera recept:
            {all_recipes_text}
            
            Dessa recept är vanligtvis anpassade för en viss mängd portioner, men nu ska {students} elever laga detta. 
            Eleverna jobbar i grupper om {group_size}, vilket betyder att recepten totalt ska lagas {portions} gånger.
            
            Din uppgift:
            1. Räkna ut exakt hur mycket av varje råvara som behöver köpas in totalt för ALLA grupper.
            2. Omvandla små enheter (krm, tsk, msk) till de enheter man köper i affären (kg, liter, gram, styck). 
               Använd standardvikter (t.ex. att 1 msk strösocker är ca 15g, 1 msk vetemjöl är ca 10g).
            3. Slå ihop samma råvaror om de finns i flera recept.
            4. Svara BARA med en tydlig och snyggt formaterad inköpslista uppdelad i kategorier (t.ex. Mejeri, Skafferi, Frukt & Grönt).
            """
            
            try:
                response = model.generate_content(prompt)
                st.success("Klar! Här är veckans inköpslista:")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Ett fel uppstod: {e}")