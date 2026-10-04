"""
Office Engine: Template Merger Module
Wraps docxtpl for instant Jinja2 data injection into designer Word templates (.docx).
"""

import os
from typing import Dict, Any
from docxtpl import DocxTemplate

class TemplateMerger:
    @staticmethod
    def render(template_path: str, context: Dict[str, Any], output_path: str) -> str:
        """
        Loads a pre-designed Word document (.docx) containing Jinja2 syntax
        (e.g., {{ client_name }}, {% for item in items %}) and renders the data.
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template document not found at: {template_path}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        doc = DocxTemplate(template_path)
        doc.render(context)
        doc.save(output_path)
        return output_path
