from sys import stdout, argv
from openpyxl import load_workbook, writer

name_index = argv[1]
file_path = argv[2]
new_path = argv[3]

wb = load_workbook(file_path)
ws = wb.active

ws.insert_cols(0)

for row in ws.rows:
    try:
        row[0].value = row[int(name_index)].hyperlink.display
    except AttributeError:
        pass

wb.save(new_path)
