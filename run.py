from utils.agent import Actions
from utils.prompt import PromptGeneration
import os
import json
import pandas as pd
from dotenv import load_dotenv
import logging

load_dotenv() 
key = os.getenv("OPENAI_API_KEY")
from_email = "inbuy01@outlook.com"
to_email = "akshayh1993@gmail.com, zhuyanfu0712@gmail.com"
password = "Akshay1993"
subject = "Your supplier search results are available!"

p = PromptGeneration()
a = Actions(key)
remaining_list_of_dicts = a.fetch_sheet_latest_records("gcp_credential.json")

with open("data/scraped_results.json", "r") as f:
    scrape_history = json.load(f)

for sr in remaining_list_of_dicts:
    prompt = p.get_suppliers(sr)
    supplier_info = a.get_response(prompt)
    if "results" in supplier_info:
        supplier_info = supplier_info["results"]
    logging.info("Recommending suppliers...")
    logging.info(supplier_info)

    supplier_summary_collections = []
    if supplier_info is not None:
        for supplier_name, link in supplier_info.items():
            if link in scrape_history:
                scraped_results = scrape_history[link]
            else:
                scraped_results = a.scrape_web(link, 50)
                scrape_history[link] = scraped_results
                with open("data/scraped_results.json", "w") as f:
                    json.dump(scrape_history, f)
            if scraped_results is not None:
                scraped_results = a.prune_scraped_reuslts(scraped_results)
                prompt2 = p.get_recommendations(sr, scraped_results)
                if sr["image"] is not None and sr["image"] != "":
                    product_recommendations = a.get_response(prompt2, urls=[sr["image"]])
                else:
                    product_recommendations = a.get_response(prompt2)
                product_recommendations = a.get_response(prompt2)
                logging.info("Getting original recommendation...")
                logging.info(product_recommendations)
                product_recommendations = a.check_recommendations_accuracy(sr, product_recommendations)
                logging.info("Getting filtered recommendation...")
                logging.info(product_recommendations)
                product_recommendations_str = ' '.join([f"product_name: {pr['product_name']}, link: {pr['link']}" for pr in product_recommendations if "error" not in pr and "message" not in pr])
                if product_recommendations_str != '':
                    supplier_contact = a.search_contact(f"contact for {supplier_name}")
                    supplier_summary = a.generate_supplier_summary(sr["request_id"], supplier_name, supplier_contact, product_recommendations_str)
                    logging.info("Getting summary...")
                    logging.info(supplier_summary)
                    supplier_summary_collections.append(supplier_summary)
        a.send_email(password, from_email, to_email, subject, supplier_summary_collections)                
