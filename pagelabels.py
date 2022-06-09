#
# https://github.com/lovasoa/pagelabels-py/tree/master/pagelabels
# GPL-v3
from collections import namedtuple

from pdfrw import PdfName, PdfDict, PdfArray, PdfObject, PdfString


defaults = {"style": "arabic", "prefix": "", "firstpagenum": 1}
styles = {
    "arabic": PdfName("D"),
    "roman lowercase": PdfName("r"),
    "roman uppercase": PdfName("R"),
    "letters lowercase": PdfName("a"),
    "letters uppercase": PdfName("A"),
    "none": None,
}
stylecodes = {v: a for a, v in styles.items()}


PageLabelTuple = namedtuple("PageLabelScheme", "startpage style prefix firstpagenum")


class PageLabelScheme(PageLabelTuple):
    """Represents a page numbering scheme.
    startpage : the index in the pdf (starting from 0) of the
                first page the scheme will be applied to.
    style : page numbering style (arabic, roman [lowercase|uppercase], letters [lowercase|uppercase])
    prefix: a prefix to be prepended to all page labels
    firstpagenum : where to start numbering
    """

    __slots__ = tuple()

    def __new__(
        cls,
        startpage,
        style=defaults["style"],
        prefix=defaults["prefix"],
        firstpagenum=defaults["firstpagenum"],
    ):
        if style not in styles:
            raise ValueError("PageLabel style must be one of %s" % cls.styles())
        return super().__new__(
            cls, int(startpage), style, str(prefix), int(firstpagenum)
        )

    @classmethod
    def from_pdf(cls, pagenum, opts):
        """Returns a new PageLabel using options from a pdfrw object"""
        return cls(
            pagenum,
            style=stylecodes.get(opts.S, defaults["style"]),
            prefix=(opts.P and opts.P.decode() or defaults["prefix"]),
            firstpagenum=(opts.St or defaults["firstpagenum"]),
        )

    @staticmethod
    def styles():
        """List of the allowed styles"""
        return styles.keys()

    def pdfobjs(self):
        """Returns a tuple of two elements to insert in the PageLabels.Nums
        entry of a pdf"""
        page_num = PdfObject(self.startpage)
        opts = PdfDict(S=styles[self.style])
        if self.prefix != defaults["prefix"]:
            opts.P = PdfString.encode(self.prefix)
        if self.firstpagenum != defaults["firstpagenum"]:
            opts.St = PdfObject(self.firstpagenum)
        return page_num, opts


class PageLabels(list):
    @classmethod
    def from_pdf(cls, pdf):
        """Create a PageLabels object by reading the page labels of
        the given PdfReader object"""
        labels = pdf.Root.PageLabels
        if not labels:
            return cls([])
        nums = labels.Nums
        parsed = (
            PageLabelScheme.from_pdf(nums[i], nums[i + 1])
            for i in range(0, len(nums), 2)
        )
        return cls(parsed)

    def normalize(self, pagenum=float("inf")):
        """Sort the pagelabels, remove duplicate entries,
        and if pegenum is set remove entries that have a startpage >= pagenum"""
        # Remove duplicates
        page_nums = dict()
        for elem in self[:]:
            oldelem = page_nums.get(elem.startpage)
            if oldelem is not None or elem.startpage >= pagenum:
                self.remove(oldelem)
            else:
                page_nums[elem.startpage] = elem
        self.sort()
        if len(self) == 0 or self[0].startpage != 0:
            self.insert(0, PageLabelScheme(0))

    def pdfdict(self):
        """Return a PageLabel entry to pe inserted in the root of a PdfReader object"""
        nums = (i for label in sorted(self) for i in label.pdfobjs())
        return PdfDict(Type=PdfName("Catalog"), Nums=PdfArray(nums))

    def write_raw(self, pdf):
        """Write the PageLabels to a PdfReader object without sanity checks
        Use at your own risks, this may corrupt your PDF"""
        pdf.Root.PageLabels = self.pdfdict()

    def write(self, pdf):
        """Write the PageLabels to a PdfReader object, normalizing it first"""
        self.normalize(len(pdf.pages))
        pdf.Root.PageLabels = self.pdfdict()
