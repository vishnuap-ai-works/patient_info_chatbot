import streamlit as st
import requests
import os 

# FastAPI server URL
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "fastapi-app")
API_URL = f"http://{FASTAPI_HOST}:8000/generate_sql/"

def get_sql_and_report(question):
    """Call the FastAPI backend to generate SQL and clinical report"""
    try:
        response = requests.get(API_URL, params={"question": question})
        response.raise_for_status()
        return response.json()  # Returns JSON with sql_query and clinical_report
    except requests.exceptions.RequestException as e:
        st.error(f"Error occurred: {e}")
        return None

# Streamlit UI
st.title("Patient Chat Bot SQL Generator")

# Question input
question = st.text_area("Enter your question:")

if st.button("Generate SQL and Report"):
    if question:
        st.write("Generating SQL and clinical report... Please wait.")
        result = get_sql_and_report(question)
        if result:
            st.subheader("Generated SQL Query")
            st.code(result.get("sql_query"), language="sql")
            
            st.subheader("Clinical Interpretation")
            st.write(result.get("clinical_report"))
    else:
        st.warning("Please enter a question to generate the SQL query.")
