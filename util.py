import pandas as pd
import json

def excel_to_json(file_path: str, output_path: str):
    try:
        df = pd.read_excel(file_path)
        
        # 1. Date Sanitization
        date_columns = ['birthdate', 'enrolled_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')

        # 2. Email Cleaning Logic
        # This replaces NaN, empty strings, or a simple hyphen with your default
        if 'email' in df.columns:
            df['email'] = df['email'].replace(['-', ''], pd.NA).fillna('unknown@gmail.com')

        # 3. Rename columns
        column_mapping = {
            'full name': 'full_name',
            'phonenumber': 'phone_number',
            'parentname': 'parent_name',
            'parentphone': 'parent_phone',
            'enrolled_date': 'enrolled_date'
        }
        df = df.rename(columns=column_mapping)
        
        # 4. Export
        result = df.to_json(orient='records', indent=4)
        with open(output_path, 'w') as f:
            f.write(result)
            
        print("Success. Data processed with email fallback applied.")
        
    except Exception as e:
        print(f"An error occurred: {e}")

# Usage
excel_to_json('20intake.xlsx', 'intake20.json')