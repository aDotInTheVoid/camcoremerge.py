#!/usr/bin/env python3

# camcoremerge.py: Merges Cambridges Core PDF's

# Copyright (C) 2022 Nixon Enraght-Moony

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pprint import pp
import sys
import os
from collections import namedtuple
import re

from pdfrw import PdfReader, PdfWriter, PdfName, PdfDict, PdfArray, PdfObject, PdfString

#
# https://www.oreilly.com/library/view/python-cookbook/0596001673/ch03s24.html
#
def int_to_roman(input):
    if not isinstance(input, type(1)):
        raise TypeError("expected integer, got %s" % type(input))
    if not 0 < input < 4000:
        raise ValueError("Argument must be between 1 and 3999")
    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ("M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I")
    result = []
    for i in range(len(ints)):
        count = int(input / ints[i])
        result.append(nums[i] * count)
        input -= ints[i] * count
    return "".join(result)


def roman_to_int(input):
    if not isinstance(input, str):
        raise TypeError(f"expected string, got {type(input)}")
    input = input.upper()
    nums = {"M": 1000, "D": 500, "C": 100, "L": 50, "X": 10, "V": 5, "I": 1}
    sum = 0
    for i in range(len(input)):
        try:
            value = nums[input[i]]
            # If the next place holds a larger number, this value is negative
            if i + 1 < len(input) and nums[input[i + 1]] > value:
                sum -= value
            else:
                sum += value
        except KeyError:
            raise ValueError("input is not a valid Roman numeral: %s" % input)
    # easiest test for validity...
    if int_to_roman(sum) == input:
        return sum
    else:
        raise ValueError("input is not a valid Roman numeral: %s" % input)


#
# https://github.com/lovasoa/pagelabels-py/tree/master/pagelabels
# GPL-v3

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


#
# My Own Code
#


# 01.0_pp_i_iv_Frontmatter.pdf
INPUT_PDF_REGEX = r"^[0-9]+\.[0-9]+_pp_([^_]+)_([^_]+)_.+\.pdf$"
MAX_PREFIX_LEN = 5000


def page_no_ish(pageno):
    try:
        return int(pageno)
    except ValueError:
        return roman_to_int(pageno) - MAX_PREFIX_LEN


def page_no_real(pageno):
    try:
        return int(pageno)
    except ValueError:
        return roman_to_int(pageno)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: %s <input_dir> <output.pdf>" % sys.argv[0])
        sys.exit(1)

    cwd = sys.argv[1]
    outpdf = sys.argv[2]
    assert outpdf.endswith(".pdf")

    pages = []

    for i in os.listdir(cwd):
        if m := re.match(INPUT_PDF_REGEX, i):
            pages.append(
                (
                    i,
                    m.group(1),
                    m.group(2),
                    page_no_ish(m.group(1)),
                    page_no_ish(m.group(2)),
                )
            )

    pages = sorted(pages, key=lambda x: x[3])

    # Phaise 1: Merge PDFS
    mergeOut = PdfWriter()
    for i, s_start, s_end, i_start, i_end in pages:
        part_pages = PdfReader(os.path.join(cwd, i)).pages
        assert len(part_pages) == i_end - i_start + 1
        print(f"{i:70} {s_start}, {s_end}")
        mergeOut.addpages(part_pages)
    mergeOut.write(outpdf)

    # Phaise 2: Relabel
    relabelIn = PdfReader(outpdf)
    labels = PageLabels.from_pdf(relabelIn)
    rpn = 0
    for i, s_start, s_end, i_start, i_end in pages:
        sty = "arabic" if str(i_start) == s_start else "roman lowercase"
        labels.append(
            PageLabelScheme(
                startpage=rpn, style=sty, firstpagenum=page_no_real(s_start)
            )
        )
        rpn += i_end - i_start + 1
    labels.write(relabelIn)
    relabelOut = PdfWriter()
    relabelOut.trailer = relabelIn
    relabelOut.write(outpdf)
