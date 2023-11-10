import os
import requests
import csv
import re

url = "http://api.powertochoose.org/api/PowerToChoose/plans"
params = {'zip_code': '78681', 'plan_mo_from': '6', 'plan_mo_to': '12'}

headers = {
    'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

try:
    response = requests.get(url, params=params, headers=headers)
    data = response.json()

    if response.status_code == 200 and data.get('success', False):
        plans = data.get('data', [])

        # Extract relevant information
        extracted_data = [{
            'company_name': plan['company_name'],
            'plan_name': plan['plan_name'],
            'special_terms': plan['special_terms'],
            'rate_type': plan['rate_type'],
            'term_value': plan['term_value'],
            'price_kwh500': plan['price_kwh500'],
            'price_kwh1000': plan['price_kwh1000'],
            'price_kwh2000': plan['price_kwh2000'],
            'fact_sheet': plan['fact_sheet'],
            'minimum_usage': plan['minimum_usage'],
        } for plan in plans]

        # Save the data to a CSV file
        csv_filename = 'power_plans_data.csv'
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'company_name', 'plan_name', 'special_terms', 'rate_type',
                'term_value', 'price_kwh500', 'price_kwh1000', 'price_kwh2000',
                'fact_sheet', 'minimum_usage'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in extracted_data:
                writer.writerow(row)

                # Download PDFs and save to fact_sheets folder
                fact_sheet_url = row['fact_sheet']

                print(f"fact_sheet_url = {fact_sheet_url}")
                pdf_response = requests.get(fact_sheet_url)
                print(f"pdf_response = {pdf_response}")
                pdf_content = pdf_response.content

                # Remove special characters from the generated file name
                pdf_name = re.sub(r'[^a-zA-Z0-9\s]', '',
                                  row['company_name'] + '_' + row['plan_name'])

                fact_sheets_folder = 'fact_sheets'
                os.makedirs(fact_sheets_folder, exist_ok=True)

                pdf_path = os.path.join(fact_sheets_folder, pdf_name + '.pdf')
                with open(pdf_path, 'wb') as pdf_file:
                    pdf_file.write(pdf_content)

                print(f"Downloaded and saved PDF: {pdf_path}")

        print(f"Data and PDFs saved successfully.")
    else:
        print(f"Request failed with status code: {response.status_code}")
        print(data)

except requests.RequestException as e:
    print(f"An error occurred: {e}")
