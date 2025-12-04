import sys
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.google_auth import get_credentials

def get_docs_service():
    creds = get_credentials()
    return build('docs', 'v1', credentials=creds)

def read_structural_elements(elements):
    """Recursively read text from structural elements."""
    text = ''
    for value in elements:
        if 'paragraph' in value:
            elements = value.get('paragraph').get('elements')
            for elem in elements:
                text += elem.get('textRun', {}).get('content', '')
        elif 'table' in value:
            table = value.get('table')
            for row in table.get('tableRows'):
                for cell in row.get('tableCells'):
                    text += read_structural_elements(cell.get('content'))
        elif 'tableOfContents' in value:
            toc = value.get('tableOfContents')
            text += read_structural_elements(toc.get('content'))
    return text

def get_document_text(doc_id):
    """Retrieve full text content from a Google Doc."""
    try:
        service = get_docs_service()
        document = service.documents().get(documentId=doc_id).execute()
        content = document.get('body').get('content')
        return read_structural_elements(content)
    except HttpError as err:
        print(f"An error occurred: {err}")
        return None

if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(get_document_text(sys.argv[1]))
    else:
        print("Usage: python google_docs_utils.py <doc_id>")
