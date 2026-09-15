"""
Multi-page PDF test script
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

pdf_path = Path("sample_data/Test_5_Pages.pdf")
doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
styles = getSampleStyleSheet()

story = []
for i in range(1, 6):
    story.append(Paragraph(f"This is Section {i} on Page {i} of the 5-page document.", styles["Heading1"]))
    story.append(Paragraph(f"Content for page {i}. Testing multi-page PDF ingestion and indexing.", styles["Normal"]))
    if i < 5:
        story.append(PageBreak())

doc.build(story)
print("Created 5-page test PDF:", pdf_path)

from backend.ingestion import extract_pages_from_pdf
from backend.chunking import chunk_extracted_pages
from backend.vector_store import add_chunks_to_store, list_indexed_documents, clear_vector_store

pages = extract_pages_from_pdf(pdf_path)
print(f"Extracted pages count: {len(pages)}")
for p in pages:
    pg_num = p['page_number']
    tot_pg = p['total_pages']
    txt = p['text'][:40]
    print(f"  Page {pg_num} of {tot_pg}: {txt}")

chunks = chunk_extracted_pages(pages)
print(f"Total chunks created: {len(chunks)}")

add_chunks_to_store(chunks)
docs = list_indexed_documents()
print("Indexed doc stats:", docs)
