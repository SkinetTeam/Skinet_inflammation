"""
Mask R-CNN
Display and Visualization Functions.

Copyright (c) 2017 Matterport, Inc.
Licensed under the MIT License (see LICENSE_MATTERPORT for details)
Written by Waleed Abdulla

Copyright (c) 2021 Skinet Team
Licensed under the MIT License (see LICENSE for details)
Updated/Modified by Adrien JAUGEY
"""

import os
import sys
import random
import itertools
import colorsys
import cv2

import numpy as np
from skimage.measure import find_contours
import matplotlib.pyplot as plt
from matplotlib import patches, lines
from matplotlib.patches import Polygon
import IPython.display

# Root directory of the project
from common_utils import format_number
from datasetTools.datasetDivider import CV2_IMWRITE_PARAM
from mrcnn.Config import Config

ROOT_DIR = os.path.abspath("../../")

# Import Mask RCNN
sys.path.append(ROOT_DIR)  # To find local version of the library
from mrcnn import utils


############################################################
#  Visualization
############################################################

def display_images(images, titles=None, cols=4, cmap=None, norm=None,
                   interpolation=None):
    """Display the given set of images, optionally with titles.
    images: list or array of image tensors in HWC format.
    titles: optional. A list of titles to display with each image.
    cols: number of images per row
    cmap: Optional. Color map to use. For example, "Blues".
    norm: Optional. A Normalize instance to map values to colors.
    interpolation: Optional. Image interpolation to use for display.
    """
    titles = titles if titles is not None else [""] * len(images)
    rows = len(images) // cols + 1
    plt.figure(figsize=(14, 14 * rows // cols))
    i = 1
    for image, title in zip(images, titles):
        plt.subplot(rows, cols, i)
        plt.title(title, fontsize=9)
        plt.axis('off')
        plt.imshow(image.astype(np.uint8), cmap=cmap,
                   norm=norm, interpolation=interpolation)
        i += 1
    plt.show()


def random_colors(N, bright=True, shuffle=True):
    """
    Generate random colors.
    To get visually distinct colors, generate them in HSV space then
    convert to RGB.
    """
    brightness = 1.0 if bright else 0.7
    hsv = [(i / N, 1, brightness) for i in range(N)]
    colors = list(map(lambda c: colorsys.hsv_to_rgb(*c), hsv))
    if shuffle:
        random.shuffle(colors)
    return colors


def apply_mask(image, mask, color, alpha=0.5, bbox=None):
    """Apply the given mask to the image.
    """
    # Define bbox as whole image if not given
    if bbox is None:
        y1, x1, y2, x2 = 0, 0, image.shape[0], image.shape[1]
    else:
        y1, x1, y2, x2 = bbox

    # Take only mask part if not already
    if (y2 - y1) != mask.shape[0] or (x2 - x1) != mask.shape[1]:
        _mask = mask[y1:y2, x1:x2]
    else:
        _mask = mask

    if type(color) in [tuple, list] and len(image.shape) > 2:
        # Color conversion if given in percentage instead of raw value
        if type(color[0]) is float:
            _color = [round(channelColor * 255) for channelColor in color]
        else:
            _color = color

        # Apply mask on each channel
        for channel in range(3):
            image[y1:y2, x1:x2, channel] = np.where(
                _mask > 0,
                (image[y1:y2, x1:x2, channel].astype(np.uint32) * (1 - alpha) + alpha * _color[channel]).astype(
                    np.uint8),
                image[y1:y2, x1:x2, channel]
            )
    elif type(color) in [int, float] and len(image.shape) == 2:
        # Color conversion if given in percentage instead of raw value
        _color = (color * 255) if type(color) is float else color

        image[y1:y2, x1:x2] = np.where(
            _mask > 0,
            (image[y1:y2, x1:x2].astype(np.uint32) * (1 - alpha) + alpha * _color).astype(np.uint8),
            image[y1:y2, x1:x2]
        )
    return image


def get_text_color_by_colormap(val, maxVal, colormap, light_threshold=0.5):
    """
    Return black or white text color for confusion matrix depending on the colormap and value given
    :param val: the current value
    :param maxVal: max value in the confusion matrix
    :param colormap: the colormap that is used to color the confusion matrix
    :param light_threshold: the threshold used to determine whether or not a color is dark or light
    :return: "k" if background color is light else "w"
    """
    # Based on https://css-tricks.com/switch-font-color-for-different-backgrounds-with-css/
    # TODO: Add support to minVal != 0
    index = int(round((val / maxVal) * 256))
    red, green, blue, _ = colormap(index)
    return get_text_color(red, green, blue, light_threshold)


def get_text_color(r, g, b, light_threshold=0.5):
    """
    Return black or white text color depending on the background color
    :param r: amount of red color
    :param g: amount of green color
    :param b: amount of blue color
    :param light_threshold: the threshold used to determine whether or not a color is dark or light
    :return: "k" if background color is light else "w"
    """
    _, light, _ = colorsys.rgb_to_hls(r, g, b)
    return "k" if light >= light_threshold else "w"


def display_confusion_matrix(confusion_matrix, class_names, title="Confusion Matrix", normalize=False,
                             cmap=plt.get_cmap('gray'), show=True, fileName=None):
    """
    Display confusion matrix and can also save it to an image file
    :param confusion_matrix: the raw confusion matrix as a 2-D array
    :param class_names: list of the class names in the same order as for the dataset
    :param title: [optional] custom title of the figure
    :param normalize: [optional] whether or not the confusion matrix should be normalized
    :param cmap: [optional] custom colormap for the display
    :param show: [optional] whether or not plot should be shown
    :param fileName: [optional] name of the file to be saved, if not given, figure will not be saved as file
    :return: None
    """
    matrix = np.copy(confusion_matrix)
    NB_CLASS = len(class_names)

    # plt.plot()
    fig, ax = plt.subplots(figsize=(9, 6.75), frameon=False)
    ax.set_title(title)

    if normalize:
        matrix = matrix.astype(np.float)
        for i in range(len(matrix)):
            somme = 0.0
            for j in range(len(matrix[0])):
                somme += matrix[i][j]
            if somme != 0:
                for j in range(len(matrix[0])):
                    matrix[i][j] = matrix[i][j] / somme

    # Displaying the confusion matrix as a gray image scaled with min/max values
    minVal = np.amin(matrix)
    maxVal = np.amax(matrix)
    ax.imshow(matrix, cmap=cmap, vmin=minVal, vmax=maxVal)

    # Using class names as labels of both axis
    plt.xlabel("Predicted")
    ax.set_xticks(np.arange(NB_CLASS))
    ax.set_xticklabels(class_names)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    plt.ylabel("Ground Truth")
    ax.set_yticks(np.arange(NB_CLASS))
    ax.set_yticklabels(class_names)

    # Adding the text values above the image
    for i in range(NB_CLASS):
        for j in range(NB_CLASS):
            if matrix[i][j] >= 0.005:
                color = get_text_color_by_colormap(matrix[i][j], maxVal, cmap)
                if normalize:
                    text = f"{round(matrix[i][j], 2):0.2f}"
                else:
                    text = format_number(matrix[i][j], maxLength=4)
                ax.text(j, i, text, ha="center", va="center", color=color)
    # Auto resize of dimension
    fig.tight_layout()
    # Saving the figure if fileName given
    if fileName is not None:
        fig.savefig(fileName + ".png")
    if show:
        plt.show()
    fig.clf()
    del ax, fig


def create_multiclass_mask(image_shape, results: dict, config: Config = None):
    """
    Creates an image containing all the masks where pixel color is the mask's class ID
    :param image_shape: the shape of the initial image
    :param results: the results dictionary containing all the masks
    :param config: the config object used to expand mini_masks if enabled
    :return: the multi-mask image
    """
    res = np.zeros((image_shape[0], image_shape[1]), np.uint8)

    masks = results['masks']
    class_ids = results['class_ids']
    rois = results['rois']
    indices = np.arange(len(class_ids))

    classes_hierarchy = config.get_classes_hierarchy()
    if classes_hierarchy is None:
        levels = [[i + 1 for i in range(len(config.get_classes_info()))]]
    else:
        levels = utils.remove_redundant_classes(utils.classes_level(classes_hierarchy), keepFirst=False)

    for lvl in levels:
        current_indices = indices[np.isin(class_ids, lvl)]
        for idx in current_indices:
            mask = masks[:, :, idx].astype(bool).astype(np.uint8) * 255
            roi = rois[idx]
            classID = int(class_ids[idx])
            if config is not None and config.is_using_mini_mask():
                shifted_bbox = utils.shift_bbox(roi)
                mask = utils.expand_mask(shifted_bbox, mask, shifted_bbox[2:])
            res = apply_mask(res, mask, classID, 1, roi)
    return res


def display_instances(image, boxes, masks, class_ids, class_names,
                      scores=None, title="",
                      figsize=(16, 16), ax=None, fig=None, image_format="jpg",
                      show_mask=True, show_bbox=True,
                      colors=None, colorPerClass=False, captions=None,
                      fileName=None, save_cleaned_img=False, silent=False, config: Config = None):
    """
    boxes: [num_instance, (y1, x1, y2, x2, class_id)] in image coordinates.
    masks: [height, width, num_instances]
    class_ids: [num_instances]
    class_names: list of class names of the dataset
    scores: (optional) confidence scores for each box
    title: (optional) Figure title
    show_mask, show_bbox: To show masks and bounding boxes or not
    figsize: (optional) the size of the image
    colors: (optional) An array or colors to use with each object
    captions: (optional) A list of strings to use as captions for each object
    """
    # Number of instances
    N = boxes.shape[0]
    if not N:
        print("\n*** No instances to display *** \n")
    else:
        assert boxes.shape[0] == masks.shape[-1] == class_ids.shape[0]

    # If no axis is passed, create one and automatically call show()
    auto_show = False
    ownFig = False
    if ax is None or fig is None:
        ownFig = True
        fig, ax = plt.subplots(1, figsize=figsize)
        auto_show = not silent

    # Generate random colors
    nb_color = (len(class_names) - 1) if colorPerClass else N
    colors = colors if colors is not None else random_colors(nb_color, shuffle=(not colorPerClass))
    if type(colors[0][0]) is int:
        _colors = []
        for color in colors:
            _colors.append([c / 255. for c in color])
    else:
        _colors = colors
    # Show area outside image boundaries.
    height, width = image.shape[:2]
    ax.set_ylim(height + 10, -10)
    ax.set_xlim(-10, width + 10)
    ax.axis('off')
    ax.set_title(title)

    # To be usable on Google Colab we do not make a copy of the image leading to too much ram usage if it is a biopsy
    # or nephrectomy image
    masked_image = image
    # masked_image = image.astype(np.uint32).copy()
    for i in range(N):
        if colorPerClass:
            color = _colors[class_ids[i] - 1]
        else:
            color = _colors[i]
        # Bounding box
        if not np.any(boxes[i]):
            # Skip this instance. Has no bbox. Likely lost in image cropping.
            continue
        y1, x1, y2, x2 = boxes[i]
        if show_bbox:
            p = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2,
                                  alpha=0.7, linestyle="dashed",
                                  edgecolor=color, facecolor='none')
            ax.add_patch(p)

        # Label
        if not captions:
            class_id = class_ids[i]
            score = scores[i] if scores is not None else None
            label = class_names[class_id]
            caption = "{} {:.3f}".format(label, score) if score else label
        else:
            caption = captions[i]
        ax.text(x1 + 4, y1 + 19, caption, color=get_text_color(color[0], color[1], color[2]),
                size=12, backgroundcolor=color)

        # Mask
        mask = masks[:, :, i]
        bbox = boxes[i]
        shift = np.array([0, 0])
        if config is not None and config.is_using_mini_mask():
            shifted_bbox = utils.shift_bbox(bbox)
            shift = bbox[:2]
            mask = utils.expand_mask(shifted_bbox, mask, tuple(shifted_bbox[2:]))
            mask = mask.astype(np.uint8) * 255
        if show_mask:
            masked_image = apply_mask(masked_image, mask, color, bbox=bbox)

        # Mask Polygon
        # Pad to ensure proper polygons for masks that touch image edges.
        padded_mask = np.zeros(
            (mask.shape[0] + 2, mask.shape[1] + 2), dtype=np.uint8)
        padded_mask[1:-1, 1:-1] = mask
        contours = find_contours(padded_mask, 0.5)
        for verts in contours:
            verts = verts + shift
            # Subtract the padding and flip (y, x) to (x, y)
            verts = np.fliplr(verts) - 1
            p = Polygon(verts, facecolor="none", edgecolor=color)
            ax.add_patch(p)
    # masked_image = masked_image.astype(np.uint8)
    ax.imshow(masked_image)
    fig.tight_layout()
    if fileName is not None:
        fig.savefig(f"{fileName}.{image_format}")
        if save_cleaned_img:
            BGR_img = cv2.cvtColor(masked_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(f"{fileName}_clean.{image_format}", BGR_img, CV2_IMWRITE_PARAM)
    if auto_show:
        plt.show()
    fig.clf()
    if ownFig:
        del ax, fig
    return masked_image


def display_differences(image,
                        gt_box, gt_class_id, gt_mask,
                        pred_box, pred_class_id, pred_score, pred_mask,
                        class_names, title="", ax=None,
                        show_mask=True, show_box=True,
                        iou_threshold=0.5, score_threshold=0.5):
    """Display ground truth and prediction instances on the same image."""
    # Match predictions to ground truth
    gt_match, pred_match, overlaps, _ = utils.compute_matches(
        gt_box, gt_class_id, gt_mask,
        pred_box, pred_class_id, pred_score, pred_mask,
        ap_iou_threshold=iou_threshold, min_iou_to_count=score_threshold)
    # Ground truth = green. Predictions = red
    colors = [(0, 1, 0, .8)] * len(gt_match) \
             + [(1, 0, 0, 1)] * len(pred_match)
    # Concatenate GT and predictions
    class_ids = np.concatenate([gt_class_id, pred_class_id])
    scores = np.concatenate([np.zeros([len(gt_match)]), pred_score])
    boxes = np.concatenate([gt_box, pred_box])
    masks = np.concatenate([gt_mask, pred_mask], axis=-1)
    # Captions per instance show score/IoU
    captions = ["" for m in gt_match] + ["{:.2f} / {:.2f}".format(
        pred_score[i],
        (overlaps[i, int(pred_match[i])]
         if pred_match[i] > -1 else overlaps[i].max()))
        for i in range(len(pred_match))]
    # Set title if not provided
    title = title or "Ground Truth and Detections\n GT=green, pred=red, captions: score/IoU"
    # Display
    display_instances(
        image,
        boxes, masks, class_ids,
        class_names, scores, ax=ax,
        show_bbox=show_box, show_mask=show_mask,
        colors=colors, captions=captions,
        title=title)


def draw_rois(image, rois, refined_rois, mask, class_ids, class_names, limit=10):
    """
    anchors: [n, (y1, x1, y2, x2)] list of anchors in image coordinates.
    proposals: [n, 4] the same anchors but refined to fit objects better.
    """
    masked_image = image.copy()

    # Pick random anchors in case there are too many.
    ids = np.arange(rois.shape[0], dtype=np.int32)
    ids = np.random.choice(
        ids, limit, replace=False) if ids.shape[0] > limit else ids

    fig, ax = plt.subplots(1, figsize=(12, 12))
    if rois.shape[0] > limit:
        plt.title("Showing {} random ROIs out of {}".format(
            len(ids), rois.shape[0]))
    else:
        plt.title("{} ROIs".format(len(ids)))

    # Show area outside image boundaries.
    ax.set_ylim(image.shape[0] + 20, -20)
    ax.set_xlim(-50, image.shape[1] + 20)
    ax.axis('off')

    for i, id in enumerate(ids):
        color = np.random.rand(3)
        class_id = class_ids[id]
        # ROI
        y1, x1, y2, x2 = rois[id]
        p = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2,
                              edgecolor=color if class_id else "gray",
                              facecolor='none', linestyle="dashed")
        ax.add_patch(p)
        # Refined ROI
        if class_id:
            ry1, rx1, ry2, rx2 = refined_rois[id]
            p = patches.Rectangle((rx1, ry1), rx2 - rx1, ry2 - ry1, linewidth=2,
                                  edgecolor=color, facecolor='none')
            ax.add_patch(p)
            # Connect the top-left corners of the anchor and proposal for easy visualization
            ax.add_line(lines.Line2D([x1, rx1], [y1, ry1], color=color))

            # Label
            label = class_names[class_id]
            ax.text(rx1, ry1 + 8, "{}".format(label),
                    color='w', size=11, backgroundcolor="none")

            # Mask
            m = utils.unmold_mask(mask[id], rois[id]
            [:4].astype(np.int32), image.shape)
            masked_image = apply_mask(masked_image, m, color)

    ax.imshow(masked_image)

    # Print stats
    print("Positive ROIs: ", class_ids[class_ids > 0].shape[0])
    print("Negative ROIs: ", class_ids[class_ids == 0].shape[0])
    print("Positive Ratio: {:.2f}".format(
        class_ids[class_ids > 0].shape[0] / class_ids.shape[0]))


# TODO: Replace with matplotlib equivalent?
def draw_box(image, box, color):
    """Draw 3-pixel width bounding boxes on the given image array.
    color: list of 3 int values for RGB.
    """
    y1, x1, y2, x2 = box
    image[y1:y1 + 2, x1:x2] = color
    image[y2:y2 + 2, x1:x2] = color
    image[y1:y2, x1:x1 + 2] = color
    image[y1:y2, x2:x2 + 2] = color
    return image


def display_top_masks(image, mask, class_ids, class_names, limit=4):
    """Display the given image and the top few class masks."""
    to_display = []
    titles = []
    to_display.append(image)
    titles.append("H x W={}x{}".format(image.shape[0], image.shape[1]))
    # Pick top prominent classes in this image
    unique_class_ids = np.unique(class_ids)
    mask_area = [np.sum(mask[:, :, np.where(class_ids == i)[0]])
                 for i in unique_class_ids]
    top_ids = [v[0] for v in sorted(zip(unique_class_ids, mask_area),
                                    key=lambda r: r[1], reverse=True) if v[1] > 0]
    # Generate images and titles
    for i in range(limit):
        class_id = top_ids[i] if i < len(top_ids) else -1
        # Pull masks of instances belonging to the same class.
        m = mask[:, :, np.where(class_ids == class_id)[0]]
        m = np.sum(m * np.arange(1, m.shape[-1] + 1), -1)
        to_display.append(m)
        titles.append(class_names[class_id] if class_id != -1 else "-")
    display_images(to_display, titles=titles, cols=limit + 1, cmap="Blues_r")


def plot_precision_recall(AP, precisions, recalls):
    """Draw the precision-recall curve.

    AP: Average precision at IoU >= 0.5
    precisions: list of precision values
    recalls: list of recall values
    """
    # Plot the Precision-Recall curve
    _, ax = plt.subplots(1)
    ax.set_title("Precision-Recall Curve. AP@50 = {:.3f}".format(AP))
    ax.set_ylim(0, 1.1)
    ax.set_xlim(0, 1.1)
    _ = ax.plot(recalls, precisions)


def draw_boxes(image, boxes=None, refined_boxes=None,
               masks=None, captions=None, visibilities=None,
               title="", ax=None):
    """Draw bounding boxes and segmentation masks with different
    customizations.

    boxes: [N, (y1, x1, y2, x2, class_id)] in image coordinates.
    refined_boxes: Like boxes, but draw with solid lines to show
        that they're the result of refining 'boxes'.
    masks: [N, height, width]
    captions: List of N titles to display on each box
    visibilities: (optional) List of values of 0, 1, or 2. Determine how
        prominent each bounding box should be.
    title: An optional title to show over the image
    ax: (optional) Matplotlib axis to draw on.
    """
    # Number of boxes
    assert boxes is not None or refined_boxes is not None
    N = boxes.shape[0] if boxes is not None else refined_boxes.shape[0]

    # Matplotlib Axis
    if not ax:
        _, ax = plt.subplots(1, figsize=(12, 12))

    # Generate random colors
    colors = random_colors(N)

    # Show area outside image boundaries.
    margin = image.shape[0] // 10
    ax.set_ylim(image.shape[0] + margin, -margin)
    ax.set_xlim(-margin, image.shape[1] + margin)
    ax.axis('off')

    ax.set_title(title)

    masked_image = image.astype(np.uint32).copy()
    for i in range(N):
        # Box visibility
        visibility = visibilities[i] if visibilities is not None else 1
        if visibility == 0:
            color = "gray"
            style = "dotted"
            alpha = 0.5
        elif visibility == 1:
            color = colors[i]
            style = "dotted"
            alpha = 1
        elif visibility == 2:
            color = colors[i]
            style = "solid"
            alpha = 1

        # Boxes
        if boxes is not None:
            if not np.any(boxes[i]):
                # Skip this instance. Has no bbox. Likely lost in cropping.
                continue
            y1, x1, y2, x2 = boxes[i]
            p = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2,
                                  alpha=alpha, linestyle=style,
                                  edgecolor=color, facecolor='none')
            ax.add_patch(p)

        # Refined boxes
        if refined_boxes is not None and visibility > 0:
            ry1, rx1, ry2, rx2 = refined_boxes[i].astype(np.int32)
            p = patches.Rectangle((rx1, ry1), rx2 - rx1, ry2 - ry1, linewidth=2,
                                  edgecolor=color, facecolor='none')
            ax.add_patch(p)
            # Connect the top-left corners of the anchor and proposal
            if boxes is not None:
                ax.add_line(lines.Line2D([x1, rx1], [y1, ry1], color=color))

        # Captions
        if captions is not None:
            caption = captions[i]
            # If there are refined boxes, display captions on them
            if refined_boxes is not None:
                y1, x1, y2, x2 = ry1, rx1, ry2, rx2
            ax.text(x1, y1, caption, size=11, verticalalignment='top',
                    color='w', backgroundcolor="none",
                    bbox={'facecolor': color, 'alpha': 0.5,
                          'pad': 2, 'edgecolor': 'none'})

        # Masks
        if masks is not None:
            mask = masks[:, :, i]
            masked_image = apply_mask(masked_image, mask, color)
            # Mask Polygon
            # Pad to ensure proper polygons for masks that touch image edges.
            padded_mask = np.zeros(
                (mask.shape[0] + 2, mask.shape[1] + 2), dtype=np.uint8)
            padded_mask[1:-1, 1:-1] = mask
            contours = find_contours(padded_mask, 0.5)
            for verts in contours:
                # Subtract the padding and flip (y, x) to (x, y)
                verts = np.fliplr(verts) - 1
                p = Polygon(verts, facecolor="none", edgecolor=color)
                ax.add_patch(p)
    ax.imshow(masked_image.astype(np.uint8))


def display_table(table):
    """Display values in a table format.
    table: an iterable of rows, and each row is an iterable of values.
    """
    html = ""
    for row in table:
        row_html = ""
        for col in row:
            row_html += "<td>{:40}</td>".format(str(col))
        html += "<tr>" + row_html + "</tr>"
    html = "<table>" + html + "</table>"
    IPython.display.display(IPython.display.HTML(html))


def display_weight_stats(model):
    """Scans all the weights in the model and returns a list of tuples
    that contain stats about each weight.
    """
    layers = model.get_trainable_layers()
    table = [["WEIGHT NAME", "SHAPE", "MIN", "MAX", "STD"]]
    for l in layers:
        weight_values = l.get_weights()  # list of Numpy arrays
        weight_tensors = l.weights  # list of TF tensors
        for i, w in enumerate(weight_values):
            weight_name = weight_tensors[i].name
            # Detect problematic layers. Exclude biases of conv layers.
            alert = ""
            if w.min() == w.max() and not (l.__class__.__name__ == "Conv2D" and i == 1):
                alert += "<span style='color:red'>*** dead?</span>"
            if np.abs(w.min()) > 1000 or np.abs(w.max()) > 1000:
                alert += "<span style='color:red'>*** Overflow?</span>"
            # Add row
            table.append([
                weight_name + alert,
                str(w.shape),
                "{:+9.4f}".format(w.min()),
                "{:+10.4f}".format(w.max()),
                "{:+9.4f}".format(w.std()),
            ])
    display_table(table)
