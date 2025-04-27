from pathlib import Path
import pandas as pd
import os
import sqlite3

# Get the current file path
current_file_path = Path(__file__).resolve()
# Get the data/db path
root = current_file_path.parents[3]
data_path = os.path.join(root,'data/raw_data')
db_path = os.path.join(root,'data/database')

#Connect to SQLite (creates database if it doesn't exist)
conn = sqlite3.connect(f'{db_path}/patient_data.db')
cursor = conn.cursor()

# Read the CSV files
PatientData = pd.read_csv(f'{data_path}/Health_Dataset_1.csv')
PhysicalActivityData = pd.read_csv(f'{data_path}/Health_Dataset_2.csv')


cursor.execute('''
CREATE TABLE PatientData (
    Patient_Number INTEGER PRIMARY KEY,
    Blood_Pressure_Abnormality INTEGER, -- 0=Normal, 1=Abnormal
    Level_of_Hemoglobin REAL, -- (g/dl)
    Genetic_Pedigree_Coefficient REAL,
    Age INTEGER,
    BMI REAL,
    Sex INTEGER CHECK (Sex IN (0,1)), -- 0=Male, 1=Female
    Pregnancy INTEGER, -- 0=No, 1=Yes
    Smoking INTEGER CHECK (Smoking IN (0,1)), -- 0=No, 1=Yes
    Salt_Content_in_the_Diet REAL, -- (mg per day)
    Alcohol_Consumption_Per_Day REAL, -- (ml per day)
    Level_of_Stress INTEGER, -- 1=Low, 2=Normal, 3=High
    Chronic_Kidney_Disease INTEGER, -- 0=No, 1=Yes
    Adrenal_and_Thyroid_Disorders INTEGER -- 0=No, 1=Yes
);
''')

cursor.execute('''
CREATE TABLE PhysicalActivityData (
    Patient_Number INTEGER,
    Day_Number INTEGER,
    Physical_Activity REAL,
    PRIMARY KEY (Patient_Number, Day_Number),
    FOREIGN KEY (Patient_Number) REFERENCES PatientData(Patient_Number)
);
''')

conn.commit()

# Insert data only if tables were empty (optional safety)
PatientData.to_sql('PatientData', conn, if_exists='append', index=False)
PhysicalActivityData.to_sql('Table2', conn, if_exists='append', index=False)

# Close connection
conn.close()

print("Tables created if missing, data loaded, foreign key set.")
