import re


# The information we cared about is the base rate and delivery rate so we can plug those numbers to the simulator
class CleanSkyParser:

    def __init__(self) -> None:
        pass

    def parse(self, table: list[list[str]]):
        # get all table content together
        flat_table = ' '.join(
            filter(None, [
                item for sublist in table if sublist is not None
                for item in sublist
            ]))

        # Use regex to extract the substring between "Average monthly use" and "Other Key Terms and Questions"
        match = re.search(
            r'Average monthly use:(.*?)Other Key\nTerms and\nquestions',
            flat_table, re.DOTALL)

        # Extract the matched substring
        if match:
            extracted_string = match.group(1).strip()
            print("----------------")
            print(extracted_string)
        else:
            print("Substring not found.")
