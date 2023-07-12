import os
import time
from base64 import b64decode
import openai

openai.organization = os.environ['ZEPHYR_OPENAI_ORG']
openai.api_key = os.environ['ZEPHYR_OPENAI_KEY']
model = os.environ['ZEPHYR_OPENAI_MODEL']

#
# OpenAI stuff
#

class Chat:
    def __init__(self, grounding):
        self.grounding = grounding
        self.messages = []
        self.messages.append( { "role": "system", "content": grounding } )
        
    def complete(self, text):
        max_retries = 5
        while max_retries > 0:
            try:
                return self.complete_once(text)
            except openai.error.RateLimitError as e:
                print("Rate limit reached, waiting for 5 seconds...")
                time.sleep(20)
                max_retries -= 1
    
    def complete_once(self, text):
        self.messages.append( {"role": "user", "content": text} )

        response = openai.ChatCompletion.create(
            model=model,
            messages = self.messages,
            max_tokens=500,
            temperature=0.9,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        return response.choices[0].message.content


# create image from text using openai, output to image.png
def create_image(text, file_name):
    while True:
        try:
            return create_image_once(text, file_name)
        except openai.error.RateLimitError as e:
            print("Rate limit reached, waiting for 5 seconds...")
            time.sleep(20)

def create_image_once(text, file_name):
    response = openai.Image.create(prompt=text,response_format="b64_json",n=1,size="512x512")
    img_data = b64decode( response.data[0].b64_json )
    with open(file_name, "wb") as fh:
        fh.write(img_data)