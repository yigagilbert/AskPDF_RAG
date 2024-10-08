# importing dependencies
from dotenv import load_dotenv
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import faiss
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from htmlTemplates import css, bot_template, user_template

# Creating custom template to guide LLM model
custom_template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.
Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question:"""

CUSTOM_QUESTION_PROMPT = PromptTemplate.from_template(custom_template)

# Extracting text from PDF
def get_pdf_text(docs):
    text = ""
    for pdf in docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Converting text to chunks
def get_chunks(raw_text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )   
    chunks = text_splitter.split_text(raw_text)
    return chunks

# Using all-MiniLm embeddings model and FAISS to get vectorstore
def get_vectorstore(chunks):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    vectorstore = faiss.FAISS.from_texts(texts=chunks, embedding=embeddings)
    return vectorstore

# Generating conversation chain  
def get_conversationchain(vectorstore):
    llm = ChatOpenAI(temperature=0.2)
    memory = ConversationBufferMemory(
        memory_key='chat_history', 
        return_messages=True,
        output_key='answer'
    )  # Using conversation buffer memory to hold past information
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        condense_question_prompt=CUSTOM_QUESTION_PROMPT,
        memory=memory
    )
    return conversation_chain

# Generating response from user queries and displaying them accordingly
def handle_question(question):
    response = st.session_state.conversation({'question': question})
    st.session_state.chat_history = response["chat_history"]
    for i, msg in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", msg.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", msg.content), unsafe_allow_html=True)

def main():
    load_dotenv()
    st.set_page_config(page_title="Sunbird Demo Chat With Multiple PDFs", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)
    
    # Initialize session state variables
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("Sunbird Demo Chat With Multiple PDFs :books:")

    # Handle question input
    question = st.text_input("Ask a question from your document:")
    if question:
        if st.session_state.conversation is None:
            st.warning("Please upload and process your documents first.")
        else:
            handle_question(question)
            st.session_state.question_input = ""  # Clear input field

    # Sidebar for document upload and processing
    with st.sidebar:
        st.subheader("Your documents")
        docs = st.file_uploader("Upload your PDF here and click on 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            if docs:
                with st.spinner("Processing"):
                    # Get the PDF text
                    raw_text = get_pdf_text(docs)
                    
                    # Get the text chunks
                    text_chunks = get_chunks(raw_text)
                    
                    # Create vectorstore
                    vectorstore = get_vectorstore(text_chunks)
                    
                    # Create conversation chain
                    st.session_state.conversation = get_conversationchain(vectorstore)
                st.success("Documents processed successfully!")
            else:
                st.warning("Please upload at least one PDF document.")

if __name__ == '__main__':
    main()
