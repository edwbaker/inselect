# -*- coding: UTF-8 -*-
import os
import pytz
import sys
import tempfile
import unittest

from datetime import datetime
from itertools import izip
from pathlib import Path

import numpy as np

from inselect.lib.document import InselectDocument
from inselect.lib.inselect_error import InselectError
from inselect.lib.rect import Rect
from inselect.lib.utils import make_readonly

from inselect.tests.utils import temp_directory_with_files


TESTDATA = Path(__file__).parent.parent / 'test_data'


class TestDocument(unittest.TestCase):
    def test_load(self):
        "Load a document from a file"
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)

        # Properties are as expected
        self.assertEqual(doc.document_path, path)
        self.assertEqual(5, len(doc.items))
        self.assertEqual(5, doc.n_items)
        self.assertEqual(doc.scanned.path, path.with_suffix('.png'))
        self.assertTrue(doc.thumbnail is None)
        self.assertEqual(TESTDATA / 'test_segment_crops', doc.crops_dir)
        self.assertEqual('Lawrence Hudson', doc.properties['Created by'])
        self.assertEqual("2015-03-14T09:19:47",
                         doc.properties['Created on'].strftime('%Y-%m-%dT%H:%M:%S'))
        self.assertEqual('Lawrence Hudson', doc.properties['Saved by'])
        self.assertEqual("2015-03-14T09:19:47",
                         doc.properties['Saved on'].strftime('%Y-%m-%dT%H:%M:%S'))

        # Check read-only properties
        with self.assertRaises(AttributeError):
            doc.document_path = ''
        with self.assertRaises(AttributeError):
            doc.items = []
        with self.assertRaises(AttributeError):
            doc.crops_dir = ''
        with self.assertRaises(AttributeError):
            doc.n_items = 1

    def _test_load_fails(self, contents):
        """Helper that writes contents to a temp file and asserts that
        InselectDocument.load raises.
        """
        # Temporary files on Windows are pain
        f = tempfile.NamedTemporaryFile(delete=False)
        try:
            f.write(contents)
            f.seek(0)
            f.close()
            self.assertRaises(InselectError, InselectDocument.load, f.name)
        finally:
            os.unlink(f.name)

    def test_load_not_json_document(self):
        "Try to load a file that is not a json document"
        self._test_load_fails('XYZ')

    def test_load_not_inselect_document(self):
        "Try to load a json file that is not an inselect document"
        self._test_load_fails('{"x": 1}')

    def test_load_bad_version(self):
        "Try to load an inselect document with an unsupported version"
        self._test_load_fails('{"items": [], "inselect version": 1000}')
        self._test_load_fails('{"items": [], "inselect version": -1}')

    def test_load_images(self):
        "Load document's images"
        source = TESTDATA / 'test_segment.inselect'
        with temp_directory_with_files(TESTDATA / 'test_segment.inselect') as tempdir:
            doc_temp = tempdir / 'test_segment.inselect'
            doc_temp.open('w').write(source.open().read())

            # Document load with no scanned image file
            self.assertRaises(InselectError, InselectDocument.load, doc_temp)

            # Document load with scanned image file present
            scanned_temp = tempdir / 'test_segment.png'
            scanned_temp.open('w')       # File only needs to exist
            actual = InselectDocument.load(doc_temp)
            self.assertEqual(InselectDocument.load(source).items, actual.items)
            self.assertFalse(actual.thumbnail)

            # Document load with scanned and thumbnail files present
            thumbnail_temp = tempdir / 'test_segment_thumbnail.jpg'
            thumbnail_temp.open('w')       # File only needs to exist
            actual = InselectDocument.load(doc_temp)
            self.assertEqual(InselectDocument.load(source).items, actual.items)
            self.assertTrue(actual.thumbnail)

    def test_save(self):
        "Save document"
        with temp_directory_with_files(TESTDATA / 'test_segment.inselect',
                                       TESTDATA / 'test_segment.png') as tempdir:
            items = [{
                'fields': {'type': u'インセクト'},
                'rect': Rect(0.1, 0.2, 0.5, 0.5),
            }]

            doc_temp = tempdir / 'test_segment.inselect'
            d = InselectDocument.load(doc_temp)
            d.set_items(items)
            d.save()

            self.assertEqual(items, InselectDocument.load(doc_temp).items)

            # Saved on time should be within last 2 seconds
            now = datetime.now(pytz.timezone("UTC"))
            saved_on = d.properties['Saved on']
            self.assertLessEqual((now - saved_on).seconds, 2)

    def test_repr(self):
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)
        expected = "InselectDocument ['{0}'] [5 items]".format(str(doc.scanned.path))
        self.assertEqual(expected, repr(doc))

    def test_crops(self):
        "Cropped object images are as expected"
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)

        self.assertEqual(5, len(doc.items))

        # Check the contents of each crop
        boxes = doc.scanned.from_normalised([i['rect'] for i in doc.items])
        for box, crop in izip(boxes, doc.crops):
            x0, y0, x1, y1 = box.coordinates
            self.assertTrue(np.all(doc.scanned.array[y0:y1, x0:x1] == crop))

    def test_set_items(self):
        "Items are set as expected"
        # TODO LH Check field validation
        path = TESTDATA / 'test_segment.inselect'
        doc = InselectDocument.load(path)

        items = [{'fields': {}, 'rect': Rect(0, 0, 0.5, 0.5)}]
        doc.set_items(items)
        self.assertEqual(items, doc.items)

    def test_new_from_scan(self):
        "New document is created and saved"
        with temp_directory_with_files(TESTDATA / 'test_segment.png') as tempdir:
            doc = InselectDocument.new_from_scan(tempdir / 'test_segment.png')
            self.assertTrue(doc.document_path.is_file())
            self.assertEqual(tempdir / 'test_segment.png', doc.scanned.path)

            # Saved on time should be within last 2 seconds
            now = datetime.now(pytz.timezone("UTC"))
            created_on = doc.properties['Created on']
            self.assertLessEqual((now - created_on).seconds, 2)

    def test_new_from_scan_doc_exists(self):
        "Document of scanned image already exists"
        path = TESTDATA / 'test_segment.png'
        self.assertRaises(InselectError, InselectDocument.new_from_scan, path)

    def test_new_from_thumbnail(self):
        "Can't create a document from a thumbnail image"
        with temp_directory_with_files(TESTDATA / 'test_segment.png') as tempdir:
            doc = InselectDocument.new_from_scan(
                tempdir / 'test_segment.png',
                thumbnail_width_pixels=2048
            )
            thumbnail = tempdir / 'test_segment_thumbnail.jpg'
            self.assertTrue(thumbnail.is_file())
            self.assertEqual(2048, doc.thumbnail.array.shape[1])
            self.assertRaises(InselectError, InselectDocument.new_from_scan,
                              thumbnail)

    def test_new_from_scan_no_image(self):
        "Image does not exist"
        self.assertRaises(
            InselectError, InselectDocument.new_from_scan, 'i am not a file'
        )

    def test_thumbnail_silly_size(self):
        "Can't create thumbnail with a silly size"
        with temp_directory_with_files(TESTDATA / 'test_segment.png') as tempdir:
            self.assertRaisesRegexp(
                InselectError, "width should be between",
                InselectDocument.new_from_scan, tempdir / 'test_segment.png', -1
            )
            self.assertRaisesRegexp(
                InselectError, "width should be between",
                InselectDocument.new_from_scan, tempdir / 'test_segment.png', 50
            )
            self.assertRaisesRegexp(
                InselectError, "width should be between",
                InselectDocument.new_from_scan, tempdir / 'test_segment.png',
                20000
            )

    @unittest.skipIf(sys.platform.startswith("win"),
                     "Read-only directories not available on Windows")
    def test_thumbnail_read_only(self):
        "Can't write thumbnail to a read-only directory"
        # This case is doing more than simply testing filesystem behavour
        # because it tests the failure code in InselectDocument
        with temp_directory_with_files(TESTDATA / 'test_segment.png') as tempdir:
            mode = make_readonly(tempdir)

            self.assertRaises(
                InselectError, InselectDocument.new_from_scan,
                tempdir / 'test_segment.png', thumbnail_width_pixels=2048
            )

            # Restor the original mode
            tempdir.chmod(mode)

    def test_thumbnail_path_of_scanned(self):
        self.assertEqual(Path('x_thumbnail.jpg'),
                         InselectDocument.thumbnail_path_of_scanned('x.png'))

    def test_path_is_thumbnail_file(self):
        with temp_directory_with_files() as tempdir:
            thumbnail = tempdir / 'xx_thumbnail.jpg'
            thumbnail.open('w')       # File only needs to exist

            # Thumbnail file exists but there is no corresponding .inselect doc
            self.assertFalse(InselectDocument.path_is_thumbnail_file(thumbnail))

            doc = tempdir / 'xx.inselect'
            doc.open('w')       # File only needs to exist

            # Thumbnail file and corresponding .inselect file both exist
            self.assertTrue(InselectDocument.path_is_thumbnail_file(thumbnail))

if __name__ == '__main__':
    unittest.main()
