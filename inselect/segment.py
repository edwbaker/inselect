import cv2
import numpy as np


def right_sized(contour, image_size, size_filter=True):
    x, y, w, h = cv2.boundingRect(contour)
    area = image_size[0] * image_size[1]
    if w > h:
        ratio = float(w) / h
    else:
        ratio = float(h) / w

    # compares contour area to bounding rectangle area
    fill_ratio = cv2.contourArea(contour) / (w * h)
    # filter very long narrow objects and small objects
    is_right_shape = ratio < 8 and w * h > area / 8E3
    # filter to remove containers that are a) large and b) contains
    # too much or too little contour area in bounding box
    is_not_container = (0.1 < fill_ratio < 0.9 or
                       (w < image_size[1] * 0.35 and
                        h < image_size[0] * 0.35))
    is_too_large = (w > image_size[1] * 0.35 or h > image_size[0] * 0.35)

    return is_right_shape and is_not_container and \
        not (size_filter and is_too_large)


def process_contours(image, contours, hierarchy, index=0, size_filter=True):
    result = []
    while index >= 0:
        next, previous, child, parent = hierarchy[0][index]
        if right_sized(contours[index], image.shape, size_filter=size_filter):
            rect = cv2.boundingRect(contours[index])
            rect += (contours[index],)
            result.append(rect)
        else:
            if child != -1:
                rects = process_contours(image, contours, hierarchy, child,
                                         size_filter=size_filter)
                result.extend(rects)
        index = next
    return result


# alternate process, may be useful if we abandon hierarchical contours later
def _process_contours_iterate(image, contours, hierarchy, index=0,
                              size_filter=True):
    result = []
    for contour in contours:
        if right_sized(contour, image.shape, size_filter=size_filter):
            rect = cv2.boundingRect(contour)
            rect += (contour,)
            result.append(rect)
    return result


def remove_lines(image):
    """Removes long horizontal and vertical edges"""
    gray = cv2.cvtColor(image, cv2.cv.CV_BGR2GRAY)
    v_edges = cv2.Sobel(gray, cv2.CV_32F, 1, 0, None, 1)
    h_edges = cv2.Sobel(gray, cv2.CV_32F, 0, 1, None, 1)
    mag = np.abs(v_edges)
    mask = np.zeros(gray.shape, dtype=np.uint8)
    threshold = 20
    mag2 = (255*mag/np.max(mag)).astype(np.uint8)
    _, mag2 = cv2.threshold(mag2, threshold, 255, cv2.cv.CV_THRESH_BINARY)
    contours, hierarchy = cv2.findContours(mag2.copy(),
                                           cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        _, _, w, h = cv2.boundingRect(contour)
        if h > image.shape[0] / 4 and w < 50:
            cv2.drawContours(mask, [contour], -1, 255, -1)
    mag = np.abs(h_edges)
    mag2 = (255*mag/np.max(mag)).astype(np.uint8)
    _, mag2 = cv2.threshold(mag2, threshold, 255, cv2.cv.CV_THRESH_BINARY)
    contours, hierarchy = cv2.findContours(mag2.copy(),
                                           cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        _, _, w, h = cv2.boundingRect(contour)
        if w > image.shape[1] / 4 and h < 50:
            cv2.drawContours(mask, [contour], -1, 255, -1)
    return mask


def segment_edges(image, window=None, threshold=12, lab_based=True,
                  variance_threshold=None, size_filter=1, line_filter=1):
    """Segments an image based on edge intensities.

    Parameters
    ----------
    image : (M, N, 3) array
        Image to process.
    window : tuple, (x, y, w, h)
        Optional subwindow in image.
    lab_based: boolean
        Considers edges in the LAB colour space, else in the gray scale.
    variance_threshold : float
        Color variance limit for detected regions.
    size_filter: Boolean
        Reject large objects.
    line_filter: Boolean
        Remove long line segment edges.

    Returns
    -------
    (rects, display) : list, (M, N, 3) array
        Region results and visualization image.
    """
    if window:
        subimage = np.array(image)
        x, y, w, h = window
        image = subimage[y:y + h, x:x + w]

    gray = cv2.cvtColor(image, cv2.cv.CV_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 3)
    display = gray.copy()
    if not lab_based:
        v_edges = cv2.Sobel(gray, cv2.CV_32F, 1, 0, None, 1)
        h_edges = cv2.Sobel(gray, cv2.CV_32F, 0, 1, None, 1)
        mag = np.sqrt(v_edges ** 2 + h_edges ** 2)
        mag2 = (255*mag/np.max(mag)).astype(np.uint8)
        _, mag2 = cv2.threshold(mag2, threshold, 255, cv2.cv.CV_THRESH_BINARY)
    else:
        image2 = cv2.GaussianBlur(image, (3, 3), 3)
        lab_image = cv2.cvtColor(image2, cv2.cv.CV_BGR2Lab)
        # L component
        channel = np.array(lab_image[:, :, 0])
        v_edges = cv2.Sobel(channel, cv2.CV_32F, 1, 0, None, 1)
        h_edges = cv2.Sobel(channel, cv2.CV_32F, 0, 1, None, 1)
        mag = np.sqrt(v_edges ** 2 + h_edges ** 2)
        mag0 = (255*mag/np.max(mag)).astype(np.uint8)
        threshold = 10
        _, mag0 = cv2.threshold(mag0, threshold, 255, cv2.cv.CV_THRESH_BINARY)
        # B component
        channel = np.array(lab_image[:, :, 2])
        v_edges = cv2.Sobel(channel, cv2.CV_32F, 1, 0, None, 1)
        h_edges = cv2.Sobel(channel, cv2.CV_32F, 0, 1, None, 1)
        mag = np.sqrt(v_edges ** 2 + h_edges ** 2)
        mag2 = (255*mag/np.max(mag)).astype(np.uint8)
        threshold = 40
        _, mag2 = cv2.threshold(mag2, threshold, 255, cv2.cv.CV_THRESH_BINARY)
        mag2 = mag0 | mag2

    if line_filter:
        mask = remove_lines(image)
        mag2[mask == 255] = 0

    display = np.dstack((mag2, mag2, mag2))
    contours, hierarchy = cv2.findContours(mag2.copy(),
                                           cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_SIMPLE)

    rects = process_contours(display, contours, hierarchy,
                             size_filter=size_filter)
    if variance_threshold:
        new_rects = []
        for rect in rects:
            im = gray[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]]
            if np.var(im) > variance_threshold:
                new_rects.append(rect)
        rects = new_rects
    if window:
        new_rects = []
        for rect in rects:
            new_rect = (rect[0] + x, rect[1] + y, rect[2], rect[3])
            new_rects.append(new_rect)
        rects = new_rects

    return rects, display


def segment_intensity(image, window=None):
    if window:
        subimage = np.array(image)
        x, y, w, h = window
        image = subimage[y:y + h, x:x + w]
    mask = remove_lines(image)
    gray = cv2.cvtColor(image, cv2.cv.CV_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (25, 25), 9)
    (k, threshold) = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV |
                                   cv2.THRESH_OTSU)
    threshold[mask == 255] = 0
    contours, hierarchy = cv2.findContours(threshold.copy(),
                                           cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
    rects = [cv2.boundingRect(c) for c in contours]
    if window:
        new_rects = []
        for rect in rects:
            dx = rect[2] / 2
            dy = rect[3] / 2
            dx, dy = 0, 0
            new_rect = (rect[0] + x - dx, rect[1] + y - dy,
                        rect[2] + 2 * dx, rect[3] + 2 * dy)
            new_rects.append(new_rect)
        rects = new_rects
    display = np.dstack(3 * [threshold])
    return rects, display


def segment_grabcut(image, window=None):
    if window:
        subimage = np.array(image)
        x, y, w, h = window
        image = subimage[y:y + h, x:x + w]
    rects, display = segment_edges(image, variance_threshold=100,
                                   line_filter=0, size_filter=0)
    h, w = image.shape[:2]
    initial = np.zeros((h, w), np.uint8)
    initial[:] = cv2.GC_BGD
    for i, rect in enumerate(rects):
        cv2.drawContours(initial, [rect[4]], -1, 1, -1)

    initial[display[:, :, 0] > 0] = cv2.GC_PR_FGD
    bgmodel = np.zeros((1, 65), np.float64)
    fgmodel = np.zeros((1, 65), np.float64)
    mask = initial
    rect = None
    cv2.grabCut(image, mask, rect, bgmodel, fgmodel, 1, cv2.GC_INIT_WITH_MASK)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

    contours, hierarchy = cv2.findContours(mask2.copy(),
                                           cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
    rects = [cv2.boundingRect(c) for c in contours]

    if window:
        new_rects = []
        gray = cv2.cvtColor(image, cv2.cv.CV_BGR2GRAY)
        for rect in rects:
            dx, dy = 0, 0
            new_rect = (rect[0] + x - dx, rect[1] + y - dy,
                        rect[2] + 2 * dx, rect[3] + 2 * dy)

            im = gray[rect[1]:rect[1]+rect[3], rect[0]:rect[0]+rect[2]]
            if np.var(im) > 200 and rect[2] * rect[3] > w * h / 4E3:
                new_rects.append(new_rect)
        rects = new_rects
    display = np.dstack(3 * [255 * mask2.astype(np.uint8)])
    return rects, display


def segment_watershed(image, window=None):
    if window:
        subimage = np.array(image)
        x, y, w, h = window
        image = subimage[y:y + h, x:x + w]
    rects, display = segment_edges(image, variance_threshold=100,
                                   size_filter=0)
    h, w = image.shape[:2]
    initial = np.zeros((h, w), np.int32)
    for i, rect in enumerate(rects):
        cv2.drawContours(initial, [rect[4]], -1, 1, -1)
    display = np.zeros(initial.shape, dtype=np.uint8)

    segment_rects = []
    for i, rect in enumerate(rects):
        regions = np.zeros(initial.shape, dtype=np.uint8)
        cv2.drawContours(regions, [rect[4]], -1, 2, -1)
        regions = cv2.erode(regions, None)
        regions = cv2.erode(regions, None)
        markers = initial.copy()
        markers[regions == 2] = 2
        cv2.watershed(image, markers)
        display[markers == 2] = 255
        contours, hierarchy = cv2.findContours(regions.copy(),
                                               cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
        segment_rects.extend([cv2.boundingRect(c) for c in contours])

    if window:
        new_rects = []
        for rect in segment_rects:
            dx, dy = 0, 0
            new_rect = (rect[0] + x - dx, rect[1] + y - dy,
                        rect[2] + 2 * dx, rect[3] + 2 * dy)
            new_rects.append(new_rect)
        segment_rects = new_rects
    return segment_rects, np.dstack(3 * [display])


if __name__ == "__main__":
    image = cv2.imread("../data/drawer.jpg")
    scaled = 1.0
    image = cv2.resize(image, (int(image.shape[1] * scaled),
                               int(image.shape[0] * scaled)))
    rects, display = segment_grabcut(image)
    display = np.array(display[:, :, 0])
    display = cv2.distanceTransform(display, cv2.cv.CV_DIST_L2, 5)
    cv2.imshow("disp", (display).astype(np.uint8))
    while cv2.waitKey(0) != 27:
        pass
