import getopt
import os
import time
import sys

import fitz


def search_string_in_pdf_first_page(file_path: str, string: str):
    doc = fitz.open(file_path)
    first_page = doc[0]

    return string in first_page.getText()


def is_page_empty(file_path):
    doc = fitz.open(file_path)
    first_page = doc[0]

    return not first_page.getTextBlocks()


def add_interactive_toc(output_file):
    # move the old file, to prevent conflicts and empty pages
    old_output_file = output_file.replace('.pdf', '_old.pdf')
    os.rename(output_file, old_output_file)
    doc = fitz.open(old_output_file)

    toc_page = None
    toc = {}
    toc_list = []

    for page in doc:
        if not toc_page:  # table of content was not defined yet
            for block in page.getText('blocks'):
                # getText('blocks') returns tuple of the type
                # (x0, y0, x1, y1, "lines in blocks", block_no, block_type)
                block_type = block[6]
                block_text = block[4]

                # block_type 0 is a text bloc, if it's not - continue
                if block_type != 0:
                    continue

                # if the page has "Table of Content" in it, assume it's the table of contents
                if 'Table of Content' in block_text:
                    toc_page = page

                # after we've located the table of contents, add all the other text
                # blocks to the potential table of contents
                elif toc_page:
                    # block[4] is the blocks content
                    el_txt = block_text.replace('\n', '')

                    # don't add the text
                    if ' of ' not in el_txt and 'Created by:' not in el_txt:
                        toc[el_txt] = block
        # after locating the table of content, look where to link from the table of contents page
        else:
            for block in page.getText('blocks'):
                block_type = block[6]
                block_text = block[4]

                if block_type != 0:
                    continue

                try:
                    # get the table of contents text, and find the relevant block
                    loc = toc.pop(
                        block_text
                            .split('\n')[0]  # remove the "Document Creation Date" string
                            .split(' - ')[0]  # in case of "Highlighted issues - <XXX>"
                    )
                    x0, y0, x1, y1 = loc[:4]
                    toc_line_text = loc[4]

                    link_dict = {'kind': 1, 'page': page.number, 'from': fitz.Rect(x0, y0, x1, y1)}

                    # add a link overlay over that block
                    toc_page.insertLink(link_dict)

                    # add a bookmark to the same page, bookmark page numbers are 1 based
                    toc_list.append([1, toc_line_text, page.number + 1])

                except KeyError:  # there is no matching item in the table of contents
                    pass
                break

        if page.number > 0:
            rect = fitz.Rect(0, 841 - 18, 595, 841)  # footer size
            color = (0x66 / 0xff, 0x53 / 0xff, 1)  # vdoo color, in 0-1 notation

            pg_num_string = f'{page.number + 1} / {doc.pageCount} Pages'
            year = time.strftime('%Y')
            copyright_str = f'© {year} Vdoo. All Rights Reserved  |  info@vdoo.com'

            page.drawRect(rect, color, color)
            page.insertText((15, 835), pg_num_string, fontsize=8, color=1)
            page.insertText((415, 835), copyright_str, fontsize=7, color=1)

    doc.set_toc(toc_list)
    doc.save(output_file)


if __name__ == '__main__':
    # Used as a wrapper for PyMuPDF
    if len(sys.argv) < 3:
        print('Usage is: generate_pdf_utils.py <function> -f <file path> [-t <text to search>]')
        sys.exit(1)
    func = sys.argv[1]
    opts, args = getopt.getopt(sys.argv[2:], 'f:t:', ['file=', 'text='])
    file, text = None, None

    # Parse function params
    for opt, val in opts:
        if opt in ['-f', '--file']:
            file = val
        if opt in ['-t', '--text']:
            text = val
    if file is None:
        print('<file> is required')
        sys.exit(1)

    # Call appropriate function. exit(0) stands for True, exit(1) error, and exit(2) False
    if func == 'toc':
        # No output for this function
        add_interactive_toc(file)
    elif func == 'page_empty':
        if not is_page_empty(file):
            sys.exit(2)
    elif func == 'text_in_page':
        if text is None:
            print('Text is required for this option')
            sys.exit(1)
        if not search_string_in_pdf_first_page(file, text):
            sys.exit(2)
    else:
        print(f'Unknown func "{func}". Options are: toc, page_empty, text_in_page')
        sys.exit(1)
