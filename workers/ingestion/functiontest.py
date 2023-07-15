import gpt
import json

chat = gpt.Chat("You are a friendly but slightly dramatic weather bot.")
chat.add_system_message("Hello, I am a weather bot. I can tell you the weather in any city.")
response = chat.complete2("What is the weather in San Francisco?")
print(json.dumps(response, indent=4, sort_keys=True))