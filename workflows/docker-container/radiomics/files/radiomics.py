import csv
import os
import json
import glob


def read_results(path):
    radiomics_json = {}
    with open(path, 'r') as fp:
        reader = csv.reader(fp, delimiter=';', quotechar='"')
        # next(reader, None)  # skip the headers
        radiomics_results = [row for row in reader]
    

    for key_id in range(len(radiomics_results[0])-1):
        value = radiomics_results[1][key_id]
        isNum = value.replace('.', '', 1).replace('-','',1).replace('e+','',1).replace('e-','',1).isdigit()
        if isNum:
            value=float(value)
            if value > 99999999999999:
              value=0
            key = radiomics_results[0][key_id]+"_float"
        else:
            key = radiomics_results[0][key_id]+"_keyword"
        radiomics_json[key] = value


    return radiomics_json


if __name__ == "__main__":

    csv_file = os.getenv("CSV_FILE")
    json_file = os.getenv("JSON_FILE")

    print("CSV file: %s" % csv_file)
    radicomics_data = read_results(csv_file)
    filename = os.path.basename(csv_file).split(".cs")[0]
    base_json = {'radiomics_object': radicomics_data}
    with open(json_file, 'w') as outfile:
        json.dump(base_json, outfile)

    print("CSV2JSON done!")
