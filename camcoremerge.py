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

from dataclasses import dataclass
import functools
from pprint import pp
import sys
import os
import re

from pdfrw import PdfReader, PdfWriter

from roman import roman_to_int
from pagelabels import PageLabels, PageLabelScheme

#
# My Own Code
#

# 01.0_pp_i_iv_Frontmatter.pdf
INPUT_PDF_REGEX = r"^([0-9]+)\.([0-9]+)_pp_([^_]+)_([^_]+)_.+\.pdf$"
MAX_PREFIX_LEN = 5000


@dataclass
class SourcePdf:
    name: str
    part_no: int
    chap_no: int

    page_start: int
    page_end: int

    is_roman: bool

    def style(self):
        if self.is_roman:
            return "roman lowercase"
        else:
            return "arabic"

    def npages(self):
        return self.page_end - self.page_start + 1


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


def is_roman1(pageno):
    try:
        int(pageno)
        return False
    except ValueError:
        roman_to_int(pageno)
        return True


def is_roman(p1, p2):
    match is_roman1(p1), is_roman1(p2):
        case True, True:
            return True
        case False, False:
            return False
        case _:
            raise ValueError(f"{p1} and {p2} are not the same type")


def page_cmp(p1, p2):
    cmp_partno = p1.part_no - p2.part_no
    if cmp_partno != 0:
        return cmp_partno
    cmp_chapno = p1.chap_no - p2.chap_no
    if cmp_chapno != 0:
        return cmp_chapno
    raise ValueError(f"{p1} and {p2} are the same")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: %s <input_dir> <output.pdf>" % sys.argv[0])
        sys.exit(1)

    cwd = sys.argv[1]
    outpdf = sys.argv[2]
    assert outpdf.endswith(".pdf")

    parts = []

    for i in os.listdir(cwd):
        if m := re.match(INPUT_PDF_REGEX, i):
            part_no = m.group(1)
            chap_no = m.group(2)
            page_start_str = m.group(3)
            page_end_str = m.group(4)
            part = SourcePdf(
                name=i,
                part_no=int(part_no),
                chap_no=int(chap_no),
                page_start=page_no_real(page_start_str),
                page_end=page_no_real(page_end_str),
                is_roman=is_roman(page_start_str, page_end_str),
            )
            parts.append(part)

    pages: list[SourcePdf] = sorted(parts, key=functools.cmp_to_key(page_cmp))

    # Phaise 1: Merge PDFS
    mergeOut = PdfWriter()
    for p in pages:
        part_pages = PdfReader(os.path.join(cwd, p.name)).pages
        if len(part_pages) != p.npages():
            print(f"{p.name} has {len(part_pages)} pages, expected {p.npages()}")
            exit(1)
        print(
            f"{p.name:70} {p.part_no:3}, {p.chap_no:3}, {p.page_start:5}, {p.page_end:5} {p.is_roman}"
        )
        mergeOut.addpages(part_pages)
    mergeOut.write(outpdf)

    # Phaise 2: Relabel
    relabelIn = PdfReader(outpdf)
    labels = PageLabels.from_pdf(relabelIn)
    rpn = 0
    for p in pages:
        labels.append(
            PageLabelScheme(startpage=rpn, style=p.style(), firstpagenum=p.page_start)
        )
        rpn += p.npages()
    labels.write(relabelIn)
    relabelOut = PdfWriter()
    relabelOut.trailer = relabelIn
    relabelOut.write(outpdf)
