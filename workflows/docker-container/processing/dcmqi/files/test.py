import pandas as pd
import json
import math

code_lookup_table = pd.read_csv('./code_lookup_table.csv', sep=';')
code_lookup_table = code_lookup_table[~code_lookup_table['Code Value'].apply(math.isnan)]
code_lookup_table['Code Meaning'] = code_lookup_table['Code Meaning'].str.lower()
code_lookup_table['Code Meaning'] = code_lookup_table['Code Meaning'].str.replace(" ", "-")
code_lookup_table = code_lookup_table.set_index('Code Meaning')
code_lookup_table['Code Value'] = code_lookup_table['Code Value'].apply(int)

print(code_lookup_table['Code Value'])
with open("./code_lookup_table.json") as f:
    code_lookup_table = json.load(f)

code_meaning = "Aortic arch".lower()
code_meaning_entries =  [d for d in code_lookup_table if d["Code Meaning"].lower() == code_meaning ]
if len(code_meaning_entries) == 1:
    code_value = code_meaning_entries[0]["Code Value"]
else:
    print("Multiple found!")
print("here")

