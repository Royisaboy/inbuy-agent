from openai import OpenAI
import json

class chat:

    def __init__(self, key):
        self.client = OpenAI(api_key=key)

    def get_response(self, text_prompt, urls=None):
        if urls is None:
            prompt = [{"role": "user", "content": text_prompt}]
        else:
            text_prompt = [{"type": "text", "text": text_prompt}]
            image_prompt = [{"type": "image_url", "image_url": {"url": url}} for url in urls]
            prompt = [{"role": "user", "content": text_prompt+image_prompt}]
        chat_response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=prompt
        )
        latest_message = chat_response.choices[0].message
        return json.loads(latest_message.content)
    