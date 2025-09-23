# modifier.py
import os
import tempfile
import streamlit as st
import fitz  # PyMuPDF
from difflib import SequenceMatcher
from llm_helper import call_llm_with_fallback


def _rewrite_clause_with_llm(analysis_item):
    """
    Calls the LLM to rewrite a high-risk clause into a safer, compliant one.
    """
    original_clause = analysis_item.get("clause", "")
    regulation = analysis_item.get("regulation", "General Legal")
    risk = analysis_item.get("risk", "")

    prompt = f"""
You are a contract compliance expert. 
Your task: rewrite the following clause so that it is legally sound, risk-free, 
and compliant with {regulation}. 

Original clause:
\"\"\"{original_clause}\"\"\"

Identified risk:
- {risk}

Rewrite this clause in natural, professional contract language, 
keeping the business intent but ensuring compliance and zero high-risk exposure.

Return ONLY the rewritten clause as plain text (no JSON, no explanations).
"""

    try:
        safe_clause = call_llm_with_fallback(prompt).strip()
        return safe_clause
    except Exception as e:
        return f"[SAFE CLAUSE] Replacement failed due to error: {str(e)[:200]}"


def _find_best_match_on_page(page, clause_text, threshold=0.75):
    """
    Search for approximate (fuzzy) matches of clause_text on the page.
    Returns the rects of the best match if found.
    """
    words = page.get_text("words")  # list of (x0, y0, x1, y1, word, block_no, line_no, word_no)
    words_sorted = sorted(words, key=lambda w: (w[5], w[6], w[7]))
    text_on_page = " ".join(w[4] for w in words_sorted)

    matcher = SequenceMatcher(None, text_on_page.lower(), clause_text.lower())
    match = matcher.find_longest_match(0, len(text_on_page), 0, len(clause_text))

    if match.size / max(1, len(clause_text)) >= threshold:
        # Collect rects corresponding to this span
        matched_words = words_sorted[match.a : match.a + match.size]
        rects = [fitz.Rect(w[:4]) for w in matched_words]
        return rects, text_on_page[match.a : match.a + match.size], match.size / len(clause_text)

    return None, None, 0.0


def _overlay_replacement(new_page, rects, replacement_text):
    """
    Overlays rewritten clause by expanding rects into one bounding box.
    """
    if not rects:
        return

    # Union of all rectangles
    x0 = min(r.x0 for r in rects)
    y0 = min(r.y0 for r in rects)
    x1 = max(r.x1 for r in rects)
    y1 = max(r.y1 for r in rects)
    union_rect = fitz.Rect(x0, y0, x1, y1)

    # Slightly expand to fully cover old text
    expanded_rect = union_rect + (-2, -2, 2, 2)

    # White-out old text
    new_page.draw_rect(expanded_rect, color=(1, 1, 1), fill=(1, 1, 1))

    # Insert new text neatly in that box
    new_page.insert_textbox(
        expanded_rect,
        replacement_text,
        fontsize=10,
        fontname="helv",
        align=0,  # left aligned
    )


def modify_contract_pdf(input_pdf_path, output_pdf_path, analysis_results):
    """
    Create a NEW PDF with the same content as the original,
    replacing High severity clauses with LLM-rewritten safe clauses.
    """
    original_doc = fitz.open(input_pdf_path)
    new_doc = fitz.open()

    # Build map of risky clauses
    high_risk_map = {}
    for item in analysis_results:
        if item.get("severity", "").lower() == "high":
            original_clause = str(item.get("clause", "")).strip()
            safe_clause = _rewrite_clause_with_llm(item)
            high_risk_map[original_clause] = safe_clause

    for page_num in range(len(original_doc)):
        page = original_doc[page_num]
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)

        # Copy full original page into new_doc
        new_page.show_pdf_page(new_page.rect, original_doc, page_num)

        # Replace risky clauses
        for original_clause, safe_clause in high_risk_map.items():
            rects = page.search_for(original_clause)

            if not rects:
                rects, matched_text, score = _find_best_match_on_page(page, original_clause)
                if not rects or score < 0.75:
                    continue  # no match found

            _overlay_replacement(new_page, rects, safe_clause)

    new_doc.save(output_pdf_path)
    new_doc.close()
    original_doc.close()
    return output_pdf_path


def render_download_button(original_pdf_path, analysis_results):
    """
    Generates a brand-new modified contract PDF and renders a download button in Streamlit.
    """
    modified_path = os.path.join(tempfile.gettempdir(), "modified_contract.pdf")
    modify_contract_pdf(original_pdf_path, modified_path, analysis_results)

    with open(modified_path, "rb") as f:
        st.download_button(
            label="⬇️ Download Modified Contract (LLM-Safe)",
            data=f,
            file_name="modified_contract.pdf",
            mime="application/pdf",
        )
