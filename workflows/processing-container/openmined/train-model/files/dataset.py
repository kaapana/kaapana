from torch.utils.data import Dataset

class OpenminedDataset(Dataset):
    '''Openmined Dataset using pointers to remote data instances'''
    
    def __init__(self, img_ptr, label_ptr):
        ''' '''
        self.img_ptr = img_ptr
        self.label_ptr = label_ptr
        self.transform = None
    
    def __len__(self):
        return len(self.img_ptr)

    def __getitem__(self, idx):
        '''Return image and corresponding label'''
        img_ptr = self.img_ptr[idx]
        label_ptr = self.label_ptr[idx]
        
        return img_ptr, label_ptr
