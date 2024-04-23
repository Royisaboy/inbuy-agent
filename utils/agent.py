import json
import re
from requests import request
from utils.gpt4 import chat
import smtplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import gspread
from utils.prompt import PromptGeneration
import pandas as pd
import gdown
import uuid
from google.cloud import storage
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

class Actions(chat):
    def __init__(self, key):
        super().__init__(key)
        self.storage_client = storage.Client.from_service_account_json('gcp_credential.json')
        self.bucket = self.storage_client.bucket("infind")


    def extract_email_addresses(self, text):
        pattern = r'[\w\.-]+@[\w\.-]+(?:\.[\w]+)+'
        match = re.search(pattern, text)
        if match is not None:
            return match.group(0)
        else:
            return match

    def send_email(self, password, from_email, to_email, subject, supplier_summary_collections):
        df_html = pd.DataFrame(supplier_summary_collections).to_html()
        body = f"""
        <html>
            <head></head>
            <body>
                <p>Hi Yanfu,</p>
                <p>Here are your match results:</p>
                <p>{df_html}<p>
                <p>Thanks,<p>
                <p>Inbuy Team<p>
            </body>
        </html>
        """

        HOST = "smtp-mail.outlook.com"
        PORT = 587

        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = from_email
        message['To'] = to_email

        message.attach(MIMEText(body, 'html'))

        smtp = smtplib.SMTP(HOST, PORT)
        status_code, response = smtp.ehlo()
        status_code, response = smtp.starttls()
        status_code, response = smtp.login(from_email, password)
        smtp.sendmail(from_email, to_email, message.as_string())
        smtp.quit()

        
    def check_recommendations_accuracy(self, prompt):
        product_recommendations = self.get_response(prompt)
        if "results" in product_recommendations or "products" in product_recommendations:
            product_recommendations = list(product_recommendations.values())[0]
        else:
            product_recommendations = [product_recommendations]
        return product_recommendations
    
    def fetch_sheet_all_records(self, gcp_credential_dir):
        gc = gspread.service_account(filename=gcp_credential_dir)
        sht2 = gc.open_by_url('https://docs.google.com/spreadsheets/d/1EODc6xDvF8vS-R4JH1VleKhxwQlhhhF27fGu9Upd1pg/')
        worksheet = sht2.get_worksheet(0)
        return worksheet.get_all_records()
    
    def generate_supplier_summary(self, request_id, supplier_name, supplier_contact, product_recommendations_str):
        
        if supplier_contact == "":
            rfq_status = "Pending"
        elif "@" in supplier_contact:
            rfq_status = "Sent"
        else:
            rfq_status = "Pending"
        supplier_summary = {
            "supplier_name": supplier_name,
            "contact": supplier_contact,
            "product_recommendations": product_recommendations_str,
            "rfq_status": rfq_status
            }
        blob = self.bucket.blob(f"inbuy/logs/{request_id}/recommendations.json")
        blob.upload_from_string(json.dumps(supplier_summary))
        return supplier_summary

    def download_excel_file(self, real_file_id):
        creds = service_account.Credentials.from_service_account_json('gcp_credential.json')

        try:
            # create drive api client
            service = build("drive", "v3", credentials=creds)

            # pylint: disable=maybe-no-member
            request = service.files().get_media(fileId=real_file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}.")
            # Use BytesIO to convert bytes to a file-like object that pandas can read
            data = io.BytesIO(file.getvalue())

            # Read the Excel file from the file-like object
            return pd.read_excel(data).to_dict("records")
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None



