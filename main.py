from fastapi import FastAPI, HTTPException, Query
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
import re
from typing import Dict
import uvicorn
from pathlib import Path
import os

app = FastAPI()

# Get the current file path
current_file_path = Path(__file__).resolve()
# Get the data/db path
root = current_file_path
data_path = os.path.join(root,'data/raw_data')
db_path = 'data/database'
print(db_path)
# Initialize database connection
db = SQLDatabase.from_uri(
    f"sqlite:///{db_path}/patient_data.db",
    include_tables=["PatientData", "PhysicalActivityData"]
)

# Initialize LLM with optimized parameters
llm = ChatGroq(groq_api_key=os.getenv("GROQ_API_KEY"), 
               model_name="llama-3.3-70b-versatile", 
               streaming=True)

"""
llm = ChatOllama(
    model="sqlcoder:15b-q8_0",  # Specify the model you want to use (adjust as necessary)
    temperature=0.1,  # Fine-tune the creativity of responses (0 to 1)
    top_p=0.9,  # Controls diversity via nucleus sampling
    stop=["```"],  # Optional stopping conditions
    num_ctx=4096,  # Adjust context window size if required
)
"""

# SQL Generation Prompt
sql_template = """### Role ###
You are a clinical data SQL expert. Generate precise queries using:

### Schema
{schema}

### Approved Table Aliases ###
- PatientData (use alias: pd)
- PhysicalActivityData (use alias: pa)

### Column Details ###
{column_details}

### Rules ###
1. Always use PatientData.Patient_Number (or pd.Patient_Number) for joins
2. Use explicit JOIN conditions with table aliases
3. Always qualify column names with table aliases (e.g., pd.Patient_Number)
4. Add brief comments with --
5. Only use the approved table aliases (pd, pa)

### Examples ###
-- Good: Using approved aliases
SELECT pd.Patient_Number 
FROM PatientData pd
WHERE pd.Chronic_kidney_disease = 1;

-- Good: Join with aliases
SELECT pd.Patient_Number, pa.physical_activity
FROM PatientData pd
JOIN PhysicalActivityData pa ON pd.Patient_Number = pa.Patient_Number
WHERE pd.Chronic_kidney_disease = 1;

-- Bad: Unqualified column
SELECT Patient_Number FROM PatientData;

-- Bad: Unapproved alias
SELECT p.Patient_Number FROM PatientData p;

### Task ###
Question: {question}
"""

sql_prompt = ChatPromptTemplate.from_template(
    sql_template)
sql_prompt = sql_prompt.partial(
    column_details="""
PatientData (pd) columns:
- Patient_Number: Unique patient identifier
- Blood_Pressure_Abnormality: 0=Normal, 1=Abnormal
- Level_of_Hemoglobin: Hemoglobin level (g/dl)
- Genetic_Pedigree_Coefficient: Disease pedigree (0=distant, 1=immediate)
- Age: Patient age
- BMI: Body Mass Index
- Sex: 0=Male, 1=Female
- Pregnancy: 0=No, 1=Yes (females only)
- Smoking: 0=No, 1=Yes
- salt_content_in_the_diet: Salt intake (mg/day)
- alcohol_consumption_per_day: Alcohol intake (ml/day)
- Level_of_Stress: 1=Low, 2=Normal, 3=High
- Chronic_kidney_disease: 0=No, 1=Yes
- Adrenal_and_thyroid_disorders: 0=No, 1=Yes

PhysicalActivityData (pa) columns:
- Patient_Number: Links to PatientData
- Day_Number: Day identifier
- physical_activity: Steps per day
"""
)

# Build SQL generation chain
sql_chain = (
    RunnablePassthrough.assign(schema=lambda _: db.get_table_info())
    | sql_prompt
    | llm
    | StrOutputParser()
    | RunnableLambda(lambda x: re.sub(r"```sql|```|<s>|</s>", "", x, flags=re.IGNORECASE).strip())
)

# Response Generation
response_template = """As a medical analyst, translate these results:

Question: {question}
SQL Used: {query}
Results: {response}

Clinical Interpretation:"""
response_prompt = ChatPromptTemplate.from_template(response_template)

def execute_query(query: str):
    """Safe query execution"""
    try:
        return db.run(query)
    except Exception as e:
        raise ValueError(f"Query failed: {str(e)}\nQuery: {query}")

# Full production chain
full_chain = (
    RunnableParallel(
        question=RunnablePassthrough(),
        schema=lambda _: db.get_table_info()
    )
    .assign(query=sql_chain)
    .assign(response=lambda x: execute_query(x["query"]))
    .assign(
        answer=response_prompt | llm | StrOutputParser()
    )
    .with_retry(stop_after_attempt=3)
)

# FastAPI endpoints
@app.get("/generate_sql/")
async def generate_sql(question: str):
    """Generate SQL and clinical report based on the question."""
    try:
        result = full_chain.invoke(
            {"question": question},
            config={"metadata": {"user": "doctor_123"}}
        )
        
        return {
            "sql_query": result['query'],
            "clinical_report": result['answer']
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to the Patient Chat Bot SQL Generator!"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)