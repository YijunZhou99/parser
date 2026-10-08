"""Current: real p4l page extraction, source observations and original PNG rendering.
Limitations: OCR disabled; canonical revision changes invalidate replay inputs.
TODO(B2): validate extraction and source observations on reviewed defects.
Acceptance: first-six-page real PDF smoke and rendering checks.
"""
import hashlib
import pymupdf
import pymupdf4llm

def sha(data):
    return hashlib.sha256(data).hexdigest()


def extract(pdf, selected=None):
    digest = sha(pdf)
    with pymupdf.open(stream=pdf, filetype='pdf') as doc:
        selected = selected or list(range(1, len(doc) + 1))
        if len(set(selected)) != len(selected) or selected != sorted(selected) or any(p < 1 or p > len(doc) for p in selected):
            raise ValueError('Pages must be unique, ascending original 1-based page numbers')
        outputs = []
        for number in selected:
            page = doc[number - 1]
            error=None
            try:
                md = pymupdf4llm.to_markdown(doc, pages=[number - 1], show_progress=False,
                                           header=True, footer=True, use_ocr=False)
            except Exception as exc:
                md=''; error=f'{type(exc).__name__}: {exc}'
            if isinstance(md, list): md = '\n'.join(c['text'] for c in md)
            blocks = [list(b[:4]) for b in page.get_text('blocks') if len(b) > 6 and b[6] == 0]
            plain = page.get_text()
            table_error=None
            try: table_count=len(page.find_tables().tables)
            except Exception as exc:
                table_count=None; table_error=f'{type(exc).__name__}: {exc}'
            outputs.append({'document_hash': digest, 'page': number, 'markdown': md,
                            'source_engine': 'pymupdf4llm', 'plain_text': plain,
                            'blocks': blocks, 'width': page.rect.width,
                            'table_count':table_count, 'table_check_error':table_error,
                            'extraction_status':'failed' if error else 'extracted', 'extraction_error':error})
    return outputs


def render(pdf, page):
    with pymupdf.open(stream=pdf, filetype='pdf') as doc:
        return doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25)).tobytes('png')




def canonical_revision(pages, document_hash):
    return sha((document_hash + str([(p['page'], p['markdown']) for p in pages])).encode())
