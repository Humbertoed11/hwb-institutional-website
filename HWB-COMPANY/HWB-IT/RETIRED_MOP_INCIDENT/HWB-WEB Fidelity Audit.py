import pandas as pd
import os

def run_fidelity_audit(file_path):
    print(f"--- SigmaFidelity: Initiating Data Audit for {file_path} ---")
    
    if not os.path.exists(file_path):
        print("Error: Target file not found.")
        return

    # 1. Load Data
    df = pd.read_csv(file_path)
    initial_count = len(df)

    # 2. Duplicate Removal (The Anti-Spam Filter)
    # We drop any entry with the same Company and City
    df = df.drop_duplicates(subset=['Company_Name', 'City'], keep='first')
    duplicate_count = initial_count - len(df)

    # 3. Data Cleaning
    # Ensure ZIP codes are strings and exactly 5 digits
    df['Zip'] = df['Zip'].astype(str).str.zfill(5)
    
    # Standardize Phone Format
    df['Phone'] = df['Phone'].str.replace(r'[^0-9]', '', regex=True)
    
    # 4. Fidelity Scoring Logic
    # Every lead starts with 100 points. We subtract for missing critical data.
    df['Fidelity_Score'] = 100
    df.loc[df['Email'].isnull(), 'Fidelity_Score'] -= 20
    df.loc[df['Phone'].isnull(), 'Fidelity_Score'] -= 30
    
    # 5. Segmenting by City for the "Regional Sweep"
    city_counts = df['City'].value_counts()

    # 6. Save the Audit-Ready List
    output_file = "distribution_centers_AUDITED_v1.csv"
    df.to_csv(output_file, index=False)

    print(f"Audit Summary:")
    print(f"- Initial Leads: {initial_count}")
    print(f"- Duplicates Removed: {duplicate_count}")
    print(f"- Final Verified Leads: {len(df)}")
    print(f"- Regional Reach: {len(city_counts)} Cities")
    print(f"--- SUCCESS: {output_file} is now the single source of truth ---")

if __name__ == "__main__":
    # We audit our latest verified master list
    run_fidelity_audit("distribution_centers_verified_5000.csv")
