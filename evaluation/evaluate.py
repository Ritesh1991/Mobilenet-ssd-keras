import sys
sys.path.append("/home/manish/MobileNet-ssd-keras")
import numpy as np 
from models.ssd_mobilenet import ssd_300
import cv2
import numpy as np
from keras.optimizers import Adam
from misc.keras_ssd_loss import SSDLoss
# from misc.
import os
import h5py
import keras
import time
from keras.preprocessing import image
from misc.ssd_box_encode_decode_utils import SSDBoxEncoder, decode_y, decode_y2
from misc.ssd_batch_generator import BatchGenerator
os.environ['CUDA_VISIBLE_DEVICES'] = "1"

def compute_overlap(a, b):
    """
    Code originally from https://github.com/rbgirshick/py-faster-rcnn.
    Parameters
    ----------
    a: (N, 4) ndarray of float
    b: (K, 4) ndarray of float
    Returns
    -------
    overlaps: (N, K) ndarray of overlap between boxes and query_boxes
    """
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])

    iw = np.minimum(np.expand_dims(a[:, 2], axis=1), b[:, 2]) - np.maximum(np.expand_dims(a[:, 0], 1), b[:, 0])
    ih = np.minimum(np.expand_dims(a[:, 3], axis=1), b[:, 3]) - np.maximum(np.expand_dims(a[:, 1], 1), b[:, 1])

    iw = np.maximum(iw, 0)
    ih = np.maximum(ih, 0)

    ua = np.expand_dims((a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]), axis=1) + area - iw * ih

    ua = np.maximum(ua, np.finfo(float).eps)

    intersection = iw * ih

    return intersection / ua


def compute_ap(recall, precision):
    """ Compute the average precision, given the recall and precision curves.
    Code originally from https://github.com/rbgirshick/py-faster-rcnn.

    # Arguments
        recall:    The recall curve (list).
        precision: The precision curve (list).
    # Returns
        The average precision as computed in py-faster-rcnn.
    """
    # correct AP calculation
    # first append sentinel values at the end
    mrec = np.concatenate(([0.], recall, [1.]))
    mpre = np.concatenate(([0.], precision, [0.]))

    # compute the precision envelope
    for i in range(mpre.size - 1, 0, -1):
        mpre[i - 1] = np.maximum(mpre[i - 1], mpre[i])

    # to calculate area under PR curve, look for points
    # where X axis (recall) changes value
    i = np.where(mrec[1:] != mrec[:-1])[0]

    # and sum (\Delta recall) * prec
    ap = np.sum((mrec[i + 1] - mrec[i]) * mpre[i + 1])
    return ap



img_height = 300  # Height of the input images
img_width = 300  # Width of the input images
img_channels = 3  # Number of color channels of the input images
subtract_mean = None  # The per-channel mean of the images in the dataset
subtract_mean = [127.5,127.5,127.5]
swap_channels = False  # The color channel order in the original SSD is BGR
n_classes = 20  # Number of positive classes, e.g. 20 for Pascal VOC, 80 for MS COCO
scales_voc = [0.1, 0.2, 0.37, 0.54, 0.71, 0.88,
              1.05]  # The anchor box scaling factors used in the original SSD300 for the Pascal VOC datasets
scales_coco = [0.07, 0.15, 0.33, 0.51, 0.69, 0.87,
               1.05]  # The anchor box scaling factors used in the original SSD300 for the MS COCO datasets
scales = [0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 1]
aspect_ratios = [[1.001, 2.0, 0.5],
                 [1.0, 2.0, 0.5, 3.0, 1.0 / 3.0],
                 [1.0, 2.0, 0.5, 3.0, 1.0 / 3.0],
                 [1.0, 2.0, 0.5, 3.0, 1.0 / 3.0],
                 [1.0, 2.0, 0.5, 3.0, 1.0 / 3.0],
                 [1.0, 2.0, 0.5, 3.0, 1.0 / 3.0]]  # The anchor box aspect ratios used in the original SSD300; the order matters
two_boxes_for_ar1 = True
steps = [16, 32, 64, 100, 150, 300]  # The space between two adjacent anchor box center points for each predictor layer.
offsets = [0.5, 0.5, 0.5, 0.5, 0.5,
           0.5]  # The offsets of the first anchor box center points from the top and left borders of the image as a fraction of the step size for each predictor layer.
limit_boxes = False  # Whether or not you want to limit the anchor boxes to lie entirely within the image boundaries
variances = [0.1, 0.1, 0.2,
             0.2]  # The variances by which the encoded target coordinates are scaled as in the original implementation
coords = 'centroids'  # Whether the box coordinates to be used as targets for the model should be in the 'centroids', 'corners', or 'minmax' format, see documentation
normalize_coords = True

# 1: Build the Keras model

# K.clear_session()  # Clear previous models from memory.

model = ssd_300("training",
                image_size=(img_height, img_width, img_channels),
                n_classes=n_classes,
                l2_regularization=0.0005,
                scales=scales,
                aspect_ratios_per_layer=aspect_ratios,
                two_boxes_for_ar1=two_boxes_for_ar1,
                steps=steps,
                offsets=offsets,
                limit_boxes=limit_boxes,
                variances=variances,
                coords=coords,
                normalize_coords=normalize_coords,
                subtract_mean=subtract_mean,
                divide_by_stddev=127.5,
                swap_channels=swap_channels)



for layer in model.layers:
    layer.name = layer.name + "_v1"


model.load_weights("/home/manish/MobileNet-ssd-keras/conversion/converted_model.h5")

dataset = BatchGenerator(box_output_format=['class_id', 'xmin', 'ymin', 'xmax', 'ymax'])

VOC_2007_images_dir = '/media/shareit/VOCdevkit/VOC2007/JPEGImages/'
VOC_2012_images_dir = '/media/shareit/VOCdevkit/VOC2012/JPEGImages/'

# The directories that contain the annotations.
VOC_2007_annotations_dir = '/media/shareit/VOCdevkit/VOC2007/Annotations/'
VOC_2012_annotations_dir = '/media/shareit/VOCdevkit/VOC2012/Annotations/'

# The paths to the image sets.
VOC_2007_train_image_set_filename = '/media/shareit/VOCdevkit/VOC2007/ImageSets/Main/trainval.txt'
VOC_2012_train_image_set_filename = '/media/shareit/VOCdevkit/VOC2012/ImageSets/Main/trainval.txt'

VOC_2007_val_image_set_filename = '/media/shareit/VOCdevkit/VOC2007/ImageSets/Main/test.txt'
# VOC_2012_val_image_set_filename = '/media/shareit/manish/blitznet-master/Datasets/VOCdevkit/VOC2012/ImageSets/Main/test.txt'


# The XML parser needs to now what object class names to look for and in which order to map them to integers.
classes = ['background',
           'aeroplane', 'bicycle', 'bird', 'boat',
           'bottle', 'bus', 'car', 'cat',
           'chair', 'cow', 'diningtable', 'dog',
           'horse', 'motorbike', 'person', 'pottedplant',
           'sheep', 'sofa', 'train', 'tvmonitor']


filenames, labels, image_ids = dataset.parse_xml(images_dirs=[VOC_2007_images_dir],
                                                 image_set_filenames=[VOC_2007_val_image_set_filename],
                                                 annotations_dirs=[VOC_2007_annotations_dir],
                                                 classes=classes,
                                                 include_classes='all',
                                                 exclude_truncated=False,
                                                 exclude_difficult=False,
                                                 ret=True)

size = len(filenames)
# size = 1000
# size = 1000

detected_labels = []


all_detections = [[None for i in range(21)] for j in range(size)]
all_annotations = [[None for i in range(21)] for j in range(size)]
# print all_detections
# print all_detections[0][20]

for i in range(size):

    image_path = filenames[i]
    # im.append(image_path)
    # print image_path
    ima = cv2.imread(image_path)
    print image_path
    # cv2.imshow('image',ima)
    # cv2.waitKey(0)
    # ima = cv2.cvtColor(ima, cv2.COLOR_BGR2RGB)
    orig_images = []

    orig_images.append(ima)

    image1 = cv2.resize(ima,(300,300))
    # image1 = np.array(image1,dtype=np.float32)

    # image1[:,:,0] = 0.007843*(image1[:,:,0] - 127.5)
    # image1[:,:,1] = 0.007843*(image1[:,:,1] - 127.5)
    # image1[:,:,2] = 0.007843*(image1[:,:,2] - 127.5)

    image1 = image1[np.newaxis,:,:,:]
    # input_images.append(image1)
    input_images = np.array(image1)


    start_time = time.time()
    y_pred = model.predict(input_images)
    print "time taken by ssd", time.time() - start_time


    # confidence_threshold = 0.01

    # y_pred_decoded = [y_pred[k][y_pred[k,:,1] > confidence_threshold] for k in range(y_pred.shape[0])]
    y_pred_decoded = decode_y(y_pred,
                              confidence_thresh=0.01,
                              iou_threshold=0.45,
                              top_k=100,
                              input_coords='centroids',
                              normalize_coords=True,
                              img_height=img_height,
                              img_width=img_width)

    pred_boxes = []
    pred_labels = []

    for box in y_pred_decoded[0]:
        # print 'box shape',box.shape

        # if(classes[int(box[0])] == 'I' or classes[int(box[0])] == 'O' or classes[int(box[0])] == 'IP' or classes[int(box[0])] == 'OP'):
        # Transform the predicted bounding boxes for the 300x300 image to the original image dimensions.
        xmin = int(box[-4] * orig_images[0].shape[1] / img_width)
        ymin = int(box[-3] * orig_images[0].shape[0] / img_height)
        xmax = int(box[-2] * orig_images[0].shape[1] / img_width)
        ymax = int(box[-1] * orig_images[0].shape[0] / img_height)
        class_id = int(box[0])
        score = box[1]

        pred_boxes.append([xmin, ymin, xmax, ymax, score])
        #print "class id ", class_id
        pred_labels.append(class_id)

    pred_boxes = np.array(pred_boxes)
    pred_labels = np.array(pred_labels)
    #
    # print pred_labels
    # print pred_boxes

    l = range(1, 20 + 1)
    for label in l:
        # print label
        if(len(pred_labels)):
            all_detections[i][label] = pred_boxes[pred_labels == label, :]

    true_label = np.array(labels[i])
    
    for label in l:
        if len(true_label) > 0:
            all_annotations[i][label] = true_label[true_label[:, 0] == label, 1:5].copy()
        else:
            all_annotations[i][label] = np.array([[]])

average_precisions = {}

# print all_detections[0]
# print all_detections[0][4][4]

for label in l:
    false_positives = np.zeros((0,))
    true_positives = np.zeros((0,))
    scores = np.zeros((0,))
    num_annotations = 0.0

    for i in range(size):
        annotations = all_annotations[i][label]
        annotations = annotations.astype(np.float32)

        # print 'annotations', annotations
        num_annotations += annotations.shape[0]
        detected_annotations = []
        detections = all_detections[i][label]
        if(detections is not None):
            detections = detections.astype(np.float32)
            # print detections

            # print 'detecions' ,detections

            for d in detections:
                # print d
                scores = np.append(scores, d[4])

                try:
                    annotations[0][0]
                except IndexError:
                    false_positives = np.append(false_positives, 1)
                    true_positives = np.append(true_positives, 0)
                    continue

                overlaps = compute_overlap(np.expand_dims(d, axis=0), annotations)

                # print 'overlaps', overlaps
                assigned_annotation = np.argmax(overlaps, axis=1)
                max_overlap = overlaps[0, assigned_annotation]
                # print 'max overlap', max_overlap

                if max_overlap >= 0.5 and assigned_annotation not in detected_annotations:
                    # print 'in if condition'
                    false_positives = np.append(false_positives, 0)
                    true_positives = np.append(true_positives, 1)
                    detected_annotations.append(assigned_annotation)
                else:
                    false_positives = np.append(false_positives, 1)
                    true_positives = np.append(true_positives, 0)

    # no annotations -> AP for this class is 0 (is this correct?)
    if num_annotations == 0:
        average_precisions[label] = 0
        continue

    # print true_positives
    # print false_positives.shape

    # sort by score
    indices = np.argsort(-scores)
    false_positives = false_positives[indices]
    true_positives = true_positives[indices]

    # compute false positives and true positives
    false_positives = np.cumsum(false_positives)
    true_positives = np.cumsum(true_positives)

    # print false_positives
    # print true_positives

    # compute recall and precision
    recall = true_positives / num_annotations
    # print 'recall for the boxes', recall

    precision = true_positives / np.maximum(true_positives + false_positives, np.finfo(np.float64).eps)

    # print 'precision for the boxes', precision

    # compute average precision
    average_precision = compute_ap(recall, precision)
    average_precisions[label] = average_precision

# print average_precisions

count = 0
for k in average_precisions.keys():
    count  = count + float(average_precisions[k])



map = count/len(l)


print average_precisions
print 'map is :' , map

