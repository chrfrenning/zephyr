import os
import time
from base64 import b64decode
import openai

openai.organization = os.environ['ZEPHYR_OPENAI_ORG']
openai.api_key = os.environ['ZEPHYR_OPENAI_KEY']
model = os.environ['ZEPHYR_OPENAI_MODEL']

gpt_wait_response_throttling = 30 # seconds

#
# OpenAI stuff
#

class Chat:
    def __init__(self, grounding):
        self.grounding = grounding
        self.messages = []
        self.messages.append( { "role": "system", "content": grounding } )
        print("Grounding: " + grounding)
        
    def complete(self, text, temperature=0.0):
        print("Prompt: " + text)
        
        max_retries = 5
        while max_retries > 0:
            try:
                response = self.__complete_once(text, temperature)
                print("Response: " + response)
                return response
            except openai.error.RateLimitError as error:
                print(f"Rate limit reached, waiting for 5 seconds... ({error.message})")
                time.sleep(gpt_wait_response_throttling)
                max_retries -= 1

    def add_system_message(self, text):
        self.messages.append( {"role": "system", "content": text} )
    
    def __complete_once(self, text, temperature):
        self.messages.append( {"role": "user", "content": text} )

        response = openai.ChatCompletion.create(
            model=model,
            messages = self.messages,
            max_tokens=500,
            temperature=temperature,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        return response.choices[0].message.content


# create image from text using openai, output to image.png
# def create_image(text, file_name):
#     while True:
#         try:
#             return create_image_once(text, file_name)
#         except openai.error.RateLimitError as e:
#             print("Rate limit reached, waiting for 5 seconds...")
#             time.sleep(gpt_wait_response_throttling)

# def create_image_once(text, file_name):
#     response = openai.Image.create(prompt=text,response_format="b64_json",n=1,size="512x512")
#     img_data = b64decode( response.data[0].b64_json )
#     with open(file_name, "wb") as fh:
#         fh.write(img_data)