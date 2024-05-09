from utils.agent import Actions
from utils.prompt import PromptGeneration
import os
import json
import pandas as pd
from dotenv import load_dotenv
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv() 
key = os.getenv("OPENAI_API_KEY")
from_email = "inbuy01@outlook.com"
password = os.getenv("EMAIL_PASSWORD")
subject = "Your supplier search results are available!"

p = PromptGeneration()
a = Actions(key)
all_queries = a.fetch_sheet_all_records("gcp_credential.json")
blob = a.bucket.blob("inbuy/supplier_waitlist.json")
contents = blob.download_as_string()
waitlist = json.loads(contents)

for sr in all_queries:
    if sr["email_sent"] != "True":
        suppliers_prompt = p.get_suppliers(sr)
        supplier_info = a.get_response(suppliers_prompt)
        if "results" in supplier_info:
            supplier_info = supplier_info["results"]
        logger.info("Recommending suppliers...")
        logger.info(supplier_info)

        supplier_summary_collections = []
        if supplier_info is not None:
            for supplier_name, link in supplier_info.items():
                index_name = "supplier-db-" + re.sub('[^a-zA-Z]+', '', supplier_name).lower()
                if index_name not in a.pc.list_indexes().names():
                    logger.info(f"Scraped data for {supplier_name} doesn't exist. Put this suppplier in waitlist.")
                    if index_name not in waitlist:
                        waitlist.append({"index_name": index_name, "link": link})
                else:
                    logger.info(f"Scraped data for {supplier_name} exist.")
                    
                    recommendations_prompt = p.get_recommendations(sr)
                    product_recommendations = a.get_rga_response(recommendations_prompt, index_name)
                    logger.info("Getting original recommendation...")
                    logger.info(product_recommendations)
                    recommendation_accuracy_prompt = p.get_recommendation_accuracy(product_recommendations)
                    product_recommendations = a.check_recommendations_accuracy(recommendation_accuracy_prompt, sr)
                    logger.info("Getting filtered recommendation...")
                    logger.info(product_recommendations)
                    product_recommendations_str = ' '.join([f"product_name: {pr['product_name']}, link: {pr['link']}" for pr in product_recommendations if "error" not in pr and "message" not in pr])
                    if product_recommendations_str != '':
                        supplier_contact = a.get_rga_response(f"find me email contact for {supplier_name}", index_name)
                        supplier_summary = a.generate_supplier_summary(sr["request_id"], supplier_name, supplier_contact, product_recommendations_str)
                        logger.info("Getting summary...")
                        logger.info(supplier_summary)
                        supplier_summary_collections.append(supplier_summary)
        
            blob.upload_from_string(json.dumps(waitlist))
            if supplier_summary_collections != []:
                email_address = sr["email"]
                a.send_email(password, from_email, email_address, subject, supplier_summary_collections)
                logger.info(f"Email sent to {email_address}.")               
