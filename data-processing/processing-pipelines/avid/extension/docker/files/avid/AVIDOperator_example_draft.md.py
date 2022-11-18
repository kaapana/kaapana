dag = DAG(
    dag_id='demo-avid-python-example',
    default_args=args,
    schedule_interval=None,
    concurrency=30,
    max_active_runs=15
)


def my_function(outputs, **kwargs):
    with open(outputs[0], "w") as ofile:
         ofile.write(str(kwargs))
    print(str(kwargs))

other_arguments = {'dag':dag, 'python_callable':my_function, 'name':'avid_py_op', 'output_default_extension':'txt'}

get_input = LocalGetInputDataOperator(dag=dag)
avid = AVIDPythonOperator(input_operator=get_input, **other_arguments)
put_statistcs_to_minio = LocalMinioOperator(dag=dag, action='put', task_id="minio-put-statistics", zip_files=True, action_operators=[avid])

clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> avid >> put_statistcs_to_minio >> clean

##########################################
##########################################
#Examples for different configurations (rest of the dag can stay untouched):
#
#Assume example data set:
# - Patient1
#   - Pat1_MR_TP1
#	- Pat1_MR_TP2
#	- Pat1_CT_TP1
# - Patient2
#   - Pat2_MR1_TP1
#	- Pat2_MR2_TP1
#   - Pat2_MR1_TP2
#	- Pat2_CT_TP1
#	- Pat2_CT_TP2


#Example 1: only select a specific modality (here MR) and make a call per image
avid = AVIDPythonOperator(input_operator=get_input+DCM_MODALITY_MR_SELECTOR, **other_arguments)
# Results/calls:
# - output0: {primaryInput: [Pat1_MR_TP1]}
# - output1: {primaryInput: [Pat1_MR_TP2]}
# - output2: {primaryInput: [Pat2_MR1_TP1]}
# - output3: {primaryInput: [Pat2_MR2_TP1]}
# - output4: {primaryInput: [Pat2_MR1_TP2]}


#Example 2: like example 1 but choose another variable name
avid = AVIDPythonOperator(input_operator=get_input+DCM_MODALITY_MR_SELECTOR,
                          input_alias='mr_images', **other_arguments)
# Results/calls:
# - output0: {mr_images: [Pat1_MR_TP1]}
# - output1: {mr_images: [Pat1_MR_TP2]}
# - output2: {mr_images: [Pat2_MR1_TP1]}
# - output3: {mr_images: [Pat2_MR2_TP1]}
# - output4: {mr_images: [Pat2_MR1_TP2]}


#Example 3: select MR and CT images and call them pairwise (folding both sets)
avid = AVIDPythonOperator(input_operator=get_input+DCM_MODALITY_MR_SELECTOR,
                          additional_inputs={'ct_images': get_input+DCM_MODALITY_CT_SELECTOR},
						  input_alias='mr_images', **other_arguments)
# Results/calls:
# - output0: {mr_images: [Pat1_MR_TP1], ct_images: [Pat1_CT_TP1]}
# - output1: {mr_images: [Pat1_MR_TP2], ct_images: [Pat1_CT_TP1]}
# - output2: {mr_images: [Pat2_MR1_TP1], ct_images: [Pat2_CT_TP1]}
# - output3: {mr_images: [Pat2_MR2_TP1], ct_images: [Pat2_CT_TP1]}
# - output4: {mr_images: [Pat2_MR1_TP2], ct_images: [Pat2_CT_TP1]}
# - output5: {mr_images: [Pat2_MR1_TP1], ct_images: [Pat2_CT_TP2]}
# - output6: {mr_images: [Pat2_MR2_TP1], ct_images: [Pat2_CT_TP2]}
# - output7: {mr_images: [Pat2_MR1_TP2], ct_images: [Pat2_CT_TP2]}


#Example 3: select MR and CT images and call them pairwise (but only MRs and CTs of same patient and timepoint)
avid = AVIDPythonOperator(input_operator=get_input+DCM_MODALITY_MR_SELECTOR,
                          additional_inputs={'ct_images': get_input+DCM_MODALITY_CT_SELECTOR},
						  linkers={'ct_images': CaseLinker()+TimePointLinker()}
						  input_alias='mr_images', **other_arguments)
# Results/calls:
# - output0: {mr_images: [Pat1_MR_TP1], ct_images: [Pat1_CT_TP1]}
# - output1: {mr_images: [Pat2_MR1_TP1], ct_images: [Pat2_CT_TP1]}
# - output2: {mr_images: [Pat2_MR2_TP1], ct_images: [Pat2_CT_TP1]}
# - output3: {mr_images: [Pat2_MR1_TP2], ct_images: [Pat2_CT_TP2]}


#Example 4: select MR and CT images and call them case wise
avid = AVIDPythonOperator(input_operator=get_input+DCM_MODALITY_MR_SELECTOR,
                          additional_inputs={'ct_images': get_input+DCM_MODALITY_CT_SELECTOR},
						  splitters={'mr_images', CaseSplitter(), 'ct_images': CaseSplitter()}
						  input_alias='mr_images', **other_arguments)
# Results/calls:
# - output0: {mr_images: [Pat1_MR_TP1, Pat1_MR_TP2], ct_images: [Pat1_CT_TP1]}
# - output1: {mr_images: [Pat2_MR1_TP1, Pat2_MR2_TP1, Pat2_MR1_TP2], ct_images: [Pat2_CT_TP1, Pat2_CT_TP2]}


