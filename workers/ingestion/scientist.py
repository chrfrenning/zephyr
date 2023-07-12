import os
import sys
import pandas as pd
import numpy as np
import generator

# load sample.csv into pandas
df = pd.read_csv('sample.csv')

# get column names
column_names = df.columns.values.tolist()

# get a random sample with five rows of this data
sample = df.sample(5)

# save sample as json string
sample_json = sample.to_json(orient='records')

# grounding
grounding = "You are a Data Scientist. You are working with the following dataset: " + sample_json

# describe the dataset
chat = generator.Chat(grounding)
question = "Describe the dataset in your own words."
response = chat.complete(question)
print(">>> Description: ", response)

# generate
response = chat.complete("Suggest three visualizations for this dataset. Return the results in a json document formatted like this: {\"vis1\": \"\", \"vis2\": \"\", \"vis3\": \"\"}")
print(">>> Visualisations: ", response)

# generate code
response = chat.complete("Write python code to generate a the first visualisation from the data, loading the dataset from sample.csv into pandas and plotting with matplotlib and saving to chart.png. Select the most interesting values so that the chart is easy to understand and fully readable.")
print(">>> Code: ", response)
# pick out lines between ```python and ``` in response
code = response.split("```python")[1].split("```")[0]
# save to script.py
with open("script.py", "w") as fh:
    fh.write(code)
# execute script.py
os.system("python script.py")
