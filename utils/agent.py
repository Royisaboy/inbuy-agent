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
# import gdown
import uuid
from google.cloud import storage

class Actions(chat):
    def __init__(self, key):
        super().__init__(key)
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
        
    def search_product_link(self, query):
        try:
            url = f"https://www.googleapis.com/customsearch/v1?key=AIzaSyD6hSd8BCa-VYtNCyIMFFgIOD93xsl_HEc&cx=84249567808554f8e&q={query}"
            search_reulsts = request("GET", url).json()
            return search_reulsts["items"][0]["link"]
        except Exception:
            return ""
        
    def check_recommendations_accuracy(self, description, recommendations):
        p = PromptGeneration()
        prompt = p.get_recommendation_accuracy(description, recommendations)
        product_recommendations = self.get_response(prompt)
        if "results" in product_recommendations or "products" in product_recommendations:
            product_recommendations = list(product_recommendations.values())[0]
        else:
            product_recommendations = [product_recommendations]
        return product_recommendations
    
    def fetch_sheet_latest_records(self, gcp_credential_dir):
        gc = gspread.service_account(filename=gcp_credential_dir)
        sht2 = gc.open_by_url('https://docs.google.com/spreadsheets/d/1EODc6xDvF8vS-R4JH1VleKhxwQlhhhF27fGu9Upd1pg/')
        worksheet = sht2.get_worksheet(0)
        list_of_dicts = worksheet.get_all_records()
        with open("data/google_sheet_history.json", "r") as f_in:
            current_position = json.load(f_in)["current_position"]
        remaining_list_of_dicts = list_of_dicts[current_position:]
        
        modified = []
        for d in remaining_list_of_dicts:
            request_id = str(uuid.uuid4())
            d["request_id"] = request_id
            modified.append(d)
            blob = self.bucket.blob(f"inbuy/logs/{request_id}/request.json")
            blob.upload_from_string(json.dumps(d))
        new_position = current_position + len(modified)
        with open("data/google_sheet_history.json", "w") as f_out:
            json.dump({"current_position": new_position}, f_out)
        return modified
    
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
    
    def prune_scraped_reuslts(self, s):
        while len(json.dumps(s)) > 32000:
            if len(s) == 1:
                first_element = s[0]
                first_element["html"] = first_element["html"][:32000]
                s = [first_element]
            else:
                s = s[:-1]
        return s