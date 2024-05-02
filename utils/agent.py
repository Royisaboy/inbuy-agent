import json
import re
from requests import request
from utils.gpt4 import Chat
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

class Actions:
    def __init__(self, key):
        self.c = Chat(key)
        self.p = PromptGeneration()
        self.storage_client = storage.Client.from_service_account_json('gcp_credential.json')
        self.bucket = self.storage_client.bucket("infind")

    def scrape_web(self, url, max_pages):
        payload = json.dumps({
            "url": url,
            "match": f"{url}/**",
            "maxPagesToCrawl": max_pages,
            "outputFileName": "output.json",
            "maxTokens": 2000000
        })
        headers = {
            'Content-Type': 'application/json'
        }
        response = request("POST", "http://localhost:3000/crawl", headers=headers, data=payload)
        return response.json()



    def extract_email_addresses(self, text):
        pattern = r'[\w\.-]+@[\w\.-]+(?:\.[\w]+)+'
        match = re.search(pattern, text)
        if match is not None:
            return match.group(0)
        else:
            return match

    def extract_phone_numbers(self, text):
        pattern = r'\+?\d[\d -]{8,}\d'
        match = re.search(pattern, text)
        if match is not None:
            return match.group(0)
        else:
            return match

    def find_email_or_phone(self, text):
        if text is None:
            return None  # Return None or handle appropriately if text is None
        contact = self.extract_email_addresses(text)
        if contact is None:
            contact = self.extract_phone_numbers(text)
        return contact
    
    def find_email_or_phone_recursively(self, scrape_web):
        contacts = []
        for r in scrape_web:
            contact = self.find_email_or_phone(r["html"])
            if contact is not None:
                contacts.append(contact)
        return ", ".join(list(set(contacts)))

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

    def search_contact(self, query):
        url = f"https://www.googleapis.com/customsearch/v1?key=AIzaSyD6hSd8BCa-VYtNCyIMFFgIOD93xsl_HEc&cx=84249567808554f8e&q={query}"
        search_reulsts = request("GET", url).json()
        if "items" not in search_reulsts:
            return ""
        contact_url = search_reulsts["items"][0]["link"]
        crawl_contact_results = self.scrape_web(contact_url, 3)
        contact = self.find_email_or_phone_recursively(crawl_contact_results)
        if contact is not None:
            return contact
        else:
            return ""

    def search_product_links(self, query):
            # try:
            url = f"https://www.googleapis.com/customsearch/v1?key=AIzaSyD6hSd8BCa-VYtNCyIMFFgIOD93xsl_HEc&cx=84249567808554f8e&q={query}"
            search_reulsts = request("GET", url).json()
            if "items" in search_reulsts:
                item_count = len(search_reulsts["items"])
                if item_count > 3:
                    return [item["link"] for item in search_reulsts["items"][:3]]
                else:
                    return [item["link"] for item in search_reulsts["items"]]
            else:
                return []
    
    def fetch_sheet_all_records(self, gcp_credential_dir):
        gc = gspread.service_account(filename=gcp_credential_dir)
        sht2 = gc.open_by_url('https://docs.google.com/spreadsheets/d/1EODc6xDvF8vS-R4JH1VleKhxwQlhhhF27fGu9Upd1pg/')
        worksheet = sht2.get_worksheet(0)
        return worksheet.get_all_records()
    
    def generate_supplier_summary(self, supplier_name, supplier_contact, product_recommendations_str):
        
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
        return supplier_summary

    
    def download_excel_file(self, real_file_id):
        creds = service_account.Credentials.from_service_account_file('gcp_credential.json')

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

    def sample_search_queries(self, link, part):
        sample_queries_prompt = self.p.get_search_queries_prompt(part)
        sample_queries = self.c.get_response(sample_queries_prompt)["search_queries"]
        sample_queries = [f"site: {link} {q}" for q in sample_queries]
        return sample_queries

    def get_product_recommendations(self, part, sampled_queries):
        product_links = []
        for q in sampled_queries:
            product_links += self.search_product_links(q)
        product_contents = []
        for link in product_links:
            product_contents += self.scrape_web(link, 1)
        filter_recommendations_prompt = self.p.filter_recommendations_prompt(part, product_contents)
        product_recommendations = self.c.get_response(filter_recommendations_prompt)
        if "results" in product_recommendations or "products" in product_recommendations:
            product_recommendations = list(product_recommendations.values())[0]
        else:
            product_recommendations = [product_recommendations]
        return product_recommendations