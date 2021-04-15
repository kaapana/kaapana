import torchvision
from PIL import Image
from torchvision import transforms


def provide_dataset_transforms(dataset: str):

    transform_dict = None

    if dataset == 'mnist':
        transform_dict = {
            'train': transforms.Compose([
                transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
                transforms.ToTensor(),
                transforms.Normalize((0.1307,), (0.3081,))
                ]),
            'test': transforms.Compose([
                transforms.Grayscale(num_output_channels=1), # <-- needed since imgs are loaded with 3 channels by default
                transforms.ToTensor(),
                transforms.Normalize((0.1307,), (0.3081,))
                ])}
    
    elif dataset == 'xray':
        transform_dict = {
            'train': transforms.Compose([
                transforms.Resize((256,256), interpolation=Image.NEAREST),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
            ]),
            'test': transforms.Compose([
                transforms.Resize((256,256), interpolation=Image.NEAREST),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
            ]),
        }

    else:
        print('ERROR - dataset specific Transforms not implemented yet')
    
    return transform_dict
