import json

class PromptGeneration:
    def __init__(self):
        pass

    def get_suppliers(self, supplier_dict):
        description = supplier_dict["description"]
        tech_specs = supplier_dict["tech_specs"]
        industry = supplier_dict["industry"]
        geo = supplier_dict["geo"]
        supplier_reqs = supplier_dict["supplier_reqs"]
        requirements = f"'''description: {description}; tech_specs: {tech_specs}; product_industry: {industry}; supplier_geo_preference: {geo}; supplier_selection_criteria: {supplier_reqs};'''"
        prompt = f'''
        Based on client requirements: {requirements}

        Find me a list of maximum 15 suppliers that sell products that fit above requirements. 
        Structure your results in a VALID JSON FORMAT using below template.

        JSON Template:
        '''
        json_template = json.dumps({
            "supplierName1": "website1",
            "supplierName2": "website2",
            "supplierName3": "website3"
        })
        return prompt + json_template

    
    def get_recommendations(self, supplier_dict):
        description = supplier_dict["description"]
        tech_specs = supplier_dict["tech_specs"]
        industry = supplier_dict["industry"]
        requirements = f"'''description: {description}; tech_specs: {tech_specs}; product_industry: {industry}'''"
        prompt = f'''
        Based on client requirements: {requirements}

        Find me maximum five products with product names, short descriptions and product links that exactly meet requirements.
        Structure your results in a VALID JSON FORMAT using below template.

        JSON Template:
        '''
        json_template = json.dumps(
                [
                {"product_name": "product_name1", "short_description": "short_description1", "link": "product_link1"},
                {"product_name": "product_name2", "short_description": "short_description1", "link": "product_link2"},
                {"product_name": "product_name3", "short_description": "short_description1", "link": "product_link3"}
            ]
        )
        return prompt + json_template
    
    
    def get_recommendation_accuracy(self, supplier_dict, recommendations):
        description = supplier_dict["description"]
        tech_specs = supplier_dict["tech_specs"]
        industry = supplier_dict["industry"]
        requirements = f"'''description: {description}; tech_specs: {tech_specs}; product_industry: {industry}'''"
        prompt = f'''
        Based on client requirements: {requirements}

        Remove irrelevant products from the below recommendations that don't meet above requirements.

        {recommendations}

        Structure your results in a VALID JSON FORMAT using below template.
        '''
        json_template = json.dumps(
                [
                {"product_name": "product_name1", "link": "product_link1"},
                {"product_name": "product_name2", "link": "product_link2"},
                {"product_name": "product_name3", "link": "product_link3"}
            ]
        )
        return prompt + json_template