import sys, os
import glob
from reportlab.lib import colors
from reportlab.lib.pagesizes import *
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet
import csv
import datetime

print("")
print("#####################################################")
print("")
print("Starting statistics2pdf...")
print("")
print("#####################################################")
print("")
batch_folders = sorted([f for f in glob.glob(os.path.join('/', os.environ['WORKFLOW_DIR'], os.environ['BATCH_NAME'], '*'))])

for batch_element_dir in batch_folders:
    print("")
    print("#####################################################")
    print("")
    print("Processing element: {}".format(batch_element_dir))
    print("")
    print("#####################################################")
    print("")
    element_input_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_IN_DIR'])
    element_output_dir = os.path.join(batch_element_dir, os.environ['OPERATOR_OUT_DIR'])
    html_output_path = os.path.join(element_output_dir,"statistics.html")
    pdf_output_path = os.path.join(element_output_dir,"statistics.pdf")
    if not os.path.exists(element_output_dir):
        os.makedirs(element_output_dir)

    csv_list = glob.glob(os.path.join(element_input_dir,"*.csv"))
    if len(csv_list) == 0:
        print("############### no *.csv file found at {} ".format(element_input_dir))
        raise FileNotFoundError
    
    for csv_file in csv_list:
        print("Found CSV file: {}".format(csv_file))
        print("")
        now = datetime.datetime.now()
        line1 = 'DICOM RADIOMICS REPORT'
        line2 = 'Date: ' + now.strftime("%d-%m-%y")

        #PDF document layout
        table_style = TableStyle([('ALIGN',(1,1),(-2,-2),'RIGHT'),
                            ('TEXTCOLOR',(1,1),(-2,-2),colors.red),
                            ('VALIGN',(0,0),(0,-1),'TOP'),
                            ('TEXTCOLOR',(0,0),(0,-1),colors.blue),
                            ('ALIGN',(0,-1),(-1,-1),'CENTER'),
                            ('VALIGN',(0,-1),(-1,-1),'MIDDLE'),
                            ('TEXTCOLOR',(0,-1),(-1,-1),colors.green),
                            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                            ])
        styles = getSampleStyleSheet()
        styleNormal = styles['Normal']
        styleHeading = styles['Heading1']
        styleHeading2 = styles['Heading2']
        styleHeading.alignment = 1 # centre text (TA_CENTRE)

        #Configure style and word wrap
        s = getSampleStyleSheet()
        s = s["BodyText"]
        s.wordWrap = 'CJK'

        # File that must be written to report
        with open(csv_file, "r") as csvfile:
            reader = csv.reader(csvfile,delimiter=';')
            lista = list(reader)

        headers = lista[0]
        conteo = 1

        for numRecord in range(1,len(lista)):
            record1 = lista[numRecord]
            data = list()
            emptyRecords = list()
            records = list()
            header = list()
            countRecords = 0

            for line in record1:

                if line == '':
                    emptyRecords.append(line)
                else:
                    records.append(line)
                    header.append(headers[countRecords])

                    data.append([str(headers[countRecords]), str(line)])

                countRecords = countRecords + 1

            data2 = [[Paragraph(cell, s) for cell in row] for row in data]
            t = Table(data2)
            t.setStyle(table_style)
            elements = []
            # Name of file
            conteo = conteo + 1
            print(f" Writing PDF to {pdf_output_path}")
            archivo_pdf = SimpleDocTemplate(pdf_output_path, pagesize = letter, rightMargin = 40, leftMargin = 40, topMargin = 40, bottomMargin = 28)
            #Send the data and build the file
            elements.append(Paragraph(line1, styleNormal))
            elements.append(Paragraph(line2, styleNormal))
            elements.append(Spacer(inch, .25*inch))
            elements.append(t)
            archivo_pdf.build(elements)

        print("")
        print("##################################################")
        print("")
