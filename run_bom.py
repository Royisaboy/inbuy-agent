from utils.agent import Actions
from utils.prompt import PromptGeneration
from utils.gpt4 import Chat
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
c = Chat(key)
all_queries = a.fetch_sheet_all_records("gcp_credential.json")

for query in all_queries:
    bom_link = query["upload_bom"]
    if bom_link is not None and bom_link != "":
        results = []
        parts = a.download_excel_file(query["spreadsheet_id_formula"])
        substitutions = []
        for part in parts:
            logger.info(f"Part Number: {part}")
            supplier_prompt = p.get_suppliers_prompt(part)
            suppliers = c.get_response(supplier_prompt)
            if "results" in suppliers:
                suppliers = suppliers["results"]
            logger.info("Recommending suppliers...")
            logger.info(suppliers)
            supplier_summary_collections = []
            if suppliers is not None:
                for supplier_name, link in suppliers.items():
                        sampled_queries = a.sample_search_queries(link, part)
                        logger.info("Sampling search queries...")
                        logger.info(sampled_queries)
                        product_recommendations = a.get_product_recommendations(part, sampled_queries)
                        product_recommendations_str = ' '.join([f"product_name: {pr['product_name']}, link: {pr['link']}" for pr in product_recommendations if "error" not in pr and "message" not in pr])
                        logger.info("getting product recommendations...")
                        logger.info(product_recommendations_str)
            substitution = {"part_number": part["part_number"], "substitutions": product_recommendations_str}
            logger.info("Suggesting substitutions...")
            logger.info(substitution)
            substitutions.append(substitution)
        logger.info("Substitution Summary")
        logger.info(substitutions)
            
        if substitutions != []:
            email_address = query["email"]
            a.send_email(password, from_email, email_address, subject, pd.DataFrame(substitutions))
            logger.info(f"Email sent to {email_address}.")    
