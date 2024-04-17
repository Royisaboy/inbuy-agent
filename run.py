from utils.agent import Actions
from utils.prompt import PromptGeneration
import os
import json
import pandas as pd
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv() 
key = os.getenv("OPENAI_API_KEY")
from_email = "inbuy01@outlook.com"
password = os.getenv("EMAIL_PASSWORD")
subject = "Your supplier search results are available!"

p = PromptGeneration()
a = Actions(key)
remaining_list_of_dicts = a.fetch_sheet_latest_records("gcp_credential.json")

blobs = a.storage_client.list_blobs("infind")
suppliers = [blob.name.split("/")[-1].replace(".json", "") for blob in blobs]

for sr in remaining_list_of_dicts:
    prompt = p.get_suppliers(sr)
    supplier_info = a.get_response(prompt)
    if "results" in supplier_info:
        supplier_info = supplier_info["results"]
    logger.info("Recommending suppliers...")
    logger.info(supplier_info)

    supplier_summary_collections = []
    if supplier_info is not None:
        for supplier_name, link in supplier_info.items():
            if supplier_name in suppliers:
                logger.info(f"Scraped data for {supplier_name} exist.")
                blob = a.bucket.blob(f"inbuy/scraped_data/{supplier_name}.json")
                contents = blob.download_as_string()
                scraped_results = json.loads(contents)
            else:
                logger.info(f"Scraped data for {supplier_name} don't exist. Scraping it now...")
                scraped_results = a.scrape_web(link, 50)
                blob = a.bucket.blob(f"inbuy/scraped_data/{supplier_name}.json")
                blob.upload_from_string(json.dumps(scraped_results))
            if scraped_results is not None:
                scraped_results = a.prune_scraped_reuslts(scraped_results)
                prompt2 = p.get_recommendations(sr, scraped_results)
                if sr["image"] is not None and sr["image"] != "":
                    try:
                        product_recommendations = a.get_response(prompt2, urls=[sr["image"]])
                    except Exception as e:
                        logger.error(e)
                        product_recommendations = a.get_response(prompt2)
                else:
                    product_recommendations = a.get_response(prompt2)
                product_recommendations = a.get_response(prompt2)
                logger.info("Getting original recommendation...")
                logger.info(product_recommendations)
                product_recommendations = a.check_recommendations_accuracy(sr, product_recommendations)
                logger.info("Getting filtered recommendation...")
                logger.info(product_recommendations)
                product_recommendations_str = ' '.join([f"product_name: {pr['product_name']}, link: {pr['link']}" for pr in product_recommendations if "error" not in pr and "message" not in pr])
                if product_recommendations_str != '':
                    supplier_contact = a.search_contact(f"contact for {supplier_name}")
                    supplier_summary = a.generate_supplier_summary(sr["request_id"], supplier_name, supplier_contact, product_recommendations_str)
                    logger.info("Getting summary...")
                    logger.info(supplier_summary)
                    supplier_summary_collections.append(supplier_summary)
        email_address = sr["email"]
        a.send_email(password, from_email, email_address, subject, supplier_summary_collections)
        logger.info(f"Email sent to {email_address}.")               
