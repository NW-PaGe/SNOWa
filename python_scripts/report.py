from jinja2 import Environment, FileSystemLoader
import argparse
import os
import yaml
from mistletoe import markdown
from fpdf import FPDF

parser = argparse.ArgumentParser(description='This script generates the final report')
parser.add_argument("--template",
                    default="defaults/sc2-ww-template.md",
                    help="template input")
parser.add_argument("--markdown", "-md",
                    default="ww_report.md",
                    help="markdown output filename")
parser.add_argument("--html", "-html",
                    default="ww_report.html",
                    help="html output filepath")

args=parser.parse_args()

with open('defaults/config.yaml', 'r') as f:
    data = yaml.safe_load(f)

report_config=data["report"]

template_name=os.path.basename(args.template)
template_path=os.path.dirname(args.template)

env = Environment(loader=FileSystemLoader(template_path))
template = env.get_template(template_name)

rendered_markdown = template.render(report_config)
rendered_html=markdown(rendered_markdown)

if args.markdown:
    with open(args.markdown, "w") as markdown:
        markdown.write(rendered_markdown)

if args.html:
    with open(args.html, "w") as html:
        html.write(rendered_html)