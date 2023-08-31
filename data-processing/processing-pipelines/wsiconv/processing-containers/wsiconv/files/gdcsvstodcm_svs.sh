#!/bin/sh
#
# Usage: ./gdcsvstodcm_svs.sh projectdirname/filename.svs [outdir]
echo "Copyright (c) 2001-2022, David A. Clunie DBA PixelMed Publishing. All rights reserved."

infile="$1"
outdir="$2"

TMPJSONFILE="/tmp/`basename $0`.$$"

# these persist across invocations ...
FILEMAPPINGSPECIMENIDTOUID="TCGAspecimenIDToUIDMap.csv"
FILEMAPPINGSTUDYIDTOUID="TCGAstudyIDToUIDMap.csv"
FILEMAPPINGSTUDYIDTODATETIME="TCGAstudyIDToDateTimeMap.csv"

UIDMAPPINGFILE="tcga_tabulateduids.csv"
TMPSLIDEUIDFILE="slideuid.csv"

#JHOVE="${HOME}/work/jhove/jhove"


#PIXELMEDDIR="${HOME}/work/pixelmed/imgbook"
PIXELMEDDIR="/kaapana/app/idc-wsi-conversion"
PATHTOADDITIONAL="${PIXELMEDDIR}/lib/additional"

filename=`basename "${infile}" '.svs'`
echo "$filename"


# "TCGA-GBM/TCGA-12-0819-01A-01-TS1.f94b9687-a5b8-4390-bd23-c913769e45be.svs"
# "TCGA-BRCA/TCGA-A2-A1G0-01Z-00-DX1.9ECB0B8A-EF4E-45A9-82AC-EF36375DEF65.svs"
# "TCGA-DLBC/0c159ca4-c2ed-4a69-bc8d-59611f2122ec/TCGA-GR-A4D9-01A-01-TS1.53C66BD8-5D6B-4685-9A6B-CABDEEC126ED.svs"
# "TCGA-DLBC/0c159ca4-c2ed-4a69-bc8d-59611f2122ec/TCGA-GR-A4D9-01A-01-TS1.53C66BD8-5D6B-4685-9A6B-CABDEEC126ED.svs"
# "TCGA-PRAD/dae680cf-fc39-4da7-8326-ffbb82af9f35/TCGA-HC-7819-01A-01-TS1.svs" ... very occasionally the uuid after the Tissue slide ID and number is missing

# the project name is NOT in the file name ...
tcgaproject=`dirname "${infile}" | sed -e 's/^.*\(TCGA-[A-Z][A-Z]*\).*$/\1/'`

if [ -z "${outdir}" ]
then
	outdir=$WORKFLOW_DIR/$OPERATOR_OUT_DIR/${filename}
fi

tcgatissuesourcesite=`echo "${filename}" | sed -e 's/^TCGA-\([0-9A-Z]*\).*$/\1/'`
tcgaparticipant=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-\([0-9A-Z]*\).*$/\1/'`
tcgasample=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-[0-9A-Z]*-\([0-9]*\).*$/\1/'`
tcgavial=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-[0-9A-Z]*-[0-9]*\([A-Z]*\).*$/\1/'`
tcgaportion=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-[0-9A-Z]*-[0-9]*[A-Z]*-\([0-9]*\).*$/\1/'`
# tcgaanalyte seems to be missing for slides
tcgaanalyte=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-[0-9A-Z]*-[0-9]*[A-Z]*-[0-9]*\([A-Z]*\).*$/\1/'`
# "Tissue slide ID can be 'TS' ('Top Slide'), 'BS' ('Bottom Slide') or 'MS' ('Middle slide'), followed by a number or letter to indicate slide order"
# "The difference can be found by looking at the particular filename, where files with “TS#” or “BS#”, where # is an integer, is a frozen slide ... While files with “DX#”, again where # is an integer, is an FFPE slide"
# do not insist on [.] after Tissue slide ID and number, else will fail when trailing uuid is missing
tcgatissueslideidtype=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-[0-9A-Z]*-[0-9]*[A-Z]*-[0-9]*[A-Z]*-\([TBMD][SX]\)[0-9A-Z]*.*$/\1/'`
tcgatissueslideidnumber=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-[0-9A-Z]*-[0-9]*[A-Z]*-[0-9]*[A-Z]*-[TBMD][SX]\([0-9A-Z]*\).*$/\1/'`
tcgafileguid=`echo "${filename}" | sed -e 's/^TCGA-[0-9A-Z]*-[0-9A-Z]*-[0-9A-Z-]*[.]\([0-9a-fA-F-]*\)$/\1/'`

echo "infile = ${infile}"
echo "filename = ${filename}"
echo "tcgaproject = ${tcgaproject}"
echo "tcgatissuesourcesite = ${tcgatissuesourcesite}"
echo "tcgaparticipant = ${tcgaparticipant}"
echo "tcgasample = ${tcgasample}"
echo "tcgavial = ${tcgavial}"
echo "tcgaportion = ${tcgaportion}"
echo "tcgaanalyte = ${tcgaanalyte}"
echo "tcgatissueslideidtype = ${tcgatissueslideidtype}"
echo "tcgatissueslideidnumber = ${tcgatissueslideidnumber}"
echo "tcgafileguid = ${tcgafileguid}"

slidefilenameforuid="${filename}"
echo "slidefilenameforuid = ${slidefilenameforuid}"

echo "TMPSLIDEUIDFILE = ${TMPSLIDEUIDFILE}"
rm -f "${TMPSLIDEUIDFILE}"
uidarg=""
if [ -f  "${UIDMAPPINGFILE}" ]
then
	egrep "(Filename|${slidefilenameforuid})" "${UIDMAPPINGFILE}" > "${TMPSLIDEUIDFILE}"
	uidarg="UIDFILE ${TMPSLIDEUIDFILE}"
fi
echo "uidarg = ${uidarg}"

# TCIA pattern for radiology is same string for PatientName and PatientID
# GDC and TCIA do not include project in patient ID, i.e., do not use ${tcgaproject} as prefix, but just "TCGA"
dicompatientid="TCGA-${tcgatissuesourcesite}-${tcgaparticipant}"
dicompatientname="${dicompatientid}"
# make study, accession same as case (patient)
# ideally would make sure these are no longer than 16 chars ... assume it for now :(
dicomstudyid="${dicompatientid}"
dicomaccessionnumber="${dicompatientid}"
# specimen is the tissue section on the slide
dicomspecimenidentifier="${dicompatientid}-${tcgasample}${tcgavial}-${tcgaportion}${tcgaanalyte}-${tcgatissueslideidtype}${tcgatissueslideidnumber}"
# container is the slide
dicomcontaineridentifier="${dicomspecimenidentifier}"

# parent specimen that is assumed to be block (for fixation) is portionanalyte
dicomparentspecimenportionanalyteidentifier="${dicompatientid}-${tcgasample}${tcgavial}-${tcgaportion}${tcgaanalyte}"
# parent specimen that of portionanalyte block is vial
dicomparentspecimenvialidentifier="${dicompatientid}-${tcgasample}${tcgavial}"
# parent specimen that of vial block is sample
dicomparentspecimensampleidentifier="${dicompatientid}-${tcgasample}"

#dicomclinicaltrialcoordinatingcentername="GDC (IDC)"
dicomclinicaltrialcoordinatingcentername="NCI Genomic Data Commons (GDC) - Imaging Data Commons (IDC)"
dicomclinicaltrialsponsorname="TCGA"
dicomclinicalprotocolid="${tcgaproject}"

anatomycodevalue=""
anatomycsd="SCT"
anatomycodemeaning=""

# https://gdc.cancer.gov/resources-tcga-users/tcga-code-tables/tcga-study-abbreviations
# should make this a table lookupo from a separate text file :
if [ "${tcgaproject}" = "TCGA-LAML" ]
then
	dicomclinicalprotocolname="TCGA Acute Myeloid Leukemia"
	anatomycodevalue="14016003"
	anatomycodemeaning="Bone marrow"
elif [ "${tcgaproject}" = "TCGA-ACC" ]
then
	dicomclinicalprotocolname="TCGA Adrenocortical carcinoma"
	# not in SNOMED-DICOM subset - need CP to add it :(
	anatomycodevalue="68594002"
	anatomycodemeaning="Adrenal cortex"
elif [ "${tcgaproject}" = "TCGA-BLCA" ]
then
	dicomclinicalprotocolname="TCGA Bladder Urothelial Carcinoma"
	anatomycodevalue="89837001"
	anatomycodemeaning="Bladder"
elif [ "${tcgaproject}" = "TCGA-LGG" ]
then
	dicomclinicalprotocolname="TCGA Brain Lower Grade Glioma"
	anatomycodevalue="12738006"
	anatomycodemeaning="Brain"
elif [ "${tcgaproject}" = "TCGA-BRCA" ]
then
	dicomclinicalprotocolname="TCGA Breast invasive carcinoma"
	anatomycodevalue="76752008"
	anatomycodemeaning="Breast"
elif [ "${tcgaproject}" = "TCGA-CESC" ]
then
	dicomclinicalprotocolname="TCGA Cervical squamous cell, endocervical adeno, carcinoma"
	anatomycodevalue="71252005"
	anatomycodemeaning="Cervix"
elif [ "${tcgaproject}" = "TCGA-CHOL" ]
then
	dicomclinicalprotocolname="TCGA Cholangiocarcinoma"
	anatomycodevalue="28273000"
	anatomycodemeaning="Bile duct"
elif [ "${tcgaproject}" = "TCGA-LCML" ]
then
	dicomclinicalprotocolname="TCGA Chronic Myelogenous Leukemia"
	anatomycodevalue="14016003"
	anatomycodemeaning="Bone marrow"
elif [ "${tcgaproject}" = "TCGA-COAD" ]
then
	dicomclinicalprotocolname="TCGA Colon adenocarcinoma"
	anatomycodevalue="71854001"
	anatomycodemeaning="Colon"
elif [ "${tcgaproject}" = "TCGA-CNTL" ]
then
	dicomclinicalprotocolname="TCGA Controls"
elif [ "${tcgaproject}" = "TCGA-ESCA" ]
then
	dicomclinicalprotocolname="TCGA Esophageal carcinoma"
	anatomycodevalue="32849002"
	anatomycodemeaning="Esophagus"
elif [ "${tcgaproject}" = "TCGA-FPPP" ]
then
	dicomclinicalprotocolname="TCGA FFPE Pilot Phase II"
elif [ "${tcgaproject}" = "TCGA-GBM" ]
then
	dicomclinicalprotocolname="TCGA Glioblastoma multiforme"
	anatomycodevalue="12738006"
	anatomycodemeaning="Brain"
elif [ "${tcgaproject}" = "TCGA-HNSC" ]
then
	dicomclinicalprotocolname="TCGA Head and Neck squamous cell carcinoma"
	anatomycodevalue="774007"
	anatomycodemeaning="Head and Neck"
elif [ "${tcgaproject}" = "TCGA-KICH" ]
then
	dicomclinicalprotocolname="TCGA Kidney Chromophobe"
	anatomycodevalue="64033007"
	anatomycodemeaning="Kidney"
elif [ "${tcgaproject}" = "TCGA-KIRC" ]
then
	dicomclinicalprotocolname="TCGA Kidney renal clear cell carcinoma"
	anatomycodevalue="64033007"
	anatomycodemeaning="Kidney"
elif [ "${tcgaproject}" = "TCGA-KIRP" ]
then
	dicomclinicalprotocolname="TCGA Kidney renal papillary cell carcinoma"
	anatomycodevalue="64033007"
	anatomycodemeaning="Kidney"
elif [ "${tcgaproject}" = "TCGA-LIHC" ]
then
	dicomclinicalprotocolname="TCGA Liver hepatocellular carcinoma"
	anatomycodevalue="10200004"
	anatomycodemeaning="Liver"
elif [ "${tcgaproject}" = "TCGA-LUAD" ]
then
	dicomclinicalprotocolname="TCGA Lung adenocarcinoma"
	anatomycodevalue="39607008"
	anatomycodemeaning="Lung"
elif [ "${tcgaproject}" = "TCGA-LUSC" ]
then
	dicomclinicalprotocolname="TCGA Lung squamous cell carcinoma"
	anatomycodevalue="39607008"
	anatomycodemeaning="Lung"
elif [ "${tcgaproject}" = "TCGA-DLBC" ]
then
	dicomclinicalprotocolname="TCGA Lymphoid Neoplasm Diffuse Large B-cell Lymphoma"
	anatomycodevalue="6969002"
	anatomycodemeaning="Lymphoid tissue"
elif [ "${tcgaproject}" = "TCGA-MESO" ]
then
	dicomclinicalprotocolname="TCGA Mesothelioma"
	# do not assume pleura
	# not in SNOMED-DICOM subset - need CP to add it :(
	anatomycodevalue="71400007"
	anatomycodemeaning="Mesothelium"
elif [ "${tcgaproject}" = "TCGA-MISC" ]
then
	dicomclinicalprotocolname="TCGA Miscellaneous"
elif [ "${tcgaproject}" = "TCGA-OV" ]
then
	dicomclinicalprotocolname="TCGA Ovarian serous cystadenocarcinoma"
	anatomycodevalue="15497006"
	anatomycodemeaning="Ovary"
elif [ "${tcgaproject}" = "TCGA-PAAD" ]
then
	dicomclinicalprotocolname="TCGA Pancreatic adenocarcinoma"
	anatomycodevalue="15776009"
	anatomycodemeaning="Pancreas"
elif [ "${tcgaproject}" = "TCGA-PCPG" ]
then
	dicomclinicalprotocolname="TCGA Pheochromocytoma and Paraganglioma"
elif [ "${tcgaproject}" = "TCGA-PRAD" ]
then
	dicomclinicalprotocolname="TCGA Prostate adenocarcinoma"
	anatomycodevalue="41216001"
	anatomycodemeaning="Prostate"
elif [ "${tcgaproject}" = "TCGA-READ" ]
then
	dicomclinicalprotocolname="TCGA Rectum adenocarcinoma"
	anatomycodevalue="34402009"
	anatomycodemeaning="Rectum"
elif [ "${tcgaproject}" = "TCGA-SARC" ]
then
	dicomclinicalprotocolname="TCGA Sarcoma"
elif [ "${tcgaproject}" = "TCGA-SKCM" ]
then
	dicomclinicalprotocolname="TCGA Skin Cutaneous Melanoma"
	anatomycodevalue="39937001"
	anatomycodemeaning="Skin"
elif [ "${tcgaproject}" = "TCGA-STAD" ]
then
	dicomclinicalprotocolname="TCGA Stomach adenocarcinoma"
	anatomycodevalue="69695003"
	anatomycodemeaning="Stomach"
elif [ "${tcgaproject}" = "TCGA-TGCT" ]
then
	dicomclinicalprotocolname="TCGA Testicular Germ Cell Tumors"
	anatomycodevalue="40689003"
	anatomycodemeaning="Testis"
elif [ "${tcgaproject}" = "TCGA-THYM" ]
then
	dicomclinicalprotocolname="TCGA Thymoma"
	anatomycodevalue="9875009"
	anatomycodemeaning="Thymus"
elif [ "${tcgaproject}" = "TCGA-THCA" ]
then
	dicomclinicalprotocolname="TCGA Thyroid carcinoma"
	anatomycodevalue="69748006"
	anatomycodemeaning="Thyroid"
elif [ "${tcgaproject}" = "TCGA-UCS" ]
then
	dicomclinicalprotocolname="TCGA Uterine Carcinosarcoma"
	anatomycodevalue="35039007"
	anatomycodemeaning="Uterus"
elif [ "${tcgaproject}" = "TCGA-UCEC" ]
then
	dicomclinicalprotocolname="TCGA Uterine Corpus Endometrial Carcinoma"
	anatomycodevalue="35039007"
	anatomycodemeaning="Uterus"
elif [ "${tcgaproject}" = "TCGA-UVM" ]
then
	dicomclinicalprotocolname="TCGA Uveal Melanoma"
	# not in SNOMED-DICOM subset - need CP to add it :(
	anatomycodevalue="74862005"
	anatomycodemeaning="Uvea"
else
	dicomclinicalprotocolname="${tcgaproject}"
fi

dicomclinicaltrialsiteid="TCGA-${tcgatissuesourcesite}"
# could populate site name from https://gdc.cancer.gov/resources-tcga-users/tcga-code-tables/tissue-source-site-codes :(
# should make this a table lookupo from a separate text file :
if [ "${tcgatissuesourcesite}" = "01" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "02" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "04" ]
then
	dicomclinicaltrialsitename="Gynecologic Oncology Group"
elif [ "${tcgatissuesourcesite}" = "05" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "06" ]
then
	dicomclinicaltrialsitename="Henry Ford Hospital"
elif [ "${tcgatissuesourcesite}" = "07" ]
then
	dicomclinicaltrialsitename="TGen"
elif [ "${tcgatissuesourcesite}" = "08" ]
then
	dicomclinicaltrialsitename="UCSF"
elif [ "${tcgatissuesourcesite}" = "09" ]
then
	dicomclinicaltrialsitename="UCSF"
elif [ "${tcgatissuesourcesite}" = "10" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "11" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "12" ]
then
	dicomclinicaltrialsitename="Duke"
elif [ "${tcgatissuesourcesite}" = "13" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "14" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "15" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "16" ]
then
	dicomclinicaltrialsitename="Toronto Western Hospital"
elif [ "${tcgatissuesourcesite}" = "17" ]
then
	dicomclinicaltrialsitename="Washington University"
elif [ "${tcgatissuesourcesite}" = "18" ]
then
	dicomclinicaltrialsitename="Princess Margaret Hospital (Canada)"
elif [ "${tcgatissuesourcesite}" = "19" ]
then
	dicomclinicaltrialsitename="Case Western"
elif [ "${tcgatissuesourcesite}" = "1Z" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "20" ]
then
	dicomclinicaltrialsitename="Fox Chase Cancer Center"
elif [ "${tcgatissuesourcesite}" = "21" ]
then
	dicomclinicaltrialsitename="Fox Chase Cancer Center"
elif [ "${tcgatissuesourcesite}" = "22" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "23" ]
then
	dicomclinicaltrialsitename="Cedars Sinai"
elif [ "${tcgatissuesourcesite}" = "24" ]
then
	dicomclinicaltrialsitename="Washington University"
elif [ "${tcgatissuesourcesite}" = "25" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "26" ]
then
	dicomclinicaltrialsitename="University of Florida"
elif [ "${tcgatissuesourcesite}" = "27" ]
then
	dicomclinicaltrialsitename="Milan - Italy, Fondazione IRCCS Instituto Neuroligico C. Besta"
elif [ "${tcgatissuesourcesite}" = "28" ]
then
	dicomclinicaltrialsitename="Cedars Sinai"
elif [ "${tcgatissuesourcesite}" = "29" ]
then
	dicomclinicaltrialsitename="Duke"
elif [ "${tcgatissuesourcesite}" = "2A" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering Cancer Center"
elif [ "${tcgatissuesourcesite}" = "2E" ]
then
	dicomclinicaltrialsitename="University of Kansas Medical Center"
elif [ "${tcgatissuesourcesite}" = "2F" ]
then
	dicomclinicaltrialsitename="Erasmus MC"
elif [ "${tcgatissuesourcesite}" = "2G" ]
then
	dicomclinicaltrialsitename="Erasmus MC"
elif [ "${tcgatissuesourcesite}" = "2H" ]
then
	dicomclinicaltrialsitename="Erasmus MC"
elif [ "${tcgatissuesourcesite}" = "2J" ]
then
	dicomclinicaltrialsitename="Mayo Clinic"
elif [ "${tcgatissuesourcesite}" = "2K" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "2L" ]
then
	dicomclinicaltrialsitename="Technical University of Munich"
elif [ "${tcgatissuesourcesite}" = "2M" ]
then
	dicomclinicaltrialsitename="Technical University of Munich"
elif [ "${tcgatissuesourcesite}" = "2N" ]
then
	dicomclinicaltrialsitename="Technical University of Munich"
elif [ "${tcgatissuesourcesite}" = "2P" ]
then
	dicomclinicaltrialsitename="University of California San Diego"
elif [ "${tcgatissuesourcesite}" = "2V" ]
then
	dicomclinicaltrialsitename="University of California San Diego"
elif [ "${tcgatissuesourcesite}" = "2W" ]
then
	dicomclinicaltrialsitename="University of New Mexico"
elif [ "${tcgatissuesourcesite}" = "2X" ]
then
	dicomclinicaltrialsitename="ABS IUPUI"
elif [ "${tcgatissuesourcesite}" = "2Y" ]
then
	dicomclinicaltrialsitename="Moffitt Cancer Center"
elif [ "${tcgatissuesourcesite}" = "2Z" ]
then
	dicomclinicaltrialsitename="Moffitt Cancer Center"
elif [ "${tcgatissuesourcesite}" = "30" ]
then
	dicomclinicaltrialsitename="Harvard"
elif [ "${tcgatissuesourcesite}" = "31" ]
then
	dicomclinicaltrialsitename="Imperial College"
elif [ "${tcgatissuesourcesite}" = "32" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital (AZ)"
elif [ "${tcgatissuesourcesite}" = "33" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "34" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "35" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "36" ]
then
	dicomclinicaltrialsitename="BC Cancer Agency"
elif [ "${tcgatissuesourcesite}" = "37" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "38" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "39" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "3A" ]
then
	dicomclinicaltrialsitename="Moffitt Cancer Center"
elif [ "${tcgatissuesourcesite}" = "3B" ]
then
	dicomclinicaltrialsitename="Moffitt Cancer Center"
elif [ "${tcgatissuesourcesite}" = "3C" ]
then
	dicomclinicaltrialsitename="Columbia University"
elif [ "${tcgatissuesourcesite}" = "3E" ]
then
	dicomclinicaltrialsitename="Columbia University"
elif [ "${tcgatissuesourcesite}" = "3G" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "3H" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "3J" ]
then
	dicomclinicaltrialsitename="Carle Cancer Center"
elif [ "${tcgatissuesourcesite}" = "3K" ]
then
	dicomclinicaltrialsitename="Boston Medical Center"
elif [ "${tcgatissuesourcesite}" = "3L" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "3M" ]
then
	dicomclinicaltrialsitename="University of Kansas Medical Center"
elif [ "${tcgatissuesourcesite}" = "3N" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "3P" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "3Q" ]
then
	dicomclinicaltrialsitename="Greenville Health Systems"
elif [ "${tcgatissuesourcesite}" = "3R" ]
then
	dicomclinicaltrialsitename="University of New Mexico"
elif [ "${tcgatissuesourcesite}" = "3S" ]
then
	dicomclinicaltrialsitename="University of New Mexico"
elif [ "${tcgatissuesourcesite}" = "3T" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "3U" ]
then
	dicomclinicaltrialsitename="University of Chicago"
elif [ "${tcgatissuesourcesite}" = "3W" ]
then
	dicomclinicaltrialsitename="University of California San Diego"
elif [ "${tcgatissuesourcesite}" = "3X" ]
then
	dicomclinicaltrialsitename="Alberta Health Services"
elif [ "${tcgatissuesourcesite}" = "3Z" ]
then
	dicomclinicaltrialsitename="Mary Bird Perkins Cancer Center - Our Lady of the Lake"
elif [ "${tcgatissuesourcesite}" = "41" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "42" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "43" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "44" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "46" ]
then
	dicomclinicaltrialsitename="St. Joseph's Medical Center (MD)"
elif [ "${tcgatissuesourcesite}" = "49" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "4A" ]
then
	dicomclinicaltrialsitename="Mary Bird Perkins Cancer Center - Our Lady of the Lake"
elif [ "${tcgatissuesourcesite}" = "4B" ]
then
	dicomclinicaltrialsitename="Mary Bird Perkins Cancer Center - Our Lady of the Lake"
elif [ "${tcgatissuesourcesite}" = "4C" ]
then
	dicomclinicaltrialsitename="Mary Bird Perkins Cancer Center - Our Lady of the Lake"
elif [ "${tcgatissuesourcesite}" = "4D" ]
then
	dicomclinicaltrialsitename="Molecular Response"
elif [ "${tcgatissuesourcesite}" = "4E" ]
then
	dicomclinicaltrialsitename="Molecular Response"
elif [ "${tcgatissuesourcesite}" = "4G" ]
then
	dicomclinicaltrialsitename="Sapienza University of Rome"
elif [ "${tcgatissuesourcesite}" = "4H" ]
then
	dicomclinicaltrialsitename="Proteogenex, Inc."
elif [ "${tcgatissuesourcesite}" = "4J" ]
then
	dicomclinicaltrialsitename="Proteogenex, Inc."
elif [ "${tcgatissuesourcesite}" = "4K" ]
then
	dicomclinicaltrialsitename="Proteogenex, Inc."
elif [ "${tcgatissuesourcesite}" = "4L" ]
then
	dicomclinicaltrialsitename="Proteogenex, Inc."
elif [ "${tcgatissuesourcesite}" = "4N" ]
then
	dicomclinicaltrialsitename="Mary Bird Perkins Cancer Center - Our Lady of the Lake"
elif [ "${tcgatissuesourcesite}" = "4P" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "4Q" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "4R" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "4S" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "4T" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "4V" ]
then
	dicomclinicaltrialsitename="Hospital Louis Pradel"
elif [ "${tcgatissuesourcesite}" = "4W" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "4X" ]
then
	dicomclinicaltrialsitename="Yale University"
elif [ "${tcgatissuesourcesite}" = "4Y" ]
then
	dicomclinicaltrialsitename="Medical College of Wisconsin"
elif [ "${tcgatissuesourcesite}" = "4Z" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "50" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "51" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "52" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "53" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "55" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "56" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "57" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "58" ]
then
	dicomclinicaltrialsitename="Thoraxklinik at University Hospital Heidelberg"
elif [ "${tcgatissuesourcesite}" = "59" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "5A" ]
then
	dicomclinicaltrialsitename="Wake Forest University"
elif [ "${tcgatissuesourcesite}" = "5B" ]
then
	dicomclinicaltrialsitename="Medical College of Wisconsin"
elif [ "${tcgatissuesourcesite}" = "5C" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "5D" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "5F" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "5G" ]
then
	dicomclinicaltrialsitename="Cleveland Clinic Foundation"
elif [ "${tcgatissuesourcesite}" = "5H" ]
then
	dicomclinicaltrialsitename="Retina Consultants Houston"
elif [ "${tcgatissuesourcesite}" = "5J" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "5K" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "5L" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "5M" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "5N" ]
then
	dicomclinicaltrialsitename="University Hospital Erlangen"
elif [ "${tcgatissuesourcesite}" = "5P" ]
then
	dicomclinicaltrialsitename="University Hospital Erlangen"
elif [ "${tcgatissuesourcesite}" = "5Q" ]
then
	dicomclinicaltrialsitename="Proteogenex, Inc"
elif [ "${tcgatissuesourcesite}" = "5R" ]
then
	dicomclinicaltrialsitename="Proteogenex, Inc"
elif [ "${tcgatissuesourcesite}" = "5S" ]
then
	dicomclinicaltrialsitename="Holy Cross"
elif [ "${tcgatissuesourcesite}" = "5T" ]
then
	dicomclinicaltrialsitename="Holy Cross"
elif [ "${tcgatissuesourcesite}" = "5U" ]
then
	dicomclinicaltrialsitename="Regina Elena National Cancer Institute"
elif [ "${tcgatissuesourcesite}" = "5V" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "5W" ]
then
	dicomclinicaltrialsitename="University of Alabama"
elif [ "${tcgatissuesourcesite}" = "5X" ]
then
	dicomclinicaltrialsitename="University of Alabama"
elif [ "${tcgatissuesourcesite}" = "60" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "61" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "62" ]
then
	dicomclinicaltrialsitename="Thoraxklinik at University Hospital Heidelberg"
elif [ "${tcgatissuesourcesite}" = "63" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research"
elif [ "${tcgatissuesourcesite}" = "64" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "65" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "66" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "67" ]
then
	dicomclinicaltrialsitename="St Joseph's Medical Center (MD)"
elif [ "${tcgatissuesourcesite}" = "68" ]
then
	dicomclinicaltrialsitename="Washington University - Cleveland Clinic"
elif [ "${tcgatissuesourcesite}" = "69" ]
then
	dicomclinicaltrialsitename="Washington University - Cleveland Clinic"
elif [ "${tcgatissuesourcesite}" = "6A" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "6D" ]
then
	dicomclinicaltrialsitename="University of Oklahoma HSC"
elif [ "${tcgatissuesourcesite}" = "6G" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "6H" ]
then
	dicomclinicaltrialsitename="Test For lcml"
elif [ "${tcgatissuesourcesite}" = "70" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "71" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "72" ]
then
	dicomclinicaltrialsitename="NCH"
elif [ "${tcgatissuesourcesite}" = "73" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "74" ]
then
	dicomclinicaltrialsitename="Swedish Neurosciences"
elif [ "${tcgatissuesourcesite}" = "75" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "76" ]
then
	dicomclinicaltrialsitename="Thomas Jefferson University"
elif [ "${tcgatissuesourcesite}" = "77" ]
then
	dicomclinicaltrialsitename="Prince Charles Hospital"
elif [ "${tcgatissuesourcesite}" = "78" ]
then
	dicomclinicaltrialsitename="Prince Charles Hospital"
elif [ "${tcgatissuesourcesite}" = "79" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)/Ottawa"
elif [ "${tcgatissuesourcesite}" = "80" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)/Ottawa"
elif [ "${tcgatissuesourcesite}" = "81" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "82" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "83" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "85" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "86" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "87" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "90" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "91" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "92" ]
then
	dicomclinicaltrialsitename="Washington University - St. Louis"
elif [ "${tcgatissuesourcesite}" = "93" ]
then
	dicomclinicaltrialsitename="Washington University - St. Louis"
elif [ "${tcgatissuesourcesite}" = "94" ]
then
	dicomclinicaltrialsitename="Washington University - Emory"
elif [ "${tcgatissuesourcesite}" = "95" ]
then
	dicomclinicaltrialsitename="Washington University - Emory"
elif [ "${tcgatissuesourcesite}" = "96" ]
then
	dicomclinicaltrialsitename="Washington University - NYU"
elif [ "${tcgatissuesourcesite}" = "97" ]
then
	dicomclinicaltrialsitename="Washington University - NYU"
elif [ "${tcgatissuesourcesite}" = "98" ]
then
	dicomclinicaltrialsitename="Washington University - Alabama"
elif [ "${tcgatissuesourcesite}" = "99" ]
then
	dicomclinicaltrialsitename="Washington University - Alabama"
elif [ "${tcgatissuesourcesite}" = "A1" ]
then
	dicomclinicaltrialsitename="UCSF"
elif [ "${tcgatissuesourcesite}" = "A2" ]
then
	dicomclinicaltrialsitename="Walter Reed"
elif [ "${tcgatissuesourcesite}" = "A3" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "A4" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "A5" ]
then
	dicomclinicaltrialsitename="Cedars Sinai"
elif [ "${tcgatissuesourcesite}" = "A6" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "A7" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "A8" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "AA" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "AB" ]
then
	dicomclinicaltrialsitename="Washington University"
elif [ "${tcgatissuesourcesite}" = "AC" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "AD" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "AF" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "AG" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "AH" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "AJ" ]
then
	dicomclinicaltrialsitename="International Genomics Conosrtium"
elif [ "${tcgatissuesourcesite}" = "AK" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "AL" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "AM" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "AN" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "AO" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "AP" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "AQ" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "AR" ]
then
	dicomclinicaltrialsitename="Mayo"
elif [ "${tcgatissuesourcesite}" = "AS" ]
then
	dicomclinicaltrialsitename="St. Joseph's Medical Center-(MD)"
elif [ "${tcgatissuesourcesite}" = "AT" ]
then
	dicomclinicaltrialsitename="St. Joseph's Medical Center-(MD)"
elif [ "${tcgatissuesourcesite}" = "AU" ]
then
	dicomclinicaltrialsitename="St. Joseph's Medical Center-(MD)"
elif [ "${tcgatissuesourcesite}" = "AV" ]
then
	dicomclinicaltrialsitename="NCH"
elif [ "${tcgatissuesourcesite}" = "AW" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "AX" ]
then
	dicomclinicaltrialsitename="Gynecologic Oncology Group"
elif [ "${tcgatissuesourcesite}" = "AY" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "AZ" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "B0" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "B1" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "B2" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "B3" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "B4" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "B5" ]
then
	dicomclinicaltrialsitename="Duke"
elif [ "${tcgatissuesourcesite}" = "B6" ]
then
	dicomclinicaltrialsitename="Duke"
elif [ "${tcgatissuesourcesite}" = "B7" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "B8" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "B9" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "BA" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "BB" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "BC" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "BD" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "BF" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "BG" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "BH" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "BI" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "BJ" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "BK" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "BL" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "BM" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "BP" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "BQ" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "BR" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "BS" ]
then
	dicomclinicaltrialsitename="University of Hawaii"
elif [ "${tcgatissuesourcesite}" = "BT" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "BW" ]
then
	dicomclinicaltrialsitename="St. Joseph's Medical Center-(MD)"
elif [ "${tcgatissuesourcesite}" = "C4" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "C5" ]
then
	dicomclinicaltrialsitename="Medical College of Wisconsin"
elif [ "${tcgatissuesourcesite}" = "C8" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "C9" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "CA" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "CB" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "CC" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "CD" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "CE" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "CF" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "CG" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "CH" ]
then
	dicomclinicaltrialsitename="Indivumed"
elif [ "${tcgatissuesourcesite}" = "CI" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "CJ" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "CK" ]
then
	dicomclinicaltrialsitename="Harvard"
elif [ "${tcgatissuesourcesite}" = "CL" ]
then
	dicomclinicaltrialsitename="Harvard"
elif [ "${tcgatissuesourcesite}" = "CM" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "CN" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "CQ" ]
then
	dicomclinicaltrialsitename="University Health Network, Toronto"
elif [ "${tcgatissuesourcesite}" = "CR" ]
then
	dicomclinicaltrialsitename="Vanderbilt University"
elif [ "${tcgatissuesourcesite}" = "CS" ]
then
	dicomclinicaltrialsitename="Thomas Jefferson University"
elif [ "${tcgatissuesourcesite}" = "CU" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "CV" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "CW" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "CX" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "CZ" ]
then
	dicomclinicaltrialsitename="Harvard"
elif [ "${tcgatissuesourcesite}" = "D1" ]
then
	dicomclinicaltrialsitename="Mayo Clinic"
elif [ "${tcgatissuesourcesite}" = "D3" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "D5" ]
then
	dicomclinicaltrialsitename="Greater Poland Cancer Center"
elif [ "${tcgatissuesourcesite}" = "D6" ]
then
	dicomclinicaltrialsitename="Greater Poland Cancer Center"
elif [ "${tcgatissuesourcesite}" = "D7" ]
then
	dicomclinicaltrialsitename="Greater Poland Cancer Center"
elif [ "${tcgatissuesourcesite}" = "D8" ]
then
	dicomclinicaltrialsitename="Greater Poland Cancer Center"
elif [ "${tcgatissuesourcesite}" = "D9" ]
then
	dicomclinicaltrialsitename="Greater Poland Cancer Center"
elif [ "${tcgatissuesourcesite}" = "DA" ]
then
	dicomclinicaltrialsitename="Yale"
elif [ "${tcgatissuesourcesite}" = "DB" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "DC" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "DD" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "DE" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "DF" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research"
elif [ "${tcgatissuesourcesite}" = "DG" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research"
elif [ "${tcgatissuesourcesite}" = "DH" ]
then
	dicomclinicaltrialsitename="University of Florida"
elif [ "${tcgatissuesourcesite}" = "DI" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "DJ" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "DK" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "DM" ]
then
	dicomclinicaltrialsitename="University Of Michigan"
elif [ "${tcgatissuesourcesite}" = "DO" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "DQ" ]
then
	dicomclinicaltrialsitename="University Of Michigan"
elif [ "${tcgatissuesourcesite}" = "DR" ]
then
	dicomclinicaltrialsitename="University of Hawaii"
elif [ "${tcgatissuesourcesite}" = "DS" ]
then
	dicomclinicaltrialsitename="Cedars Sinai"
elif [ "${tcgatissuesourcesite}" = "DT" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "DU" ]
then
	dicomclinicaltrialsitename="Henry Ford Hospital"
elif [ "${tcgatissuesourcesite}" = "DV" ]
then
	dicomclinicaltrialsitename="NCI Urologic Oncology Branch"
elif [ "${tcgatissuesourcesite}" = "DW" ]
then
	dicomclinicaltrialsitename="NCI Urologic Oncology Branch"
elif [ "${tcgatissuesourcesite}" = "DX" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "DY" ]
then
	dicomclinicaltrialsitename="University Of Michigan"
elif [ "${tcgatissuesourcesite}" = "DZ" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "E1" ]
then
	dicomclinicaltrialsitename="Duke"
elif [ "${tcgatissuesourcesite}" = "E2" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "E3" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "E5" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "E6" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "E7" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "E8" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "E9" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "EA" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "EB" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "EC" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "ED" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "EE" ]
then
	dicomclinicaltrialsitename="University of Sydney"
elif [ "${tcgatissuesourcesite}" = "EF" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "EI" ]
then
	dicomclinicaltrialsitename="Greater Poland Cancer Center"
elif [ "${tcgatissuesourcesite}" = "EJ" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "EK" ]
then
	dicomclinicaltrialsitename="Gynecologic Oncology Group"
elif [ "${tcgatissuesourcesite}" = "EL" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "EM" ]
then
	dicomclinicaltrialsitename="University Health Network"
elif [ "${tcgatissuesourcesite}" = "EO" ]
then
	dicomclinicaltrialsitename="University Health Network"
elif [ "${tcgatissuesourcesite}" = "EP" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "EQ" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "ER" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "ES" ]
then
	dicomclinicaltrialsitename="University of Florida"
elif [ "${tcgatissuesourcesite}" = "ET" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "EU" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "EV" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "EW" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "EX" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "EY" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "EZ" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "F1" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "F2" ]
then
	dicomclinicaltrialsitename="UNC"
elif [ "${tcgatissuesourcesite}" = "F4" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "F5" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "F6" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "F7" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "F9" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "FA" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "FB" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "FC" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "FD" ]
then
	dicomclinicaltrialsitename="BLN - University Of Chicago"
elif [ "${tcgatissuesourcesite}" = "FE" ]
then
	dicomclinicaltrialsitename="Ohio State University"
elif [ "${tcgatissuesourcesite}" = "FF" ]
then
	dicomclinicaltrialsitename="SingHealth"
elif [ "${tcgatissuesourcesite}" = "FG" ]
then
	dicomclinicaltrialsitename="Case Western"
elif [ "${tcgatissuesourcesite}" = "FH" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "FI" ]
then
	dicomclinicaltrialsitename="Washington University"
elif [ "${tcgatissuesourcesite}" = "FJ" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "FK" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "FL" ]
then
	dicomclinicaltrialsitename="University of Hawaii - Normal Study"
elif [ "${tcgatissuesourcesite}" = "FM" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FN" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FP" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FQ" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "FR" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "FS" ]
then
	dicomclinicaltrialsitename="Essen"
elif [ "${tcgatissuesourcesite}" = "FT" ]
then
	dicomclinicaltrialsitename="BLN - University of Miami"
elif [ "${tcgatissuesourcesite}" = "FU" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FV" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FW" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FX" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FY" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "FZ" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "G2" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "G3" ]
then
	dicomclinicaltrialsitename="Alberta Health Services"
elif [ "${tcgatissuesourcesite}" = "G4" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "G5" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "G6" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "G7" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "G8" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "G9" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "GC" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "GD" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GE" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GF" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GG" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GH" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GI" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GJ" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GK" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GL" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "GM" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "GN" ]
then
	dicomclinicaltrialsitename="Roswell"
elif [ "${tcgatissuesourcesite}" = "GP" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "GR" ]
then
	dicomclinicaltrialsitename="University of Nebraska Medical Center (UNMC)"
elif [ "${tcgatissuesourcesite}" = "GS" ]
then
	dicomclinicaltrialsitename="Fundacio Clinic per a la Recerca Biomedica"
elif [ "${tcgatissuesourcesite}" = "GU" ]
then
	dicomclinicaltrialsitename="BLN - UT Southwestern Medical Center at Dallas"
elif [ "${tcgatissuesourcesite}" = "GV" ]
then
	dicomclinicaltrialsitename="BLN - Cleveland Clinic"
elif [ "${tcgatissuesourcesite}" = "GZ" ]
then
	dicomclinicaltrialsitename="BC Cancer Agency"
elif [ "${tcgatissuesourcesite}" = "H1" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "H2" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "H3" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "H4" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "H5" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "H6" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "H7" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "H8" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "H9" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "HA" ]
then
	dicomclinicaltrialsitename="Alberta Health Services"
elif [ "${tcgatissuesourcesite}" = "HB" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "HC" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "HD" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "HE" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "HF" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "HG" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "HH" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "HI" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "HJ" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "HK" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "HL" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "HM" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "HN" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "HP" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "HQ" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "HR" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "HS" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "HT" ]
then
	dicomclinicaltrialsitename="Case Western - St Joes"
elif [ "${tcgatissuesourcesite}" = "HU" ]
then
	dicomclinicaltrialsitename="National Cancer Center Korea"
elif [ "${tcgatissuesourcesite}" = "HV" ]
then
	dicomclinicaltrialsitename="National Cancer Center Korea"
elif [ "${tcgatissuesourcesite}" = "HW" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "HZ" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "IA" ]
then
	dicomclinicaltrialsitename="Cleveland Clinic"
elif [ "${tcgatissuesourcesite}" = "IB" ]
then
	dicomclinicaltrialsitename="Alberta Health Services"
elif [ "${tcgatissuesourcesite}" = "IC" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "IE" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "IF" ]
then
	dicomclinicaltrialsitename="University of Texas MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "IG" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "IH" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "IJ" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "IK" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "IM" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "IN" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "IP" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "IQ" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "IR" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "IS" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "IW" ]
then
	dicomclinicaltrialsitename="Cedars Sinai"
elif [ "${tcgatissuesourcesite}" = "IZ" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "J1" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "J2" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "J4" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "J7" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "J8" ]
then
	dicomclinicaltrialsitename="Mayo Clinic"
elif [ "${tcgatissuesourcesite}" = "J9" ]
then
	dicomclinicaltrialsitename="Melbourne Health"
elif [ "${tcgatissuesourcesite}" = "JA" ]
then
	dicomclinicaltrialsitename="ABS - Research Metrics Pakistan"
elif [ "${tcgatissuesourcesite}" = "JL" ]
then
	dicomclinicaltrialsitename="ABS - Research Metrics Pakistan"
elif [ "${tcgatissuesourcesite}" = "JU" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "JV" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "JW" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "JX" ]
then
	dicomclinicaltrialsitename="Washington University"
elif [ "${tcgatissuesourcesite}" = "JY" ]
then
	dicomclinicaltrialsitename="University Health Network"
elif [ "${tcgatissuesourcesite}" = "JZ" ]
then
	dicomclinicaltrialsitename="University of Rochester"
elif [ "${tcgatissuesourcesite}" = "K1" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "K4" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "K6" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "K7" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "K8" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "KA" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "KB" ]
then
	dicomclinicaltrialsitename="University Health Network, Toronto"
elif [ "${tcgatissuesourcesite}" = "KC" ]
then
	dicomclinicaltrialsitename="Cornell Medical College"
elif [ "${tcgatissuesourcesite}" = "KD" ]
then
	dicomclinicaltrialsitename="Mount Sinai School of Medicine"
elif [ "${tcgatissuesourcesite}" = "KE" ]
then
	dicomclinicaltrialsitename="Mount Sinai School of Medicine"
elif [ "${tcgatissuesourcesite}" = "KF" ]
then
	dicomclinicaltrialsitename="Christiana Healthcare"
elif [ "${tcgatissuesourcesite}" = "KG" ]
then
	dicomclinicaltrialsitename="Baylor Network"
elif [ "${tcgatissuesourcesite}" = "KH" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "KJ" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "KK" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "KL" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "KM" ]
then
	dicomclinicaltrialsitename="NCI Urologic Oncology Branch"
elif [ "${tcgatissuesourcesite}" = "KN" ]
then
	dicomclinicaltrialsitename="Harvard"
elif [ "${tcgatissuesourcesite}" = "KO" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "KP" ]
then
	dicomclinicaltrialsitename="British Columbia Cancer Agency"
elif [ "${tcgatissuesourcesite}" = "KQ" ]
then
	dicomclinicaltrialsitename="Cornell Medical College"
elif [ "${tcgatissuesourcesite}" = "KR" ]
then
	dicomclinicaltrialsitename="University Of Michigan"
elif [ "${tcgatissuesourcesite}" = "KS" ]
then
	dicomclinicaltrialsitename="University Of Michigan"
elif [ "${tcgatissuesourcesite}" = "KT" ]
then
	dicomclinicaltrialsitename="Hartford"
elif [ "${tcgatissuesourcesite}" = "KU" ]
then
	dicomclinicaltrialsitename="Hartford"
elif [ "${tcgatissuesourcesite}" = "KV" ]
then
	dicomclinicaltrialsitename="Hartford"
elif [ "${tcgatissuesourcesite}" = "KZ" ]
then
	dicomclinicaltrialsitename="Hartford"
elif [ "${tcgatissuesourcesite}" = "L1" ]
then
	dicomclinicaltrialsitename="Hartford"
elif [ "${tcgatissuesourcesite}" = "L3" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "L4" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "L5" ]
then
	dicomclinicaltrialsitename="University of Michigan"
elif [ "${tcgatissuesourcesite}" = "L6" ]
then
	dicomclinicaltrialsitename="National Institutes of Health"
elif [ "${tcgatissuesourcesite}" = "L7" ]
then
	dicomclinicaltrialsitename="Christiana Care"
elif [ "${tcgatissuesourcesite}" = "L8" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "L9" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "LA" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "LB" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "LC" ]
then
	dicomclinicaltrialsitename="Hartford Hospital"
elif [ "${tcgatissuesourcesite}" = "LD" ]
then
	dicomclinicaltrialsitename="Hartford Hospital"
elif [ "${tcgatissuesourcesite}" = "LG" ]
then
	dicomclinicaltrialsitename="Hartford Hospital"
elif [ "${tcgatissuesourcesite}" = "LH" ]
then
	dicomclinicaltrialsitename="Hartford Hospital"
elif [ "${tcgatissuesourcesite}" = "LI" ]
then
	dicomclinicaltrialsitename="Hartford Hospital"
elif [ "${tcgatissuesourcesite}" = "LK" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "LL" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "LN" ]
then
	dicomclinicaltrialsitename="ILSBIO"
elif [ "${tcgatissuesourcesite}" = "LP" ]
then
	dicomclinicaltrialsitename="ILSBIO"
elif [ "${tcgatissuesourcesite}" = "LQ" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "LS" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "LT" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "M7" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "M8" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "M9" ]
then
	dicomclinicaltrialsitename="Ontario Institute for Cancer Research (OICR)"
elif [ "${tcgatissuesourcesite}" = "MA" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "MB" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "ME" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "MF" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "MG" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "MH" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "MI" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "MJ" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "MK" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "ML" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "MM" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "MN" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "MO" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "MP" ]
then
	dicomclinicaltrialsitename="Washington University - Mayo Clinic"
elif [ "${tcgatissuesourcesite}" = "MQ" ]
then
	dicomclinicaltrialsitename="Washington University - NYU"
elif [ "${tcgatissuesourcesite}" = "MR" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "MS" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "MT" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "MU" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "MV" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "MW" ]
then
	dicomclinicaltrialsitename="University of Miami"
elif [ "${tcgatissuesourcesite}" = "MX" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "MY" ]
then
	dicomclinicaltrialsitename="Montefiore Medical Center"
elif [ "${tcgatissuesourcesite}" = "MZ" ]
then
	dicomclinicaltrialsitename="Montefiore Medical Center"
elif [ "${tcgatissuesourcesite}" = "N1" ]
then
	dicomclinicaltrialsitename="Montefiore Medical Center"
elif [ "${tcgatissuesourcesite}" = "N5" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "N6" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "N7" ]
then
	dicomclinicaltrialsitename="Washington University"
elif [ "${tcgatissuesourcesite}" = "N8" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "N9" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "NA" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "NB" ]
then
	dicomclinicaltrialsitename="Washington University - CHUV"
elif [ "${tcgatissuesourcesite}" = "NC" ]
then
	dicomclinicaltrialsitename="Washington University - CHUV"
elif [ "${tcgatissuesourcesite}" = "ND" ]
then
	dicomclinicaltrialsitename="Cedars Sinai"
elif [ "${tcgatissuesourcesite}" = "NF" ]
then
	dicomclinicaltrialsitename="Mayo Clinic - Rochester"
elif [ "${tcgatissuesourcesite}" = "NG" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "NH" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "NI" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "NJ" ]
then
	dicomclinicaltrialsitename="Washington University - Rush University"
elif [ "${tcgatissuesourcesite}" = "NK" ]
then
	dicomclinicaltrialsitename="Washington University - Rush University"
elif [ "${tcgatissuesourcesite}" = "NM" ]
then
	dicomclinicaltrialsitename="Cambridge BioSource"
elif [ "${tcgatissuesourcesite}" = "NP" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "NQ" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "NS" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "O1" ]
then
	dicomclinicaltrialsitename="Washington University - CALGB"
elif [ "${tcgatissuesourcesite}" = "O2" ]
then
	dicomclinicaltrialsitename="Washington University - CALGB"
elif [ "${tcgatissuesourcesite}" = "O8" ]
then
	dicomclinicaltrialsitename="Saint Mary's Health Care"
elif [ "${tcgatissuesourcesite}" = "O9" ]
then
	dicomclinicaltrialsitename="Saint Mary's Health Care"
elif [ "${tcgatissuesourcesite}" = "OC" ]
then
	dicomclinicaltrialsitename="Saint Mary's Health Care"
elif [ "${tcgatissuesourcesite}" = "OD" ]
then
	dicomclinicaltrialsitename="Saint Mary's Health Care"
elif [ "${tcgatissuesourcesite}" = "OE" ]
then
	dicomclinicaltrialsitename="Saint Mary's Health Care"
elif [ "${tcgatissuesourcesite}" = "OJ" ]
then
	dicomclinicaltrialsitename="Saint Mary's Health Care"
elif [ "${tcgatissuesourcesite}" = "OK" ]
then
	dicomclinicaltrialsitename="Mount Sinai School of Medicine"
elif [ "${tcgatissuesourcesite}" = "OL" ]
then
	dicomclinicaltrialsitename="University of Chicago"
elif [ "${tcgatissuesourcesite}" = "OR" ]
then
	dicomclinicaltrialsitename="University of Michigan"
elif [ "${tcgatissuesourcesite}" = "OU" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "OW" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "OX" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "OY" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "P3" ]
then
	dicomclinicaltrialsitename="Fred Hutchinson"
elif [ "${tcgatissuesourcesite}" = "P4" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "P5" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "P6" ]
then
	dicomclinicaltrialsitename="Translational Genomics Research Institute"
elif [ "${tcgatissuesourcesite}" = "P7" ]
then
	dicomclinicaltrialsitename="Translational Genomics Research Institute"
elif [ "${tcgatissuesourcesite}" = "P8" ]
then
	dicomclinicaltrialsitename="University of Pittsburgh"
elif [ "${tcgatissuesourcesite}" = "P9" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "PA" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "PB" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "PC" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "PD" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "PE" ]
then
	dicomclinicaltrialsitename="Fox Chase"
elif [ "${tcgatissuesourcesite}" = "PG" ]
then
	dicomclinicaltrialsitename="Montefiore Medical Center"
elif [ "${tcgatissuesourcesite}" = "PH" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran"
elif [ "${tcgatissuesourcesite}" = "PJ" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran"
elif [ "${tcgatissuesourcesite}" = "PK" ]
then
	dicomclinicaltrialsitename="University Health Network"
elif [ "${tcgatissuesourcesite}" = "PL" ]
then
	dicomclinicaltrialsitename="Institute of Human Virology Nigeria"
elif [ "${tcgatissuesourcesite}" = "PN" ]
then
	dicomclinicaltrialsitename="Institute of Human Virology Nigeria"
elif [ "${tcgatissuesourcesite}" = "PQ" ]
then
	dicomclinicaltrialsitename="University of Colorado Denver"
elif [ "${tcgatissuesourcesite}" = "PR" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "PT" ]
then
	dicomclinicaltrialsitename="Maine Medical Center"
elif [ "${tcgatissuesourcesite}" = "PZ" ]
then
	dicomclinicaltrialsitename="ABS - Lahey Clinic"
elif [ "${tcgatissuesourcesite}" = "Q1" ]
then
	dicomclinicaltrialsitename="University of Oklahoma HSC"
elif [ "${tcgatissuesourcesite}" = "Q2" ]
then
	dicomclinicaltrialsitename="University of Oklahoma HSC"
elif [ "${tcgatissuesourcesite}" = "Q3" ]
then
	dicomclinicaltrialsitename="University of Oklahoma HSC"
elif [ "${tcgatissuesourcesite}" = "Q4" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "Q9" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "QA" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "QB" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "QC" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "QD" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "QF" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "QG" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "QH" ]
then
	dicomclinicaltrialsitename="Fondazione-Besta"
elif [ "${tcgatissuesourcesite}" = "QJ" ]
then
	dicomclinicaltrialsitename="Mount Sinai School of Medicine"
elif [ "${tcgatissuesourcesite}" = "QK" ]
then
	dicomclinicaltrialsitename="Emory University - Winship Cancer Inst."
elif [ "${tcgatissuesourcesite}" = "QL" ]
then
	dicomclinicaltrialsitename="University of Chicago"
elif [ "${tcgatissuesourcesite}" = "QM" ]
then
	dicomclinicaltrialsitename="University of Oklahoma HSC"
elif [ "${tcgatissuesourcesite}" = "QN" ]
then
	dicomclinicaltrialsitename="ILSBio"
elif [ "${tcgatissuesourcesite}" = "QQ" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "QR" ]
then
	dicomclinicaltrialsitename="National Institutes of Health"
elif [ "${tcgatissuesourcesite}" = "QS" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "QT" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "QU" ]
then
	dicomclinicaltrialsitename="Harvard Beth Israel"
elif [ "${tcgatissuesourcesite}" = "QV" ]
then
	dicomclinicaltrialsitename="Instituto Nacional de Cancerologia"
elif [ "${tcgatissuesourcesite}" = "QW" ]
then
	dicomclinicaltrialsitename="Instituto Nacional de Cancerologia"
elif [ "${tcgatissuesourcesite}" = "R1" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "R2" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "R3" ]
then
	dicomclinicaltrialsitename="CHI-Penrose Colorado"
elif [ "${tcgatissuesourcesite}" = "R5" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "R6" ]
then
	dicomclinicaltrialsitename="MD Anderson Cancer Center"
elif [ "${tcgatissuesourcesite}" = "R7" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "R8" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "R9" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "RA" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "RB" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "RC" ]
then
	dicomclinicaltrialsitename="University of Utah"
elif [ "${tcgatissuesourcesite}" = "RD" ]
then
	dicomclinicaltrialsitename="Peter MacCallum Cancer Center"
elif [ "${tcgatissuesourcesite}" = "RE" ]
then
	dicomclinicaltrialsitename="Peter MacCallum Cancer Center"
elif [ "${tcgatissuesourcesite}" = "RG" ]
then
	dicomclinicaltrialsitename="Montefiore Medical Center"
elif [ "${tcgatissuesourcesite}" = "RH" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "RL" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "RM" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "RN" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "RP" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "RQ" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "RR" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "RS" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering Cancer Center"
elif [ "${tcgatissuesourcesite}" = "RT" ]
then
	dicomclinicaltrialsitename="Cleveland Clinic Foundation"
elif [ "${tcgatissuesourcesite}" = "RU" ]
then
	dicomclinicaltrialsitename="Northwestern University"
elif [ "${tcgatissuesourcesite}" = "RV" ]
then
	dicomclinicaltrialsitename="Northwestern University"
elif [ "${tcgatissuesourcesite}" = "RW" ]
then
	dicomclinicaltrialsitename="Michigan University"
elif [ "${tcgatissuesourcesite}" = "RX" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "RY" ]
then
	dicomclinicaltrialsitename="University of California San Francisco"
elif [ "${tcgatissuesourcesite}" = "RZ" ]
then
	dicomclinicaltrialsitename="Wills Eye Institute"
elif [ "${tcgatissuesourcesite}" = "S2" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "S3" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "S4" ]
then
	dicomclinicaltrialsitename="University of Chicago"
elif [ "${tcgatissuesourcesite}" = "S5" ]
then
	dicomclinicaltrialsitename="University of Oklahoma HSC"
elif [ "${tcgatissuesourcesite}" = "S6" ]
then
	dicomclinicaltrialsitename="Gundersen Lutheran Health System"
elif [ "${tcgatissuesourcesite}" = "S7" ]
then
	dicomclinicaltrialsitename="University Hospital Motol"
elif [ "${tcgatissuesourcesite}" = "S8" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "S9" ]
then
	dicomclinicaltrialsitename="Dept of Neurosurgery at University of Heidelberg"
elif [ "${tcgatissuesourcesite}" = "SA" ]
then
	dicomclinicaltrialsitename="ABS - IUPUI"
elif [ "${tcgatissuesourcesite}" = "SB" ]
then
	dicomclinicaltrialsitename="Baylor College of Medicine"
elif [ "${tcgatissuesourcesite}" = "SC" ]
then
	dicomclinicaltrialsitename="Memorial Sloan Kettering"
elif [ "${tcgatissuesourcesite}" = "SD" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "SE" ]
then
	dicomclinicaltrialsitename="Boston Medical Center"
elif [ "${tcgatissuesourcesite}" = "SG" ]
then
	dicomclinicaltrialsitename="Cleveland Clinic Foundation"
elif [ "${tcgatissuesourcesite}" = "SH" ]
then
	dicomclinicaltrialsitename="Papworth Hospital"
elif [ "${tcgatissuesourcesite}" = "SI" ]
then
	dicomclinicaltrialsitename="Washington University St. Louis"
elif [ "${tcgatissuesourcesite}" = "SJ" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "SK" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "SL" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital AZ"
elif [ "${tcgatissuesourcesite}" = "SN" ]
then
	dicomclinicaltrialsitename="BLN - Baylor"
elif [ "${tcgatissuesourcesite}" = "SO" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "SP" ]
then
	dicomclinicaltrialsitename="University Health Network"
elif [ "${tcgatissuesourcesite}" = "SQ" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "SR" ]
then
	dicomclinicaltrialsitename="Tufts Medical Center"
elif [ "${tcgatissuesourcesite}" = "SS" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "ST" ]
then
	dicomclinicaltrialsitename="Global Bioclinical-Moldova"
elif [ "${tcgatissuesourcesite}" = "SU" ]
then
	dicomclinicaltrialsitename="Global Bioclinical-Moldova"
elif [ "${tcgatissuesourcesite}" = "SW" ]
then
	dicomclinicaltrialsitename="Global Bioclinical-Moldova"
elif [ "${tcgatissuesourcesite}" = "SX" ]
then
	dicomclinicaltrialsitename="Mayo Clinic Arizona"
elif [ "${tcgatissuesourcesite}" = "SY" ]
then
	dicomclinicaltrialsitename="Mayo Clinic Arizona"
elif [ "${tcgatissuesourcesite}" = "T1" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital Arizona"
elif [ "${tcgatissuesourcesite}" = "T2" ]
then
	dicomclinicaltrialsitename="St. University of Colorado Denver"
elif [ "${tcgatissuesourcesite}" = "T3" ]
then
	dicomclinicaltrialsitename="Molecular Response"
elif [ "${tcgatissuesourcesite}" = "T6" ]
then
	dicomclinicaltrialsitename="Molecular Response"
elif [ "${tcgatissuesourcesite}" = "T7" ]
then
	dicomclinicaltrialsitename="Molecular Response"
elif [ "${tcgatissuesourcesite}" = "T9" ]
then
	dicomclinicaltrialsitename="Molecular Response"
elif [ "${tcgatissuesourcesite}" = "TE" ]
then
	dicomclinicaltrialsitename="Global BioClinical - Georgia"
elif [ "${tcgatissuesourcesite}" = "TG" ]
then
	dicomclinicaltrialsitename="Global BioClinical - Georgia"
elif [ "${tcgatissuesourcesite}" = "TK" ]
then
	dicomclinicaltrialsitename="Global BioClinical - Georgia"
elif [ "${tcgatissuesourcesite}" = "TL" ]
then
	dicomclinicaltrialsitename="Global BioClinical - Georgia"
elif [ "${tcgatissuesourcesite}" = "TM" ]
then
	dicomclinicaltrialsitename="The University of New South Wales"
elif [ "${tcgatissuesourcesite}" = "TN" ]
then
	dicomclinicaltrialsitename="Ohio State University"
elif [ "${tcgatissuesourcesite}" = "TP" ]
then
	dicomclinicaltrialsitename="Maine Medical Center"
elif [ "${tcgatissuesourcesite}" = "TQ" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "TR" ]
then
	dicomclinicaltrialsitename="Global Bioclinical-Moldova"
elif [ "${tcgatissuesourcesite}" = "TS" ]
then
	dicomclinicaltrialsitename="University of Pennsylvania"
elif [ "${tcgatissuesourcesite}" = "TT" ]
then
	dicomclinicaltrialsitename="University of Pennsylvania"
elif [ "${tcgatissuesourcesite}" = "TV" ]
then
	dicomclinicaltrialsitename="Wake Forest University"
elif [ "${tcgatissuesourcesite}" = "UB" ]
then
	dicomclinicaltrialsitename="UCSF"
elif [ "${tcgatissuesourcesite}" = "UC" ]
then
	dicomclinicaltrialsitename="University of Washington"
elif [ "${tcgatissuesourcesite}" = "UD" ]
then
	dicomclinicaltrialsitename="University of Western Australia"
elif [ "${tcgatissuesourcesite}" = "UE" ]
then
	dicomclinicaltrialsitename="Asterand"
elif [ "${tcgatissuesourcesite}" = "UF" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "UJ" ]
then
	dicomclinicaltrialsitename="Boston Medical Center"
elif [ "${tcgatissuesourcesite}" = "UL" ]
then
	dicomclinicaltrialsitename="Boston Medical Center"
elif [ "${tcgatissuesourcesite}" = "UN" ]
then
	dicomclinicaltrialsitename="Boston Medical Center"
elif [ "${tcgatissuesourcesite}" = "UP" ]
then
	dicomclinicaltrialsitename="Boston Medical Center"
elif [ "${tcgatissuesourcesite}" = "UR" ]
then
	dicomclinicaltrialsitename="Boston Medical Center"
elif [ "${tcgatissuesourcesite}" = "US" ]
then
	dicomclinicaltrialsitename="Garvan Institute of Medical Research"
elif [ "${tcgatissuesourcesite}" = "UT" ]
then
	dicomclinicaltrialsitename="Asbestos Diseases Research Institute"
elif [ "${tcgatissuesourcesite}" = "UU" ]
then
	dicomclinicaltrialsitename="Mary Bird Perkins Cancer Center - Our Lady of the Lake"
elif [ "${tcgatissuesourcesite}" = "UV" ]
then
	dicomclinicaltrialsitename="Capital Biosciences"
elif [ "${tcgatissuesourcesite}" = "UW" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "UY" ]
then
	dicomclinicaltrialsitename="University of California San Francisco"
elif [ "${tcgatissuesourcesite}" = "UZ" ]
then
	dicomclinicaltrialsitename="University of California San Francisco"
elif [ "${tcgatissuesourcesite}" = "V1" ]
then
	dicomclinicaltrialsitename="University of California San Francisco"
elif [ "${tcgatissuesourcesite}" = "V2" ]
then
	dicomclinicaltrialsitename="Cleveland Clinic Foundation"
elif [ "${tcgatissuesourcesite}" = "V3" ]
then
	dicomclinicaltrialsitename="Cleveland Clinic Foundation"
elif [ "${tcgatissuesourcesite}" = "V4" ]
then
	dicomclinicaltrialsitename="Institut Curie"
elif [ "${tcgatissuesourcesite}" = "V5" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "V6" ]
then
	dicomclinicaltrialsitename="Duke University"
elif [ "${tcgatissuesourcesite}" = "V7" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "V8" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "V9" ]
then
	dicomclinicaltrialsitename="Medical College of Georgia"
elif [ "${tcgatissuesourcesite}" = "VA" ]
then
	dicomclinicaltrialsitename="Alliance"
elif [ "${tcgatissuesourcesite}" = "VB" ]
then
	dicomclinicaltrialsitename="Global BioClinical - Georgia"
elif [ "${tcgatissuesourcesite}" = "VD" ]
then
	dicomclinicaltrialsitename="University of Liverpool"
elif [ "${tcgatissuesourcesite}" = "VF" ]
then
	dicomclinicaltrialsitename="University of Pennsylvania"
elif [ "${tcgatissuesourcesite}" = "VG" ]
then
	dicomclinicaltrialsitename="Institute of Human Virology Nigeria"
elif [ "${tcgatissuesourcesite}" = "VK" ]
then
	dicomclinicaltrialsitename="Institute of Human Virology Nigeria"
elif [ "${tcgatissuesourcesite}" = "VL" ]
then
	dicomclinicaltrialsitename="Institute of Human Virology Nigeria"
elif [ "${tcgatissuesourcesite}" = "VM" ]
then
	dicomclinicaltrialsitename="Huntsman Cancer Institute"
elif [ "${tcgatissuesourcesite}" = "VN" ]
then
	dicomclinicaltrialsitename="NCI Urologic Oncology Branch"
elif [ "${tcgatissuesourcesite}" = "VP" ]
then
	dicomclinicaltrialsitename="Washington University"
elif [ "${tcgatissuesourcesite}" = "VQ" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "VR" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "VS" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "VT" ]
then
	dicomclinicaltrialsitename="Vanderbilt"
elif [ "${tcgatissuesourcesite}" = "VV" ]
then
	dicomclinicaltrialsitename="John Wayne Cancer Center"
elif [ "${tcgatissuesourcesite}" = "VW" ]
then
	dicomclinicaltrialsitename="Northwestern University"
elif [ "${tcgatissuesourcesite}" = "VX" ]
then
	dicomclinicaltrialsitename="Northwestern University"
elif [ "${tcgatissuesourcesite}" = "VZ" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "W2" ]
then
	dicomclinicaltrialsitename="Medical College of Wisconsin"
elif [ "${tcgatissuesourcesite}" = "W3" ]
then
	dicomclinicaltrialsitename="John Wayne Cancer Center"
elif [ "${tcgatissuesourcesite}" = "W4" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "W5" ]
then
	dicomclinicaltrialsitename="Mayo Clinic Rochester"
elif [ "${tcgatissuesourcesite}" = "W6" ]
then
	dicomclinicaltrialsitename="UCSF"
elif [ "${tcgatissuesourcesite}" = "W7" ]
then
	dicomclinicaltrialsitename="Garvan Institute of Medical Research"
elif [ "${tcgatissuesourcesite}" = "W8" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "W9" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WA" ]
then
	dicomclinicaltrialsitename="University of Schleswig-Holstein"
elif [ "${tcgatissuesourcesite}" = "WB" ]
then
	dicomclinicaltrialsitename="Erasmus MC"
elif [ "${tcgatissuesourcesite}" = "WC" ]
then
	dicomclinicaltrialsitename="MD Anderson"
elif [ "${tcgatissuesourcesite}" = "WD" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "WE" ]
then
	dicomclinicaltrialsitename="Norfolk and Norwich Hospital"
elif [ "${tcgatissuesourcesite}" = "WF" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "WG" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "WH" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "WJ" ]
then
	dicomclinicaltrialsitename="Greenville Health System"
elif [ "${tcgatissuesourcesite}" = "WK" ]
then
	dicomclinicaltrialsitename="Brigham and Women's Hospital"
elif [ "${tcgatissuesourcesite}" = "WL" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WM" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WN" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WP" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WQ" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WR" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WS" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WT" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "WU" ]
then
	dicomclinicaltrialsitename="Wake Forest University"
elif [ "${tcgatissuesourcesite}" = "WW" ]
then
	dicomclinicaltrialsitename="Wake Forest University"
elif [ "${tcgatissuesourcesite}" = "WX" ]
then
	dicomclinicaltrialsitename="Yale University"
elif [ "${tcgatissuesourcesite}" = "WY" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "WZ" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "X2" ]
then
	dicomclinicaltrialsitename="University of Washington"
elif [ "${tcgatissuesourcesite}" = "X3" ]
then
	dicomclinicaltrialsitename="Cleveland Clinic Foundation"
elif [ "${tcgatissuesourcesite}" = "X4" ]
then
	dicomclinicaltrialsitename="Institute for Medical Research"
elif [ "${tcgatissuesourcesite}" = "X5" ]
then
	dicomclinicaltrialsitename="Institute of Human Virology Nigeria"
elif [ "${tcgatissuesourcesite}" = "X6" ]
then
	dicomclinicaltrialsitename="University of Iowa"
elif [ "${tcgatissuesourcesite}" = "X7" ]
then
	dicomclinicaltrialsitename="ABS IUPUI"
elif [ "${tcgatissuesourcesite}" = "X8" ]
then
	dicomclinicaltrialsitename="St. Joseph's Hospital Arizona"
elif [ "${tcgatissuesourcesite}" = "X9" ]
then
	dicomclinicaltrialsitename="University of California, Davis"
elif [ "${tcgatissuesourcesite}" = "XA" ]
then
	dicomclinicaltrialsitename="University of Minnesota"
elif [ "${tcgatissuesourcesite}" = "XB" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "XC" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "XD" ]
then
	dicomclinicaltrialsitename="Providence Portland Medical Center"
elif [ "${tcgatissuesourcesite}" = "XE" ]
then
	dicomclinicaltrialsitename="University of Southern California"
elif [ "${tcgatissuesourcesite}" = "XF" ]
then
	dicomclinicaltrialsitename="University of Southern California"
elif [ "${tcgatissuesourcesite}" = "XG" ]
then
	dicomclinicaltrialsitename="BLN UT Southwestern Medical Center at Dallas"
elif [ "${tcgatissuesourcesite}" = "XH" ]
then
	dicomclinicaltrialsitename="BLN Baylor"
elif [ "${tcgatissuesourcesite}" = "XJ" ]
then
	dicomclinicaltrialsitename="University of Kansas"
elif [ "${tcgatissuesourcesite}" = "XK" ]
then
	dicomclinicaltrialsitename="Mayo Clinic Arizona"
elif [ "${tcgatissuesourcesite}" = "XM" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "XN" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "XP" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "XQ" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "XR" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "XS" ]
then
	dicomclinicaltrialsitename="University of Sao Paulo"
elif [ "${tcgatissuesourcesite}" = "XT" ]
then
	dicomclinicaltrialsitename="Johns Hopkins"
elif [ "${tcgatissuesourcesite}" = "XU" ]
then
	dicomclinicaltrialsitename="University Health Network"
elif [ "${tcgatissuesourcesite}" = "XV" ]
then
	dicomclinicaltrialsitename="Capital Biosciences"
elif [ "${tcgatissuesourcesite}" = "XX" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "XY" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "Y3" ]
then
	dicomclinicaltrialsitename="University of New Mexico"
elif [ "${tcgatissuesourcesite}" = "Y5" ]
then
	dicomclinicaltrialsitename="University of Arizona"
elif [ "${tcgatissuesourcesite}" = "Y6" ]
then
	dicomclinicaltrialsitename="University of Arizona"
elif [ "${tcgatissuesourcesite}" = "Y8" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "YA" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "YB" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "YC" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "YD" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "YF" ]
then
	dicomclinicaltrialsitename="University of Puerto Rico"
elif [ "${tcgatissuesourcesite}" = "YG" ]
then
	dicomclinicaltrialsitename="University of Puerto Rico"
elif [ "${tcgatissuesourcesite}" = "YH" ]
then
	dicomclinicaltrialsitename="Stanford University"
elif [ "${tcgatissuesourcesite}" = "YJ" ]
then
	dicomclinicaltrialsitename="Stanford University"
elif [ "${tcgatissuesourcesite}" = "YL" ]
then
	dicomclinicaltrialsitename="PROCURE Biobank"
elif [ "${tcgatissuesourcesite}" = "YN" ]
then
	dicomclinicaltrialsitename="University of Arizona"
elif [ "${tcgatissuesourcesite}" = "YR" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "YS" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "YT" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "YU" ]
then
	dicomclinicaltrialsitename="Barretos Cancer Hospital"
elif [ "${tcgatissuesourcesite}" = "YV" ]
then
	dicomclinicaltrialsitename="MSKCC"
elif [ "${tcgatissuesourcesite}" = "YW" ]
then
	dicomclinicaltrialsitename="Albert Einstein Medical Center"
elif [ "${tcgatissuesourcesite}" = "YX" ]
then
	dicomclinicaltrialsitename="Emory University"
elif [ "${tcgatissuesourcesite}" = "YY" ]
then
	dicomclinicaltrialsitename="Roswell Park"
elif [ "${tcgatissuesourcesite}" = "YZ" ]
then
	dicomclinicaltrialsitename="The Ohio State University"
elif [ "${tcgatissuesourcesite}" = "Z2" ]
then
	dicomclinicaltrialsitename="IDI-IRCCS"
elif [ "${tcgatissuesourcesite}" = "Z3" ]
then
	dicomclinicaltrialsitename="UCLA"
elif [ "${tcgatissuesourcesite}" = "Z4" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "Z5" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "Z6" ]
then
	dicomclinicaltrialsitename="Cureline"
elif [ "${tcgatissuesourcesite}" = "Z7" ]
then
	dicomclinicaltrialsitename="John Wayne Cancer Center"
elif [ "${tcgatissuesourcesite}" = "Z8" ]
then
	dicomclinicaltrialsitename="John Wayne Cancer Center"
elif [ "${tcgatissuesourcesite}" = "ZA" ]
then
	dicomclinicaltrialsitename="Candler"
elif [ "${tcgatissuesourcesite}" = "ZB" ]
then
	dicomclinicaltrialsitename="Thoraxklinik"
elif [ "${tcgatissuesourcesite}" = "ZC" ]
then
	dicomclinicaltrialsitename="University of Mannheim"
elif [ "${tcgatissuesourcesite}" = "ZD" ]
then
	dicomclinicaltrialsitename="ILSbio"
elif [ "${tcgatissuesourcesite}" = "ZE" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "ZF" ]
then
	dicomclinicaltrialsitename="University of Sheffield"
elif [ "${tcgatissuesourcesite}" = "ZG" ]
then
	dicomclinicaltrialsitename="University Medical Center Hamburg-Eppendorf"
elif [ "${tcgatissuesourcesite}" = "ZH" ]
then
	dicomclinicaltrialsitename="University of North Carolina"
elif [ "${tcgatissuesourcesite}" = "ZJ" ]
then
	dicomclinicaltrialsitename="NCI HRE Branch"
elif [ "${tcgatissuesourcesite}" = "ZK" ]
then
	dicomclinicaltrialsitename="University of New Mexico"
elif [ "${tcgatissuesourcesite}" = "ZL" ]
then
	dicomclinicaltrialsitename="Valley Hospital"
elif [ "${tcgatissuesourcesite}" = "ZM" ]
then
	dicomclinicaltrialsitename="University of Ulm"
elif [ "${tcgatissuesourcesite}" = "ZN" ]
then
	dicomclinicaltrialsitename="Brigham and Women's Hospital Division of Thoracic Surgery"
elif [ "${tcgatissuesourcesite}" = "ZP" ]
then
	dicomclinicaltrialsitename="Medical College of Wisconsin"
elif [ "${tcgatissuesourcesite}" = "ZQ" ]
then
	dicomclinicaltrialsitename="Tayside Tissue Bank"
elif [ "${tcgatissuesourcesite}" = "ZR" ]
then
	dicomclinicaltrialsitename="Tayside Tissue Bank"
elif [ "${tcgatissuesourcesite}" = "ZS" ]
then
	dicomclinicaltrialsitename="Tayside Tissue Bank"
elif [ "${tcgatissuesourcesite}" = "ZT" ]
then
	dicomclinicaltrialsitename="International Genomics Consortium"
elif [ "${tcgatissuesourcesite}" = "ZU" ]
then
	dicomclinicaltrialsitename="Spectrum Health"
elif [ "${tcgatissuesourcesite}" = "ZW" ]
then
	dicomclinicaltrialsitename="University of Alabama"
elif [ "${tcgatissuesourcesite}" = "ZX" ]
then
	dicomclinicaltrialsitename="University of Alabama"
else
	dicomclinicaltrialsitename=""
fi

dicominstitutionname="${dicomclinicaltrialsitename}"

dicomclinicaltrialsubjectid="${dicompatientid}"

dicomspecimenuid=""
if [ ! -f "${FILEMAPPINGSPECIMENIDTOUID}" ]
then
	touch "${FILEMAPPINGSPECIMENIDTOUID}"
fi

if [ ! -z "${dicomspecimenidentifier}" ]
then
	# dicomspecimenidentifier may be prefix for other identifiers, so assure bounded by delimiters, and use first if duplicates else fails later
	dicomspecimenuid=`egrep "^${dicomspecimenidentifier}," "${FILEMAPPINGSPECIMENIDTOUID}" | awk -F, '{print $2}' | head -1`
	if [ -z "${dicomspecimenuid}" ]
	then
		dicomspecimenuid=`java -cp ${PIXELMEDDIR}/pixelmed.jar -Djava.awt.headless=true com.pixelmed.utils.UUIDBasedOID 2>&1`
		echo "${dicomspecimenidentifier},${dicomspecimenuid}" >>"${FILEMAPPINGSPECIMENIDTOUID}"
		echo "Created Specimen UID ${dicomspecimenuid} for Specimen ID ${dicomspecimenidentifier}"
	else
		echo "Reusing Specimen UID ${dicomspecimenuid} for Specimen ID ${dicomspecimenidentifier}"
	fi
fi
# dicomspecimenuid may still be unassigned if there is no dicomspecimenidentifier - let Java code fill in new one

dicomstudyuid=""
if [ ! -f "${FILEMAPPINGSTUDYIDTOUID}" ]
then
	touch "${FILEMAPPINGSTUDYIDTOUID}"
fi

if [ ! -z "${dicomstudyid}" ]
then
	# dicomstudyid may be prefix for other identifiers, so assure bounded by delimiters, and use first if duplicates else fails later
	dicomstudyuid=`egrep "^${dicomstudyid}," "${FILEMAPPINGSTUDYIDTOUID}" | awk -F, '{print $2}' | head -1`
	if [ -z "${dicomstudyuid}" ]
	then
		dicomstudyuid=`java -cp ${PIXELMEDDIR}/pixelmed.jar -Djava.awt.headless=true com.pixelmed.utils.UUIDBasedOID 2>&1`
		echo "${dicomstudyid},${dicomstudyuid}" >>"${FILEMAPPINGSTUDYIDTOUID}"
		echo "Created Study UID ${dicomstudyuid} for Study ID ${dicomstudyid}"
	else
		echo "Reusing Study UID ${dicomstudyuid} for Study ID ${dicomstudyid}"
	fi
fi
# dicomstudyuid may still be unassigned if there is no dicomstudyid - let Java code fill in new one

# Aperio "...ScanScope ID = SS1302|Filename = 11952||Date = 04/07/14|Time = 12:30:08|Time Zone = GMT-04:00|..."
# Hamamatsu "...|Date=12/12/2013|Time=03:21:44 PM|Copyright=Hamamatsu Photonics KK|"
# ignore timezone
# ignore Hamamatsu since would need us to add 12 to PM times
svsdatetime=`tiffinfo "${infile}" | grep -v Hamamatsu | grep ScanScope | grep Date | grep Time | head -1 | sed -e 's/^.*Date = \([0-9][0-9]\)[/]\([0-9][0-9]\)[/]\([0-9][0-9]\).*Time = \([0-9][0-9]\)[:]\([0-9][0-9]\)[:]\([0-9][0-9]\).*$/20\3\1\2\4\5\6/'`
if [ -z "${svsdatetime}" ]
then
	# SCN "...|Date = 2014-07-23T16:33:58.37Z|..."
	# ignore fraction, ignore that it is Zulu time
	svsdatetime=`tiffinfo "${infile}" | grep -v Hamamatsu | grep SCN | grep Date | head -1 | sed -e 's/^.*Date = \([0-9][0-9][0-9][0-9]\)-\([0-9][0-9]\)-\([0-9][0-9]\)T\([0-9][0-9]\)[:]\([0-9][0-9]\)[:]\([0-9][0-9]\).*$/\1\2\3\4\5\6/'`
	if [ -z "${svsdatetime}" ]
	then
		echo "Cannot extract an svsdatetime"
	else
		echo "SCN-style svsdatetime"
	fi
else
	echo "Aperio-style svsdatetime"
fi
echo "svsdatetime = ${svsdatetime}"

# ideally we would pick the earliest study date time, but that would require multiple passes, so just record the 1st encountered and make all the same to satisfy information model (dcentvfy)
dicomstudydatetime=""
if [ ! -f "${FILEMAPPINGSTUDYIDTODATETIME}" ]
then
	touch "${FILEMAPPINGSTUDYIDTODATETIME}"
fi

if [ ! -z "${dicomstudyid}" ]
then
	# should only be zero or one, but head -1 just in case
	dicomstudydatetime=`grep "${dicomstudyid}" "${FILEMAPPINGSTUDYIDTODATETIME}" | head -1 | awk -F, '{print $2}'`
	if [ -z "${dicomstudydatetime}" ]
	then
		if [ -z "${svsdatetime}" ]
		then
			# use current datetime, just as TIFFToDicom would, so that this is set now and reused for all future series for the same StudyID
			dicomstudydatetime=`date '+%Y%m%d%H%M%S'`
			echo "No SVS datetime, so using current datetime ${dicomstudydatetime}"
		else
			dicomstudydatetime="${svsdatetime}"
		fi
		echo "${dicomstudyid},${dicomstudydatetime}" >>"${FILEMAPPINGSTUDYIDTODATETIME}"
		echo "Created Study Date Time ${dicomstudydatetime} for Study ID ${dicomstudyid}"
	else
		echo "Reusing Study Date Time ${dicomstudydatetime} for Study ID ${dicomstudyid}"
	fi
fi
# dicomstudydatetime may still be unassigned if there is no dicomstudyid, or if not found in SVS header - let Java code fill in one based on SVS files ImageDescription
dicomstudydate=""
dicomstudytime=""
if [ ! -z "${dicomstudydatetime}" ]
then
	dicomstudydate=`echo "${dicomstudydatetime}" | sed -e 's/^\([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]\).*$/\1/'`
	dicomstudytime=`echo "${dicomstudydatetime}" | sed -e 's/^.*\([0-9][0-9][0-9][0-9][0-9][0-9]\)$/\1/'`
fi

dicomstudydescription="Histopathology"

echo "dicompatientname = ${dicompatientname}"
echo "dicompatientid = ${dicompatientid}"
echo "dicomstudyid = ${dicomstudyid}"
echo "dicomstudyuid = ${dicomstudyuid}"
echo "dicomstudydatetime = ${dicomstudydatetime}"
echo "dicomstudydate = ${dicomstudydate}"
echo "dicomstudytime = ${dicomstudytime}"
echo "dicomstudydescription = ${dicomstudydescription}"
echo "dicomaccessionnumber = ${dicomaccessionnumber}"
echo "dicomspecimenidentifier = ${dicomspecimenidentifier}"
echo "dicomspecimenuid = ${dicomspecimenuid}"
echo "dicomcontaineridentifier = ${dicomcontaineridentifier}"

echo "dicomparentspecimenportionanalyteidentifier = ${dicomparentspecimenportionanalyteidentifier}"
echo "dicomparentspecimenvialidentifier = ${dicomparentspecimenvialidentifier}"
echo "dicomparentspecimensampleidentifier = ${dicomparentspecimensampleidentifier}"

echo "dicomclinicaltrialcoordinatingcentername = ${dicomclinicaltrialcoordinatingcentername}"
echo "dicomclinicaltrialsponsorname = ${dicomclinicaltrialsponsorname}"
echo "dicomclinicalprotocolid = ${dicomclinicalprotocolid}"
echo "dicomclinicalprotocolname = ${dicomclinicalprotocolname}"
echo "dicomclinicaltrialsiteid = ${dicomclinicaltrialsiteid}"
echo "dicomclinicaltrialsitename = ${dicomclinicaltrialsitename}"
echo "dicomclinicaltrialsubjectid = ${dicomclinicaltrialsubjectid}"

echo "dicominstitutionname = ${dicominstitutionname}"

tissuetypecodevalue=""
tissuetypecsd="SCT"
tissuetypecodemeaning=""
tissuetypeshortdescription=""

# only 01 and 11 seem to occur, so don't check for all the others in "https://gdc.cancer.gov/resources-tcga-users/tcga-code-tables/sample-type-codes"
# use Short Letter Code within SpecimenShortDescription
if [ "${tcgasample}" = "11" ]
then
	tissuetypecodevalue="17621005"
	tissuetypecodemeaning="Normal"
	tissuetypeshortdescription="NT"
elif [ "${tcgasample}" = "01" ]
then
	tissuetypecodevalue="86049000"
	tissuetypecodemeaning="Neoplasm, Primary"
	tissuetypeshortdescription="TP"
fi

echo "anatomycodevalue = ${anatomycodevalue}"
echo "anatomycsd = ${anatomycsd}"
echo "anatomycodemeaning = ${anatomycodemeaning}"

if [ "${tcgatissueslideidtype}" = "DX" ]
then
	dicomspecimenshortdescription="FFPE HE ${tissuetypeshortdescription} ${tcgatissueslideidtype}${tcgatissueslideidnumber}"
else
	dicomspecimenshortdescription="Frozen HE ${tissuetypeshortdescription} ${tcgatissueslideidtype}${tcgatissueslideidnumber}"
fi
echo "dicomspecimenshortdescription = ${dicomspecimenshortdescription}"

dicomspecimendetaileddescription=""
echo "dicomspecimendetaileddescription = ${dicomspecimendetaileddescription}"

dicomseriesdescription="${dicomspecimenshortdescription}"
echo "dicomseriesdescription = ${dicomseriesdescription}"

echo  >"${TMPJSONFILE}" "{"
echo >>"${TMPJSONFILE}" "	\"options\" : {"
echo >>"${TMPJSONFILE}" "		\"AppendToContributingEquipmentSequence\" : false"
echo >>"${TMPJSONFILE}" "	},"
echo >>"${TMPJSONFILE}" "	\"top\" : {"
echo >>"${TMPJSONFILE}" "		\"PatientName\" : \"${dicompatientname}\","
echo >>"${TMPJSONFILE}" "		\"PatientID\" : \"${dicompatientid}\","
echo >>"${TMPJSONFILE}" "		\"StudyID\" : \"${dicomstudyid}\","
echo >>"${TMPJSONFILE}" "		\"StudyInstanceUID\" : \"${dicomstudyuid}\","
if [ ! -z "${dicomstudydate}" ]
then
	echo >>"${TMPJSONFILE}" "		\"StudyDate\" : \"${dicomstudydate}\","
fi
if [ ! -z "${dicomstudytime}" ]
then
	echo >>"${TMPJSONFILE}" "		\"StudyTime\" : \"${dicomstudytime}\","
fi
echo >>"${TMPJSONFILE}" "		\"StudyDescription\" : \"${dicomstudydescription}\","
echo >>"${TMPJSONFILE}" "		\"ClinicalTrialSponsorName\" : \"${dicomclinicaltrialsponsorname}\","
echo >>"${TMPJSONFILE}" "		\"ClinicalTrialProtocolID\" : \"${dicomclinicalprotocolid}\","
echo >>"${TMPJSONFILE}" "		\"00130010\" : \"CTP\","
echo >>"${TMPJSONFILE}" "		\"00131010\" : \"${dicomclinicalprotocolid}\","
echo >>"${TMPJSONFILE}" "		\"ClinicalTrialProtocolName\" : \"${dicomclinicalprotocolname}\","
echo >>"${TMPJSONFILE}" "		\"ClinicalTrialSiteID\" : \"${dicomclinicaltrialsiteid}\","
echo >>"${TMPJSONFILE}" "		\"ClinicalTrialSiteName\" : \"${dicomclinicaltrialsitename}\","
echo >>"${TMPJSONFILE}" "		\"ClinicalTrialSubjectID\" : \"${dicomclinicaltrialsubjectid}\","
echo >>"${TMPJSONFILE}" "		\"ClinicalTrialCoordinatingCenterName\" : \"${dicomclinicaltrialcoordinatingcentername}\","
if [ ! -z "${dicominstitutionname}" ]
then
	echo >>"${TMPJSONFILE}" "		\"InstitutionName\" : \"${dicominstitutionname}\","
fi
echo >>"${TMPJSONFILE}" "		\"SeriesNumber\" : \"1\","
echo >>"${TMPJSONFILE}" "		\"SeriesDescription\" : \"${dicomseriesdescription}\","
echo >>"${TMPJSONFILE}" "		\"AccessionNumber\" : \"${dicomaccessionnumber}\","
echo >>"${TMPJSONFILE}" "		\"ContainerIdentifier\" : \"${dicomcontaineridentifier}\","
echo >>"${TMPJSONFILE}" "		\"IssuerOfTheContainerIdentifierSequence\" : [],"
# CP 2143 - use 433466003 Microscope slide (physical object) rather than 258661006 Slide (specimen) (being inactivated) or new 1179252003 Slide submitted as specimen (specimen)
echo >>"${TMPJSONFILE}" "		\"ContainerTypeCodeSequence\" : { \"cv\" : \"433466003\", \"csd\" : \"SCT\", \"cm\" : \"Microscope slide\" },"
echo >>"${TMPJSONFILE}" "		\"SpecimenDescriptionSequence\" : ["
echo >>"${TMPJSONFILE}" "	      {"
echo >>"${TMPJSONFILE}" "		    \"SpecimenIdentifier\" : \"${dicomspecimenidentifier}\","
echo >>"${TMPJSONFILE}" "		    \"IssuerOfTheSpecimenIdentifierSequence\" : [],"
echo >>"${TMPJSONFILE}" "		    \"SpecimenUID\" : \"${dicomspecimenuid}\","
if [ ! -z "${dicomspecimenshortdescription}" ]
then
	echo >>"${TMPJSONFILE}" "		\"SpecimenShortDescription\" : \"${dicomspecimenshortdescription}\","
fi
if [ ! -z "${dicomspecimendetaileddescription}" ]
then
	echo >>"${TMPJSONFILE}" "		\"SpecimenDetailedDescription\" : \"${dicomspecimendetaileddescription}\","
fi
echo >>"${TMPJSONFILE}" "		    \"SpecimenPreparationSequence\" : ["
echo >>"${TMPJSONFILE}" "		      {"
echo >>"${TMPJSONFILE}" "			    \"SpecimenPreparationStepContentItemSequence\" : ["
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"121041\", \"csd\" : \"DCM\", \"cm\" : \"Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomparentspecimensampleidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"434711009\", \"csd\" : \"SCT\", \"cm\" : \"Specimen container\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"434711009\", \"csd\" : \"SCT\", \"cm\" : \"Specimen container\" }"
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
# value "Tissue specimen" is SNOMED CT common parent of all more specific specimens and samples - there is no "Tissue sample" per se
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"371439000\", \"csd\" : \"SCT\", \"cm\" : \"Specimen type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"119376003\", \"csd\" : \"SCT\", \"cm\" : \"Tissue specimen\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111701\", \"csd\" : \"DCM\", \"cm\" : \"Processing type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"17636008\", \"csd\" : \"SCT\", \"cm\" : \"Specimen Collection\" }"
echo >>"${TMPJSONFILE}" "			      },"
# we don't really know whether it was excision or biopsy, so use generic (common parent) removal concept - not yet in CID 8109 Specimen Collection Procedure :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"17636008\", \"csd\" : \"SCT\", \"cm\" : \"Specimen Collection\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"118292001\", \"csd\" : \"SCT\", \"cm\" : \"Removal\" }"
echo >>"${TMPJSONFILE}" "			      }"
echo >>"${TMPJSONFILE}" "			    ]"
echo >>"${TMPJSONFILE}" "		      },"
echo >>"${TMPJSONFILE}" "		      {"
echo >>"${TMPJSONFILE}" "			    \"SpecimenPreparationStepContentItemSequence\" : ["
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"121041\", \"csd\" : \"DCM\", \"cm\" : \"Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomparentspecimenvialidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"434711009\", \"csd\" : \"SCT\", \"cm\" : \"Specimen container\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"434746001\", \"csd\" : \"SCT\", \"cm\" : \"Specimen vial\" }"
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"371439000\", \"csd\" : \"SCT\", \"cm\" : \"Specimen type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"119376003\", \"csd\" : \"SCT\", \"cm\" : \"Tissue specimen\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111701\", \"csd\" : \"DCM\", \"cm\" : \"Processing type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"433465004\", \"csd\" : \"SCT\", \"cm\" : \"Specimen Sampling\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111704\", \"csd\" : \"DCM\", \"cm\" : \"Sampling Method\" },"
# 433465004 is not in DICOM PS3.16 and not in CID 8110 Specimen Sampling Procedure :(
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"433465004\", \"csd\" : \"SCT\", \"cm\" : \"Sampling of tissue specimen\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111705\", \"csd\" : \"DCM\", \"cm\" : \"Parent Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomparentspecimensampleidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111707\", \"csd\" : \"DCM\", \"cm\" : \"Parent specimen type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"119376003\", \"csd\" : \"SCT\", \"cm\" : \"Tissue specimen\" }"
echo >>"${TMPJSONFILE}" "			      }"
echo >>"${TMPJSONFILE}" "			    ]"
echo >>"${TMPJSONFILE}" "		      },"
echo >>"${TMPJSONFILE}" "		      {"
echo >>"${TMPJSONFILE}" "			    \"SpecimenPreparationStepContentItemSequence\" : ["
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"121041\", \"csd\" : \"DCM\", \"cm\" : \"Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomparentspecimenportionanalyteidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111701\", \"csd\" : \"DCM\", \"cm\" : \"Processing type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"433465004\", \"csd\" : \"SCT\", \"cm\" : \"Specimen Sampling\" }"
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"434711009\", \"csd\" : \"SCT\", \"cm\" : \"Specimen container\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"434464009\", \"csd\" : \"SCT\", \"cm\" : \"Tissue cassette\" }"
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"371439000\", \"csd\" : \"SCT\", \"cm\" : \"Specimen type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"430861001\", \"csd\" : \"SCT\", \"cm\" : \"Gross specimen\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111704\", \"csd\" : \"DCM\", \"cm\" : \"Sampling Method\" },"
# 433465004 is not in DICOM PS3.16 and not in CID 8110 Specimen Sampling Procedure :(
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"433465004\", \"csd\" : \"SCT\", \"cm\" : \"Sampling of tissue specimen\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111705\", \"csd\" : \"DCM\", \"cm\" : \"Parent Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomparentspecimenvialidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111707\", \"csd\" : \"DCM\", \"cm\" : \"Parent specimen type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"119376003\", \"csd\" : \"SCT\", \"cm\" : \"Tissue specimen\" }"
echo >>"${TMPJSONFILE}" "			      }"
echo >>"${TMPJSONFILE}" "			    ]"
echo >>"${TMPJSONFILE}" "		      },"
echo >>"${TMPJSONFILE}" "		      {"
echo >>"${TMPJSONFILE}" "			    \"SpecimenPreparationStepContentItemSequence\" : ["
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"121041\", \"csd\" : \"DCM\", \"cm\" : \"Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomspecimenidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"434711009\", \"csd\" : \"SCT\", \"cm\" : \"Specimen container\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"433466003\", \"csd\" : \"SCT\", \"cm\" : \"Microscope slide\" }"
echo >>"${TMPJSONFILE}" "			      },"
# not yet in TID 8001 Specimen Preparation or TID 8002 Specimen Sampling :(
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"371439000\", \"csd\" : \"SCT\", \"cm\" : \"Specimen type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"1179252003\", \"csd\" : \"SCT\", \"cm\" : \"Slide\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111701\", \"csd\" : \"DCM\", \"cm\" : \"Processing type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"433465004\", \"csd\" : \"SCT\", \"cm\" : \"Specimen Sampling\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111704\", \"csd\" : \"DCM\", \"cm\" : \"Sampling Method\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"434472006\", \"csd\" : \"SCT\", \"cm\" : \"Block sectioning\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111705\", \"csd\" : \"DCM\", \"cm\" : \"Parent Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomparentspecimenportionanalyteidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111707\", \"csd\" : \"DCM\", \"cm\" : \"Parent specimen type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"430861001\", \"csd\" : \"SCT\", \"cm\" : \"Gross specimen\" }"
echo >>"${TMPJSONFILE}" "			      }"
echo >>"${TMPJSONFILE}" "			    ]"
echo >>"${TMPJSONFILE}" "		      },"
if [ "${tcgatissueslideidtype}" = "DX" ]
then
	echo >>"${TMPJSONFILE}" "		     {"
	echo >>"${TMPJSONFILE}" "		      \"SpecimenPreparationStepContentItemSequence\" : ["
	echo >>"${TMPJSONFILE}" "			     {"
	echo >>"${TMPJSONFILE}" "		   		\"ValueType\" : \"TEXT\","
	echo >>"${TMPJSONFILE}" "				\"ConceptNameCodeSequence\" : { \"cv\" : \"121041\", \"csd\" : \"DCM\", \"cm\" : \"Specimen Identifier\" },"
	echo >>"${TMPJSONFILE}" "		   		\"TextValue\" : \"${dicomparentspecimenportionanalyteidentifier}\""
	echo >>"${TMPJSONFILE}" "		      },"
	echo >>"${TMPJSONFILE}" "		      {"
	echo >>"${TMPJSONFILE}" "	    		\"ValueType\" : \"CODE\","
	echo >>"${TMPJSONFILE}" "				\"ConceptNameCodeSequence\" : { \"cv\" : \"111701\", \"csd\" : \"DCM\", \"cm\" : \"Processing type\" },"
	echo >>"${TMPJSONFILE}" "				\"ConceptCodeSequence\" :     { \"cv\" : \"9265001\", \"csd\" : \"SCT\", \"cm\" : \"Specimen processing\" }"
	echo >>"${TMPJSONFILE}" "		      },"
	echo >>"${TMPJSONFILE}" "		      {"
	echo >>"${TMPJSONFILE}" "	    		\"ValueType\" : \"CODE\","
	echo >>"${TMPJSONFILE}" "				\"ConceptNameCodeSequence\" : { \"cv\" : \"430864009\", \"csd\" : \"SCT\", \"cm\" : \"Tissue Fixative\" },"
	echo >>"${TMPJSONFILE}" "				\"ConceptCodeSequence\" :     { \"cv\" : \"431510009\", \"csd\" : \"SCT\", \"cm\" : \"Formalin\" }"
	echo >>"${TMPJSONFILE}" "		      }"
	echo >>"${TMPJSONFILE}" "		    ]"
	echo >>"${TMPJSONFILE}" "	      },"
fi
echo >>"${TMPJSONFILE}" "		      {"
echo >>"${TMPJSONFILE}" "			    \"SpecimenPreparationStepContentItemSequence\" : ["
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"121041\", \"csd\" : \"DCM\", \"cm\" : \"Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomparentspecimenportionanalyteidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111701\", \"csd\" : \"DCM\", \"cm\" : \"Processing type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"9265001\", \"csd\" : \"SCT\", \"cm\" : \"Specimen processing\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"430863003\", \"csd\" : \"SCT\", \"cm\" : \"Embedding medium\" },"
if [ "${tcgatissueslideidtype}" = "DX" ]
then
	echo >>"${TMPJSONFILE}" "				\"ConceptCodeSequence\" :     { \"cv\" : \"311731000\", \"csd\" : \"SCT\", \"cm\" : \"Paraffin wax\" }"
else
	echo >>"${TMPJSONFILE}" "				\"ConceptCodeSequence\" :     { \"cv\" : \"433469005\", \"csd\" : \"SCT\", \"cm\" : \"Tissue freezing medium\" }"
fi
echo >>"${TMPJSONFILE}" "			      }"
echo >>"${TMPJSONFILE}" "			    ]"
echo >>"${TMPJSONFILE}" "		      },"
echo >>"${TMPJSONFILE}" "		      {"
echo >>"${TMPJSONFILE}" "			    \"SpecimenPreparationStepContentItemSequence\" : ["
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"TEXT\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"121041\", \"csd\" : \"DCM\", \"cm\" : \"Specimen Identifier\" },"
echo >>"${TMPJSONFILE}" "		    		\"TextValue\" : \"${dicomspecimenidentifier}\""
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"111701\", \"csd\" : \"DCM\", \"cm\" : \"Processing type\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"127790008\", \"csd\" : \"SCT\", \"cm\" : \"Staining\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"424361007\", \"csd\" : \"SCT\", \"cm\" : \"Using substance\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"12710003\", \"csd\" : \"SCT\", \"cm\" : \"hematoxylin stain\" }"
echo >>"${TMPJSONFILE}" "			      },"
echo >>"${TMPJSONFILE}" "			      {"
echo >>"${TMPJSONFILE}" "		    		\"ValueType\" : \"CODE\","
echo >>"${TMPJSONFILE}" "					\"ConceptNameCodeSequence\" : { \"cv\" : \"424361007\", \"csd\" : \"SCT\", \"cm\" : \"Using substance\" },"
echo >>"${TMPJSONFILE}" "					\"ConceptCodeSequence\" :     { \"cv\" : \"36879007\", \"csd\" : \"SCT\", \"cm\" : \"water soluble eosin stain\" }"
echo >>"${TMPJSONFILE}" "			      }"
echo >>"${TMPJSONFILE}" "			    ]"
echo >>"${TMPJSONFILE}" "		      }"
if [ ! -z "${anatomycodevalue}" ]
then
	echo >>"${TMPJSONFILE}" "	    ],"
if [ -z "${tissuetypecodevalue}" ]
then
	echo >>"${TMPJSONFILE}" "	    \"PrimaryAnatomicStructureSequence\" : { \"cv\" : \"${anatomycodevalue}\", \"csd\" : \"${anatomycsd}\", \"cm\" : \"${anatomycodemeaning}\" }"
else
	echo >>"${TMPJSONFILE}" "	    \"PrimaryAnatomicStructureSequence\" : ["
	echo >>"${TMPJSONFILE}" "	      {"
	echo >>"${TMPJSONFILE}" "	   		\"CodeValue\" : \"${anatomycodevalue}\","
	echo >>"${TMPJSONFILE}" "	   		\"CodingSchemeDesignator\" : \"${anatomycsd}\","
	echo >>"${TMPJSONFILE}" "	   		\"CodeMeaning\" : \"${anatomycodemeaning}\","
	echo >>"${TMPJSONFILE}" "	   		\"PrimaryAnatomicStructureModifierSequence\" : { \"cv\" : \"${tissuetypecodevalue}\", \"csd\" : \"${tissuetypecsd}\", \"cm\" : \"${tissuetypecodemeaning}\" }"
	echo >>"${TMPJSONFILE}" "	      }"
	echo >>"${TMPJSONFILE}" "	    ]"
fi
else
	echo >>"${TMPJSONFILE}" "	    ]"
fi
echo >>"${TMPJSONFILE}" "	      }"
echo >>"${TMPJSONFILE}" "		],"
echo >>"${TMPJSONFILE}" "		\"OpticalPathSequence\" : ["
echo >>"${TMPJSONFILE}" "	      {"
echo >>"${TMPJSONFILE}" "		    \"OpticalPathIdentifier\" : \"1\","
echo >>"${TMPJSONFILE}" "		    \"IlluminationColorCodeSequence\" : { \"cv\" : \"414298005\", \"csd\" : \"SCT\", \"cm\" : \"Full Spectrum\" },"
echo >>"${TMPJSONFILE}" "		    \"IlluminationTypeCodeSequence\" :  { \"cv\" : \"111744\",  \"csd\" : \"DCM\", \"cm\" : \"Brightfield illumination\" }"
echo >>"${TMPJSONFILE}" "	      }"
echo >>"${TMPJSONFILE}" "		]"
echo >>"${TMPJSONFILE}" "	}"
echo >>"${TMPJSONFILE}" "}"

cat "${TMPJSONFILE}"

tiffinfo "${infile}"

rm -rf "${outdir}"
mkdir -p "${outdir}"
date
java -cp ${PIXELMEDDIR}/pixelmed.jar:${PATHTOADDITIONAL}/javax.json-1.0.4.jar:${PATHTOADDITIONAL}/opencsv-2.4.jar:${PATHTOADDITIONAL}/jai_imageio.jar \
	-Djava.awt.headless=true \
	-XX:-UseGCOverheadLimit \
	-Xmx8g \
	-Dorg.slf4j.simpleLogger.log.com.pixelmed.convert.TIFFToDicom=debug \
	-Dorg.slf4j.simpleLogger.log.com.pixelmed.convert.AddTIFFOrOffsetTables=info \
	com.pixelmed.convert.TIFFToDicom \
	"${TMPJSONFILE}" \
	"${infile}" \
	"${outdir}/DCM" \
	SM 1.2.840.10008.5.1.4.1.1.77.1.6 \
	ADDTIFF MERGESTRIPS DONOTADDDCMSUFFIX INCLUDEFILENAME \
	${uidarg}
date
rm "${TMPJSONFILE}"
rm -f "${TMPSLIDEUIDFILE}"
ls -l "${outdir}"

for rename in ${outdir}/*
do
	mv -- "$rename" "${rename%}.dcm"
done

for i in ${outdir}/*
do
	dciodvfy -filename "$i" 2>&1 | egrep -v '(Retired Person Name form|Warning - Unrecognized defined term <THUMBNAIL>|Error - Value is zero for value 1 of attribute <Slice Thickness>|Error - Value is zero for value 1 of attribute <Imaged Volume Depth>)'
done

#for i in ${outdir}/*
#do
#	dcfile -filename "$i"
#done

# Not -decimal (which is nice for rows, cols) because fails to display FL and FD values at all ([bugs.dicom3tools] (000554)) :(
(cd "${outdir}"; dctable -describe -recurse -k TransferSyntaxUID -k FrameOfReferenceUID -k LossyImageCompression -k LossyImageCompressionMethod -k LossyImageCompressionRatio -k InstanceNumber -k ImageType -k FrameType -k PhotometricInterpretation -k NumberOfFrames -k Rows -k Columns -k ImagedVolumeWidth -k ImagedVolumeHeight -k ImagedVolumeDepth -k ImageOrientationSlide -k XOffsetInSlideCoordinateSystem -k YOffsetInSlideCoordinateSystem -k PixelSpacing -k ObjectiveLensPower -k PrimaryAnatomicStructureSequence -k PrimaryAnatomicStructureModifierSequence -k ClinicalTrialProtocolID DCM*)

#for i in ${outdir}/*
#do
#	echo "$i"
#	tiffinfo "$i"
#done

# TIFF validation by JHOVE - throws java.io.IOException: Unable to create temporary file
#for i in ${outdir}/*
#do
#	echo "$i"
#	"${JHOVE}" "$i"
#done

#baselayerfile=`find "${outdir}" -name '*.dcm' | sort | head -1`
#echo "Making pyramids from ${baselayerfile} ..."
#date
#java -cp ${PIXELMEDDIR}/pixelmed.jar:${PATHTOADDITIONAL}/jai_imageio.jar \
#	-Djava.awt.headless=true \
#	-XX:-UseGCOverheadLimit \
#	-Xmx8g \
#	com.pixelmed.apps.TiledPyramid \
#	"${baselayerfile}" \
#	"${outdir}"
#date

echo "dcentvfy ..."
dcentvfy ${outdir}/*

#will not add pyramid files (yet) if created since name not DCM*
(cd "${outdir}"; \
	#java -cp ${PIXELMEDDIR}/pixelmed.jar -Djava.awt.headless=true com.pixelmed.dicom.DicomDirectory DICOMDIR DCM*; \
	#dciodvfy -new DICOMDIR 2>&1 | egrep -v '(Retired Person Name form|Warning - Attribute is not present in standard DICOM IOD|Warning - Dicom dataset contains attributes not present in standard DICOM IOD)'; \
	#dcdirdmp -v DICOMDIR \
)
