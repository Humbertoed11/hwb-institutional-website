import os
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.worksheet.pagebreak import Break
from openpyxl.workbook.defined_name import DefinedName

print("Testing Option 1 Layout...")
