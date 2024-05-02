import json

class PromptGeneration:
    def __init__(self):
        pass

    def get_suppliers_prompt(self, part):
        part_number = part["part_number"]
        part_name = part["part_name"]
        description = part["description"]

        requirements = f"'''description: {description}; part_number: {part_number}; part_name: {part_name}'''"
        prompt = f'''
        Based on current product specifications: {requirements}

        Find me the other two supplier that sell similar products with their website link references. 
        Structure your results in a VALID JSON FORMAT using below example.

        JSON example:
        '''

        json_template = json.dumps({
            'Amphenol Aerospace': 'https://www.amphenol-aerospace.com', 
            'TE Connectivity':'https://www.te.com/usa-en/home.html'
        })

        return prompt + json_template

    def filter_recommendations_prompt(self, part, product_data):
        part_number = part["part_number"]
        part_name = part["part_name"]
        description = part["description"]
        requirements = f"'''description: {description}; part_number: {part_number}; part_name: {part_name}'''"
        prompt = f'''
        Based on current product specifications: {requirements}

        Find me maximum three product name and its product links from below product JSON data that best meet requirements.
        Product JSON:
        {product_data}

        Structure your results in a VALID JSON FORMAT using below template.

        JSON Template:
        '''
        json_template = json.dumps(
                [
                {"product_name": "product_name1", "link": "product_link1"},
                {"product_name": "product_name2", "link": "product_link2"},
                {"product_name": "product_name3", "link": "product_link3"}
            ]
        )
        return prompt + json_template

    def get_search_queries_prompt(self, part):
        prompt = f'''
        Based on product specifications: {part}

        Generate three different search queries that can be used to search for above part. You cannot include part number and supplier name in the search query.
        Please limit each search query within four words.
        Structure your results in a VALID JSON FORMAT using below example.

        JSON Example:
        '''

        json_template = json.dumps(
            {
                "search_queries": ["16 pin circular connector"]
            }
        )
        return prompt+json_template
    
