import os
import errno
from pathlib import Path
import imageio
import numpy as np
import plotly.express as px
import pydicom


class DataReader:
    """
    class to read data from a given directory
    """

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.data_types = ["**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.npy", "**/*.dcm"]
        self.data_paths = self._read_data_paths()
        self.n_images = len(self.data_paths)
        self.current_img = None

    def _read_data_paths(self):
        """
        reads data paths to list
        ToDo: read list of datapaths and load images on the fly
        :return: list with absolute file_names
        """
        if not os.path.isdir(self.base_dir):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), self.base_dir)

        file_list = []
        for type_name in self.data_types:
            file_list += list(Path(self.base_dir).glob(type_name))
        
        print("##########Selected files##########################")
        print(file_list)

        return file_list

    def load_image(self, index: int):
        file_name = self.data_paths[index]
        file_ending = os.path.splitext(file_name)[1]
        if file_ending == ".npy":
            self.current_img = np.load(file_name)
        elif file_ending == ".dcm":
            dicom = pydicom.dcmread(file_name)
            self.current_img = dicom.pixel_array
        else:
            self.current_img = imageio.imread(file_name)

    def show_image(self, color_map='gray', norm_range=None):
        if norm_range is not None:
            data_np = self._range_norm(self.current_img.copy(), norm_range=norm_range)
        else:
            data_np = self.current_img
        fig = px.imshow(data_np, color_continuous_scale=color_map, zmin=data_np.min(), zmax=data_np.max())
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=False)
        fig.update_layout(coloraxis_showscale=False)
        return fig

    @staticmethod
    def _range_norm(data_np, norm_range):
        a1 = data_np.min()
        b1 = data_np.max()
        r1 = b1 - a1
        b2 = a1 + norm_range[1]*r1
        a2 = a1 + norm_range[0]*r1
        data_np[(data_np < a2) | (data_np > b2)] = 0  #crop range
        data_np = (data_np - data_np.min()) / (data_np.max() - data_np.min()) * (r1) + a1   #rescale to original scale
        return data_np

    def get_filename(self, selected_id):
        path = self.data_paths[selected_id]
        path = path.as_posix()
        return path
