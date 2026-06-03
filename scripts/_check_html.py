"""Rewrite html_report.py with new Xenium-style tab layout."""
import sys
sys.path.insert(0, "/home/zf-li23/SubCellSpace")
from src.html_report import generate_html_report

content = open("/home/zf-li23/SubCellSpace/src/html_report.py").read()
print(f"Current size: {len(content)} chars, {len(content.splitlines())} lines")
print("Ready to rewrite")
