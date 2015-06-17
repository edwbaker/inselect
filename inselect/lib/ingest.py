import re

from .document import InselectDocument
from .inselect_error import InselectError
from .utils import debug_print, make_readonly

# Supported image formats
IMAGE_SUFFIXES = ('.bmp', '.jpeg', '.jpg', '.png', '.tif', '.tiff',)

# A case-insensitive regular expression that matches each suffix
IMAGE_SUFFIXES_RE = '|'.join('{0}'.format(p[1:]) for p in IMAGE_SUFFIXES)
IMAGE_SUFFIXES_RE = '^.*\\.({0})$'.format(IMAGE_SUFFIXES_RE)
IMAGE_SUFFIXES_RE = re.compile(IMAGE_SUFFIXES_RE, re.IGNORECASE)
IMAGE_SUFFIXES_RE.pattern

# Patterns in the form *.bmp, *.jpeg etc
IMAGE_PATTERNS = tuple(['*{0}'.format(s) for s in IMAGE_SUFFIXES])


def ingest_image(source, dest_dir):
    """Copies the image in the path source to the directory in the path
    dest_dir. Creates an returns a new instance of InselectDocument for the
    copied image.

    An exception is raised if the destination image exists.
    An exception is raised if the Inselect document already exists.
    """
    dest = dest_dir / source.name
    if source!=dest and dest.is_file():
        raise InselectError('Destination image [{0}] exists'.format(dest))
    else:
        debug_print('Ingesting [{0}] to [{1}]'.format(source, dest))

        if source!=dest:
            source.rename(dest)

        # Raises if the document already exists
        doc = InselectDocument.new_from_scan(dest)

        # TODO Resolution to come from template
        doc.ensure_thumbnail()

        # Make images read-only
        debug_print('Making image files read-only')
        make_readonly(doc.scanned.path)
        make_readonly(doc.thumbnail.path)

        # TODO LH Copy EXIF tags?
        debug_print('Ingested [{0}] to [{1}]'.format(source, dest))

        return doc
