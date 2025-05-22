import streamlit as st
import pandas as pd
import openai
from io import StringIO
from docx import Document
import pdfplumber
from serpapi import GoogleSearch

# --- Securely get your API keys ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SERPAPI_KEY = st.secrets["SERPAPI_KEY"]

st.set_page_config(layout="wide")
st.title("Part Finder Chatbot 🤖")

st.markdown(
    """
    **Features:**  
    - Chatbot for general questions  
    - Chat about content in uploaded files (txt, Word, Excel, PDF)  
    - Uses SerpAPI to provide current web search context for your questions
    """
)

# ---- FILE UPLOAD SECTION ----
st.header("Chat With Your File")
uploaded_file = st.file_uploader(
    "Upload a file to chat with (txt, docx, xlsx, pdf):",
    type=["txt", "docx", "xlsx", "pdf"],
    key="file_uploader1"
)

def extract_text_from_file(uploaded_file):
    filetype = uploaded_file.name.split('.')[-1].lower()
    if filetype == "txt":
        return StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    elif filetype == "docx":
        doc = Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    elif filetype == "pdf":
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    elif filetype == "xlsx":
        df = pd.read_excel(uploaded_file)
        return df.head(20).to_string()
    else:
        return "Unsupported file type."

file_text = ""
if uploaded_file is not None:
    file_text = extract_text_from_file(uploaded_file)
    st.info("File content loaded and ready for chat.")

# ---- SERPAPI WEB SEARCH FUNCTION ----
def web_search(query):
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        if "organic_results" in results:
            output = ""
            for res in results["organic_results"][:3]:  # Top 3 results
                output += f"- **{res.get('title','No Title')}**: {res.get('snippet','')}\n"
                if res.get("link"):
                    output += f"  [Source]({res['link']})\n"
            return output if output else "No search results found."
        return "No search results found."
    except Exception as e:
        return f"SerpAPI Error: {e}"

# ---- Chat Section ----
st.header("Chat with IC Part Finder (Current Info + File Chat!)")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---- Display chat history using st.chat_message ----
for sender, message in st.session_state.chat_history:
    if sender == "You":
        with st.chat_message("user"):
            st.markdown(message)
    else:
        with st.chat_message("assistant"):
            st.markdown(message)

user_input = st.chat_input("Type your message...")
if user_input:
    st.session_state.chat_history.append(("You", user_input))

    # ---- Web search for up-to-date info ----
    with st.spinner("Searching the web for the latest info..."):
        search_results = web_search(user_input)
        st.write("DEBUG: Search results from SerpAPI:", search_results)  # Debug

    # ---- Compose the context for GPT ----
    system_context = ""
    if file_text:
        system_context += f"The following is the content of the uploaded file:\n{file_text}\n\n"
    if search_results:
        system_context += (
            "You MUST use the following current information found in a live web search to answer the user's question as accurately as possible. "
            "Only use your own knowledge if the web search does not answer the question.\n"
            f"{search_results}\n\n"
        )

    st.write("DEBUG: Full system context to GPT:", system_context)  # Debug

    messages = []
    if system_context:
        messages.append({"role": "system", "content": system_context})
    # Last 10 chat messages for context (optional, can increase)
    for sender, msg in st.session_state.chat_history[-10:]:
        messages.append({"role": "user" if sender == "You" else "assistant", "content": msg})

    # ---- Ask GPT ----
    with st.spinner("Thinking..."):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                max_tokens=1024,
            )
            bot_message = response.choices[0].message.content
        except Exception as e:
            bot_message = f"OpenAI API Error: {e}"

    st.session_state.chat_history.append(("Bot", bot_message))
    st.rerun()

st.divider()
