import html
import argparse
import base64
from datetime import datetime, date

def compile_qc_report(pre_qc, metadata_qc, lineage_mapping_qc, weighted_props_qc, output_html, variant_qc_fig):
    now = datetime.now()
    #convert fig to base64 string
    with open(variant_qc_fig, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    html_report = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>QC Report - {now}</title>
    </head>
    <body>
        <h1>QC Report</h1>
        <p>Generated on: {now}</p>
        <hr>
        
        <pre>{pre_qc}</pre>
        <pre>{metadata_qc}</pre>
        <pre>{lineage_mapping_qc}</pre>
        <pre>{weighted_props_qc}</pre>
        <img src="data:image/jpeg;base64,{encoded_string}" alt="QC plot depicting the detection of variants in wastewater through time" class="center-image" width=900>
        
    </body>
    </html>"""

    with open(output_html, "w", encoding="utf-8") as file:
        file.write(html_report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='This script compiles all of the qc report .txt files into an html report.')
    parser.add_argument("--pre-qc", required=True, help='pre-qc report')
    parser.add_argument("--metadata", required=True, help='metadata qc report')
    parser.add_argument("--lineage-mapping", required=True, help='lineage mapping qc report')
    parser.add_argument("--weighted-props", required=True, help='weighted proportions qc report')
    parser.add_argument("--output-html", "-o", required=True, help="Path for final qc report")
    parser.add_argument("--variant-qc-fig", required=True, help="path for variant qc fig")
    args = parser.parse_args()

    def read_report(file):
        """
        helper for reading in qc files
        """
        with open(file, "r", encoding = "utf-8") as file:
            report_string = file.read()
        return report_string

    pre_qc = read_report(args.pre_qc)
    metadata_qc = read_report(args.metadata)
    lineage_mapping_qc = read_report(args.lineage_mapping)
    weighted_props_qc = read_report(args.weighted_props)

    
    compile_qc_report(pre_qc = pre_qc, 
        metadata_qc = metadata_qc, 
        lineage_mapping_qc= lineage_mapping_qc, 
        weighted_props_qc = weighted_props_qc,
        variant_qc_fig = args.variant_qc_fig,
        output_html = args.output_html)