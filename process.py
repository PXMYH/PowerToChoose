import fitz  # PyMuPDF
from pprint import pprint
from cleanSkyParser import CleanSkyParser


def extract_pdf_content(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # Iterate through pages
    for page_number in range(pdf_document.page_count):
        # Get the page
        page = pdf_document[page_number]

        # Extract text from the page
        text = page.get_text("text")

        # Print or process the extracted text (you can customize this part)
        print(f"Page {page_number + 1}:\n{text}\n")

    # Close the PDF file
    pdf_document.close()


def extract_pdf_table(pdf_path):
    doc = fitz.open(pdf_path)  # open document
    # The information we need should be on the first pag
    page = doc[0]  # get the 1st page of the document
    tabs = page.find_tables()  # locate and extract any tables on page
    print(f"{len(tabs.tables)} found on {page}"
          )  # display number of found tables
    if tabs.tables:  # at least one table found?
        # pprint(tabs[0].extract())  # print content of first table
        return tabs[0].extract()  # return content of first table


# Provide the path to your PDF file
# pdf_file_path = "fact_sheets/Cleansky_Energyembrace_Green_8_New_Customer_Special.pdf"

# pdf_file_path = "fact_sheets/Txu_Energysimple_Value_12.pdf"
# Call the function to extract content
# extract_pdf_content(pdf_file_path)

pdf_file_path = "fact_sheets/Discount_Powersaver_12.pdf"

content_table = extract_pdf_table(pdf_file_path)
# print(f"content_table = {content_table}")
CleanSkyParser().parse(content_table)
