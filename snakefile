configfile: os.path.join(workflow.basedir, "defaults/config.yaml")
containerized: config["containerized"]

from datetime import date
from glob import glob

# Plotting
PLOT_KEYS = list(config["plots"]["filter"].keys())

PLOT_EXTENSIONS = {
    "stacked_bar_plt": "jpeg",
    "qc_pa_plt": "jpeg",
    "bubble_plt": "jpeg",
    "line_plt": "jpeg",
    "heatmap_plt": "jpeg",
    "weekly_maps_plt": "jpeg",
}

FILTERED_PLOT_CSVS = expand(
    "results/filtered/{plot_key}_filtered.csv",
    plot_key=PLOT_KEYS
)

PLOT_FILES = expand(
    config["plots"]["plot_dir"] + "{plot_key}.{ext}",
    zip,
    plot_key=PLOT_KEYS,
    ext=[PLOT_EXTENSIONS[plot_key] for plot_key in PLOT_KEYS]
)

rule all:
    input:
        "results/qc/weekly_county_report.txt",
        "results/full_qc_report.txt",
        FILTERED_PLOT_CSVS,
        PLOT_FILES,
        "results/plots/plot_list.txt",
        "results/ww_report.pdf"

rule pre_qc:
    output: 
        qc="results/qc/pre_qc_report.txt"
    params: 
        copy_runs=config["pre_qc"]["copy_runs"],
        directory=config["pre_qc"]["directory"]
    shell:
        """
        echo $'{params.copy_runs}' | python3 python_scripts/pre_qc.py \
            --directory {params.directory} \
            > {output.qc}
        """

rule merge_data:
    output: 
        data="results/raw_combined_output.csv"
    params:
        directory=config["merge_data"]["directory"]
    shell:
        """
        python3 python_scripts/merge_data.py \
            --directory {params.directory}  --output {output.data}
        """

rule metadata_qc_raw:
    input:
        data="results/raw_combined_output.csv"
    output:
        csv="results/combined_output.csv",
        log="results/qc/metadata_qc_raw.txt"
    shell:
        """
        python3 python_scripts/metadata_qc_raw.py --input {input.data} --output-csv {output.csv} --output-txt {output.log}
        """

rule add_site_and_classifications:
    input:
        data="results/combined_output.csv"
    params:
        sites=config["add_sites_and_classes"]["sites"],
        classifications=config["add_sites_and_classes"]["classifications"]
    output:
        data="results/ww_data.csv"
    shell:
        """
        python3 python_scripts/add_site_and_classifications.py \
            --sites {params.sites} \
            --classifications {params.classifications} \
            --input {input.data} \
            --output {output.data}
        """

rule variant_lineage_mapping_qc:
    input:
        data="results/ww_data.csv"
    output:
        reference="results/qc/variant_reference.csv",
        qc="results/qc/lineage_mapping_qc_report.txt"
    shell:
        """
        python3 python_scripts/check_variant_lineage_mapping.py -i {input.data} -r {output.reference} > {output.qc}
        """

rule add_population_weights:
    input:
        data="results/ww_data.csv"
    output:
        data="results/state_weighted_proportions.csv"
    shell:
        """
        python3 python_scripts/add_population_weights.py -i {input.data} -o {output.data}
        """

rule add_county_weights:
    input:
        data="results/ww_data.csv"
    output:
        data="results/county_weighted_proportions.csv"
    shell:
        """
        python3 python_scripts/add_county_weights.py -i {input.data} -o {output.data}
        """

rule pop_weighted_proportions_qc:
    input:
        state="results/state_weighted_proportions.csv",
        county="results/county_weighted_proportions.csv"
    output:
        qc="results/qc/weighted_proportions_qc_report.txt"
    shell:
        """
        python3 python_scripts/pop_weights_qc.py \
            --state {input.state} \
            --county {input.county} \
            --output-txt {output.qc}
        """

rule filter_by_timeframe:
    input:
        state="results/state_weighted_proportions.csv",
        county="results/county_weighted_proportions.csv"
    params:
        config=config["plots"]["filter"]
    output:
        FILTERED_PLOT_CSVS
    script:
        "python_scripts/filter_by_timeframe.py"

# ADD WEEKLY COUNTY PROPORTIONS REPORT FOR WEEKLY MAPS QC
rule weekly_county_report:
    input:
        county="results/filtered/weekly_maps_plt_filtered.csv"
    output:
        report="results/qc/weekly_county_report.txt"
    shell: 
        """
        python3 python_scripts/weekly_county_report.py -i  {input.county} > {output.report}
        """

rule plots:
    input:
        filtered=FILTERED_PLOT_CSVS
    output:
        plots=PLOT_FILES,
        plot_list="results/plots/plot_list.txt"
    params:
        plot_dir=config["plots"]["plot_dir"],
        plot_keys=PLOT_KEYS,
        plot_extensions=PLOT_EXTENSIONS,
        config=config
    script:
        "python_scripts/plotting.py"

rule report:
    input:
        template="defaults/report.md",
        plot_list='results/plots/plot_list.txt',
    output:
        md="results/ww_report.md",
        html="results/ww_report.html",
    shell:
        """
        python3 python_scripts/report.py --template {input.template} \
        -md {output.md} \
        -html {output.html} \
        """

rule md_to_pdf:
    container:
        "docker://pandoc/latex:latest-ubuntu"
    input:
        md="results/ww_report.md"
    output:
        pdf="results/ww_report.pdf"
    shell:
        """
        pandoc {input} \
        -V geometry:margin=.3in \
         -o {output} --resource-path=results/plots
        """

rule final_qc:
    input:
        pre_qc_report='results/qc/pre_qc_report.txt',
        metadata_qc_report='results/qc/metadata_qc_raw.txt',
        lineage_mapping_qc_report='results/qc/lineage_mapping_qc_report.txt',
        weighted_props_qc_report='results/qc/weighted_proportions_qc_report.txt'
    output:
        full_qc_report='results/full_qc_report.txt'
    shell:
        """
        cat {input.pre_qc_report} \
        {input.metadata_qc_report} \
        {input.lineage_mapping_qc_report} \
        {input.weighted_props_qc_report} \
        > {output.full_qc_report}
        """

ruleorder:  pre_qc > merge_data > metadata_qc_raw > add_site_and_classifications > variant_lineage_mapping_qc > add_population_weights > add_county_weights > pop_weighted_proportions_qc > filter_by_timeframe > weekly_county_report > plots > report > md_to_pdf > final_qc