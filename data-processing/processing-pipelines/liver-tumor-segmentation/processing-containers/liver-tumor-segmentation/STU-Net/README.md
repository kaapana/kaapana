# STU-Net
**STU-Net: Scalable and Transferable Medical Image Segmentation Models Empowered by Large-Scale Supervised Pre-training** \
*Ziyan Huang, Haoyu Wang, Zhongying Deng, Jin Ye, Yanzhou Su, Hui Sun, Junjun He, Yun Gu, Lixu Gu, Shaoting Zhang, Yu Qiao* \
[Apr. 13, 2023] [arXiv, 2023] 
<p float="left">
  <img src="assets/fig_bubble.png?raw=true" width="47.5%" />
  <img src="assets/fig_model.png?raw=true" width="47.5%" /> 
</p>

## News
- STU-Net won the championship at the MICCAI 2023 ATLAS Challenge. [leaderboard](https://atlas-challenge.u-bourgogne.fr/leaderboard)
- STU-Net won the championship at the MICCAI 2023 SPPIN Challenge. [leaderboard](https://sppin.grand-challenge.org/evaluation/final-test-phase/leaderboard/)
- STU-Net was the runner-up at the MICCAI 2023 AutoPET II Challenge (Highest DSC value). [leaderboard](https://autopet-ii.grand-challenge.org/leaderboard/)
- At the MICCAI 2023 BraTS2023 competition, STU-Net secured one runner-up and two third-place finishes. [BraTS23](https://www.synapse.org/#!Synapse:syn51156910/wiki/622343)
- STU-Net took third place at the FLARE 2023 competition. [leaderboard](https://codalab.lisn.upsaclay.fr/competitions/12239#learn_the_details-awards)
 

## Key Features
- **Scalability**: STU-Net is designed for scalability, offering models of various sizes (S, B, L, H), including STU-Net-H, the largest medical image segmentation model to date with 1.4B parameters.
- **Transferability**: STU-Net is pre-trained on a large-scale TotalSegmentator dataset (>100k annotations) and is capable of being fine-tuned for various downstream tasks.
- **Based on nnU-Net**: Built upon the widely recognized nnUNet framework, STU-Net provides a robust and validated foundation for medical image segmentation.

## Links
- [Paper](https://arxiv.org/abs/2304.06716)
- [Model](https://drive.google.com/drive/folders/1VYfpPLANIrlQdR3HnNjZMtJBx7OPGi64?usp=sharing)
- [Code](https://github.com/Ziyan-Huang/STU-Net/)

## Details
>Large-scale models pre-trained on large-scale datasets have profoundly advanced the development of deep learning. However, the state-of-the-art models for medical image segmentation are still small-scale, with their parameters only in the tens of millions. Further scaling them up to higher orders of magnitude is rarely explored. An overarching goal of exploring large-scale models is to train them on large-scale medical segmentation datasets for better transfer capacities. In this work, we design a series of Scalable and Transferable U-Net (STU-Net) models, with parameter sizes ranging from 14 million to 1.4 billion. Notably, the 1.4B STU-Net is the largest medical image segmentation model to date. Our STU-Net is based on nnU-Net framework due to its popularity and impressive performance. We first refine the default convolutional blocks in nnU-Net to make them scalable. Then, we empirically evaluate different scaling combinations of network depth and width, discovering that it is optimal to scale model depth and width together. We train our scalable STU-Net models on a large-scale TotalSegmentator dataset and find that increasing model size brings a stronger performance gain. This observation reveals that a large model is promising in medical image segmentation. Furthermore, we evaluate the transferability of our model on 14 downstream datasets for direct inference and 3 datasets for further fine-tuning, covering various modalities and segmentation targets. We observe good performance of our pre-trained model in both direct inference and fine-tuning.

## Main Results

<p align="center">
  <img src="assets/fig_percent_training_case.png?raw=true" width="50%" alt="Segmentation performance comparison for different model sizes" />
</p>
<p align="center">
  With an increase in model size, the segmentation performance on large-scale datasets improves. Furthermore, larger models demonstrate greater data efficiency in medical image segmentation compared to their smaller counterparts.
</p>

<p align="center">
  <img src="assets/fig_expert_vs_one.png?raw=true" width="100%" />
</p>
<p align="center">
With an increase in model size, universal models become capable of concurrently segmenting numerous categories, exhibiting significant performance advancements.
</p>

<p align="center">
  <img src="assets/direct_inference_table.png?raw=true" width="50%" />
</p>
<p align="center">
With an increase in model size, models trained on large-scale datasets exhibit stronger performance when directly inferring downstream tasks.
</p>

<p align="center">
  <img src="assets/finetune_table.png?raw=true" width="100%" />
</p>
<p align="center">
With an increase in model size, our STU-Net models pre-trained on the large-scale dataset, TotalSegmentator, demonstrate enhanced performance on downstream tasks, markedly surpassing models trained from scratch.
</p>




## Dataset Links
We use TotalSegmentator dataset which contains 1204 images with 104 anatomical structures (consisting of 27 organs, 59 bones, 10 muscles and 8 vessels) for pre-training and 3 MICCAI 2022 challenge datasets as the downstream tasks for further fine-tuning.
### Pre-training
- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)
### Fine-tuning
- [FLARE22](https://flare22.grand-challenge.org/)
- [AMOS22](https://amos22.grand-challenge.org/Home/)
- [AutoPET22](https://autopet.grand-challenge.org/)


## Get Started
### Main Requirements
> torch==1.10  
> nnUNet==1.7.0  
> torchinfo
### Installation
Our models are built based on [nnUNet V1](https://github.com/MIC-DKFZ/nnUNet/tree/nnunetv1). Please ensure that you meet the requirements of nnUNet.
```
git clone https://github.com/Ziyan-Huang/STU-Net.git
cd nnUNet-1.7.1
pip install -e .
```
We now support [nnUNetv2](https://github.com/MIC-DKFZ/nnUNet)! You can install it using the following command.
```
git clone https://github.com/Ziyan-Huang/STU-Net.git
cd nnUNet-2.2
pip install -e .
```
If you have installed nnUNetv1 already. You can just copy the following files in this repo to your nnUNet repository.
```
copy /network_training/* nnunet/training/network_training/
copy /network_architecture/* nnunet/network_architecture/
copy run_finetuning.py nnunet/run/
```

### Pre-trained Models:
#### TotalSegmentator trained Models
These models are trained on TotalSegmentator dataset by 4000 epochs with mirror data augmentation

| Model Name | Crop Size | #Params | FLOPs | Download Link |
|:------:|:-------:|:-----:|:---------:| :-------|
| STU-Net-S | 128x128x128 | 14.6M | 0.13T | [Baidu Netdisk](https://pan.baidu.com/s/1ZBfOhaTvjvhcgXKGNe_gWg?pwd=soz7) \| [Google Drive](https://drive.google.com/file/d/1HReH6dDrEuXgHPrsw7OrHSjvEUF3f4mv/view?usp=sharing)|
| STU-Net-B | 128x128x128 | 58.26M | 0.51T | [Baidu Netdisk](https://pan.baidu.com/s/1a17XmOGiGSgbEvK-acSOSg?pwd=91w3) \| [Google Drive](https://drive.google.com/file/d/1BHCp1Ort-OaVFwaZmvsG4qHiKiPeNb4h/view?usp=share_link)|
| STU-Net-L | 128x128x128 | 440.30M | 3.81T | [Baidu Netdisk](https://pan.baidu.com/s/1WOLoTrzCLYyJXZnITGK6jg?pwd=91pt) \| [Google Drive](https://drive.google.com/file/d/1KA1eXWWf_xAoJg5KHYrxTmfiz7wxGhHS/view?usp=share_link)|
| STU-Net-H | 128x128x128 | 1457.33M | 12.60T | [Baidu Netdisk](https://pan.baidu.com/s/1CinTvceZuvdEEWGcaJEuEA?pwd=bk9n) \| [Google Drive](https://drive.google.com/file/d/1Qrq7oGPJ7ileFHWOAxwpeWdaB6hySptU/view?usp=share_link)|

#### Fine-tuning on downstream tasks
To perform fine-tuning on downstream tasks, use the following command with the base model as an example:
```
python run_finetuning.py 3d_fullres STUNetTrainer_base_ft TASKID FOLD -pretrained_weights MODEL
```
For fine-tuning nnUNetv2, you can execute the program using the following command.
```
python nnunetv2/run/run_finetuning_stunet.py Datasetxxx 3d_fullres FOLD -pretrained_weights MODEL -tr STUNetTrainer_base_ft 
```
If we wish to start training from scratch, we can use the following command.
```
python nnunetv2/run/run_training.py Datasetxxx 3d_fullres FOLD  -tr STUNetTrainer_base
```
If we wish to continue training from previously trained weights, run this command.
```
python nnunetv2/run/run_training.py Datasetxxx 3d_fullres FOLD  -tr STUNetTrainer_base --c
```
Please note that you may need to adjust the learning rate according to the specific downstream task. To do this, modify the learning rate in the corresponding Trainer (e.g., STUNetTrainer_base_ft) for the task.

### Using Our Models for Inference
To use our trained models to conduct inference on CT images, please first organize the file structures in your `RESULTS_FOLDER/nnUNet/3d_fullres/` as follows:
```
- Task101_TotalSegmentator/
  - STUNetTrainer_small__nnUNetPlansv2.1/
    - plans.pkl
    - fold_0/
      - small_ep4k.model
      - small_ep4k.model.pkl
  - STUNetTrainer_base__nnUNetPlansv2.1/
    - plans.pkl
    - fold_0/
      - base_ep4k.model
      - base_ep4k.model.pkl
  - STUNetTrainer_large__nnUNetPlansv2.1/
    - plans.pkl
    - fold_0/
      - large_ep4k.model
      - large_ep4k.model.pkl
  - STUNetTrainer_huge__nnUNetPlansv2.1/
    - plans.pkl
    - fold_0/
      - huge_ep4k.model
      - huge_ep4k.model.pkl
```
These pickle files can be found in the [plan_files](plan_files) directory within this repository. You can download the models from the provided paths above and set `TASKID` and `TASK_NAME` according to your preferences.

To conduct inference, you can use following command (base model for example):
```
nnUNet_predict -i INPUT_PATH -o OUTPUT_PATH -t 101 -m 3d_fullres -f 0 -tr STUNetTrainer_base  -chk base_ep4k
```
For much faster inference speed with minimal performance loss, it is recommended to use the following command:
```
nnUNet_predict -i INPUT_PATH -o OUTPUT_PATH -t 101 -m 3d_fullres -f 0 -tr STUNetTrainer_base  -chk base_ep4k --mode fast --disable_tta
```
The categories corresponding to the label values can be found in the [label_orders](label_orders.json) file within our repository (please note that this differs from the official TotalSegmentator version).

## 🙋‍♀️ Feedback and Contact
If you have any question, feel free to contact ziyanhuang@sjtu.edu.cn.

## 🛡️ License
This project is under the Apache License 2.0 license. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgement
Our code is based on the [nnU-Net](https://github.com/MIC-DKFZ/nnUNet) framework. 

## 📝 Citation
If you find this repository useful, please consider citing our paper:
```
@misc{huang2023stunet,
      title={STU-Net: Scalable and Transferable Medical Image Segmentation Models Empowered by Large-Scale Supervised Pre-training}, 
      author={Ziyan Huang and Haoyu Wang and Zhongying Deng and Jin Ye and Yanzhou Su and Hui Sun and Junjun He and Yun Gu and Lixu Gu and Shaoting Zhang and Yu Qiao},
      year={2023},
      eprint={2304.06716},
      archivePrefix={arXiv},
      primaryClass={cs.CV}
}
```
