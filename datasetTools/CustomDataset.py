"""
Skinet (Segmentation of the Kidney through a Neural nETwork) Project
Dataset tools

Copyright (c) 2021 Skinet Team
Licensed under the MIT License (see LICENSE for details)
Written by Adrien JAUGEY
"""
import os
import numpy as np
from skimage.io import imread

from datasetTools.datasetWrapper import getBboxFromName
from mrcnn import utils
from mrcnn.Config import Config


class CustomDataset(utils.Dataset):

    def __init__(self, dataset_id, image_info, config: Config, previous_mode=False, enable_occlusion=False):
        super().__init__()
        self.__ID = dataset_id
        self.__CONFIG = config
        self.__CUSTOM_CLASS_NAMES = [c['name'] for c in config.get_classes_info("previous" if previous_mode else None)]
        self.__IMAGE_INFO = image_info
        self.__ENABLE_OCCLUSION = enable_occlusion

    def get_class_names(self):
        return self.__CUSTOM_CLASS_NAMES.copy()

    def get_visualize_names(self):
        visualize_names = ['background']
        visualize_names.extend(self.__CUSTOM_CLASS_NAMES)
        return visualize_names

    def load_images(self):
        # Add classes
        for class_id, class_name in enumerate(self.__CUSTOM_CLASS_NAMES):
            self.add_class(self.__ID, class_id + 1, class_name)
        image_name = self.__IMAGE_INFO["NAME"]
        img_path = os.path.join('data', image_name, "images",
                                f"{image_name}.{self.__IMAGE_INFO['IMAGE_FORMAT']}")
        self.add_image(self.__ID, image_id=self.__IMAGE_INFO["NAME"], path=img_path)

    def image_reference(self, image_id_):
        """ Return the data of the image. """
        info = self.image_info[image_id_]
        if info["source"] == self.__ID:
            return info[self.__ID]
        else:
            super(self.__class__).image_reference(self, image_id_)

    def load_mask(self, image_id_):
        """ Generate instance masks for cells of the given image ID. """
        info = self.image_info[image_id_]
        info = info.get("id")

        path = os.path.join('data', info)

        # Counting masks for current image
        number_of_masks = 0
        masks_dir_list = [p for p in os.listdir(path) if p in self.__CUSTOM_CLASS_NAMES]
        for masks_dir in masks_dir_list:
            temp_DIR = os.path.join(path, masks_dir)
            # https://stackoverflow.com/a/2632251/9962046
            number_of_masks += len([name_ for name_ in os.listdir(temp_DIR)
                                    if os.path.isfile(os.path.join(temp_DIR, name_))])
        if self.__CONFIG.get_param().get('resize', None) is not None:
            masks_shape = tuple(self.__CONFIG.get_param().get('resize', None)) + (number_of_masks,)
        elif self.__CONFIG.is_using_mini_mask():
            masks_shape = self.__CONFIG.get_mini_mask_shape() + (number_of_masks,)
        else:
            masks_shape = (self.__IMAGE_INFO["HEIGHT"], self.__IMAGE_INFO["WIDTH"], number_of_masks)
        masks = np.zeros(masks_shape, dtype=np.uint8)
        bboxes = np.zeros((number_of_masks, 4), dtype=np.int32)
        iterator = 0
        class_ids = np.zeros((number_of_masks,), dtype=int)
        for masks_dir in masks_dir_list:
            temp_class_id = self.__CUSTOM_CLASS_NAMES.index(masks_dir) + 1
            masks_dir_path = os.path.join(path, masks_dir)
            for mask_file in os.listdir(masks_dir_path):
                mask = imread(os.path.join(masks_dir_path, mask_file))
                mask = np.where(mask > 220, 255, 0).astype(np.uint8)
                masks[:, :, iterator] = mask
                if self.__CONFIG.is_using_mini_mask():
                    bboxes[iterator] = getBboxFromName(mask_file)
                else:
                    bboxes[iterator] = utils.extract_bboxes(mask)
                class_ids[iterator] = temp_class_id
                iterator += 1
        # Handle occlusions /!\ In our case there is no possible occlusion (part of object that
        # is hidden), all objects are complete (some are parts of other)
        if self.__ENABLE_OCCLUSION:
            occlusion = np.logical_not(masks[:, :, -1]).astype(np.uint8)
            for i in range(number_of_masks - 2, -1, -1):
                masks[:, :, i] = masks[:, :, i] * occlusion
                occlusion = np.logical_and(occlusion, np.logical_not(masks[:, :, i]))
        return masks, class_ids.astype(np.int32), bboxes
