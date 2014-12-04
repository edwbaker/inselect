from itertools import groupby
from operator import itemgetter

import cv2
import numpy as np

from PySide import QtGui

def qimage_of_bgr(bgr):
    """ A QtGui.QImage representation of a BGR numpy array
    """
    bgr = cv2.cvtColor(bgr.astype('uint8'), cv2.COLOR_BGR2RGB)
    bgr = np.ascontiguousarray(bgr)
    qt_image = QtGui.QImage(bgr.data,
                            bgr.shape[1], bgr.shape[0],
                            bgr.strides[0], QtGui.QImage.Format_RGB888)

    # QImage does not take a deep copy of np_arr.data so hold a reference
    # to it
    assert(not hasattr(qt_image, 'bgr_array'))
    qt_image.bgr_array = bgr
    return qt_image

def unite_rects(rects):
    """Returns united rect
    """
    # TODO LH There must be a more elegant way of doing this
    rect = rects[0]
    for other in rects[1:]:
        rect = rect.united(other)
    return rect

def get_corners(x1, y1, x2, y2):
    """Given two diagonally opposite corners of a box, return the top left and
    bottom right corners

    Parameters
    ----------
    x1 : float
    y1 : float
    x2 : float
    y2 : float

    Returns
    -------
    tuple
    """
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    return (x1, y1), (x2, y2)

def contiguous(values):
    """yields tuples (value, count) of contiguous blocks of integers in values

    >>> for value, count in contiguous([0, 15, 16, 17, 18, 22, 25, 26, 27, 28]):
        print(value, count)
    (0, 1)
    (15, 4)
    (22, 1)
    (25, 4)
    """
    # http://stackoverflow.com/questions/2361945/detecting-consecutive-integers-in-a-list
    for k, g in groupby(enumerate(values), lambda (i,x):i-x):
        g = list(g)
        lower, upper = g[0][1], g[-1][1]
        count = upper - lower + 1
        yield lower, count