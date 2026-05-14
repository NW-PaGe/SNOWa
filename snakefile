configfile: os.path.join(workflow.basedir, "defaults/config.yaml")
containerized: config["containerized"]
from datetime import date
from glob import glob

rule all:
    input:
        'results/full_qc_report.txt',
        "ww_report.pdf"

rule pre_qc:
    output: 
        qc="results/qc/pre_qc_report.txt"
    params: 
        copy_runs=config["pre_qc"]["copy_runs"],
        directory=config["pre_qc"]["directory"]
        # The directory info would go here, as a parameter rather than an input.
        # snakemake can't take directories as inputs (above), so this is a workaround.
        # you can use checkpoints, but it's kind of complicated and I'm not sure the juice is worth the squeeze
    shell:
        """
        mkdir -p results/qc
        echo $'{params.copy_runs}' | python3 python_scripts/pre_qc.py \
            --directory {params.directory} # this has to be pointed to params (above)
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
        log="results/metadata_qc_raw.txt"
    shell:
        """
        python3 python_scripts/metadata_qc_raw.py --input {input.data} --output-csv {output.csv} --output-txt {output.log}
        """

rule add_site_and_classifications:
    input:
        data="results/combined_output.csv",
        sites="defaults/sample_site-counties.csv",
        classifications="defaults/ww_lineage_classifications.csv"
    output: 'results/ww_data.csv'
    shell:
        """
        python3 python_scripts/add_site_and_classifications.py
        """

rule variant_lineage_mapping_qc:
    input:
        data="results/ww_data.csv"
    output: 
        qc="results/qc/lineage_mapping_qc_report.txt"
    shell:
        """
        python3 python_scripts/check_variant_lineage_mapping.py {input.data} > {output.qc}
        """

rule add_population_weights:
    input:
        data="results/ww_data.csv"
    output:
        data="results/population_weighted_props.csv"
    shell:
        """
        python3 python_scripts/add_population_weights.py {input.data} -o {output.data}
        """

rule add_county_weights:
    input:
        data="results/ww_data.csv"
    output:
        data="results/county_weighted_proportions.csv"
    shell:
        """
        python3 python_scripts/add_county_weights.py {input.data} -o {output.data}
        """

rule pop_weighted_proportions_qc:
    input:
        state="results/population_weighted_props.csv",
        county="results/county_weighted_proportions.csv"
    output:
        qc="results/qc/weighted_proportions_qc_report.txt"
    shell:
        """
        python3 python_scripts/pop_weights_qc.py --county {input.county} --state {input.state} > {output.qc}
        """

rule plots:
    input:
        weighted_props="results/population_weighted_props.csv",
        ww_data="results/ww_data.csv"
    output:
        plot_list='results/plots/plot_list.txt'
    params:
        plot_dir=config['plots']['plot_dir']
    shell:
        """
        mkdir -p {params.plot_dir}
        python3 python_scripts/plots.py \
        --dataset {input.ww_data} \
        --proportions {input.weighted_props} \
        --barplot "{params.plot_dir}barplot.jpeg" \
        --timeline "{params.plot_dir}timeline.jpeg" \
        --top3 "{params.plot_dir}top3.jpeg" \
        --heatmap "{params.plot_dir}heatmap.jpeg" \
        --n-weeks-map "{params.plot_dir}n_weeks_map"
        touch {params.plot_dir}plot_list.txt && ls -1 {params.plot_dir} > {params.plot_dir}plot_list.txt
        """

rule report:
    input:
        template="defaults/sc2-ww-template.md",
        plot_list='results/plots/plot_list.txt',
    output:
        md="ww_report.md",
        html="ww_report.html",
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
        md="ww_report.md"
    output:
        pdf="ww_report.pdf"
    shell:
        """
        pandoc {input} \
        -V geometry:margin=.3in \
         -o {output} --resource-path=results/plots
        """

rule final_qc:
    input:
        pre_qc_report='results/qc/pre_qc_report.txt',
        lineage_mapping_qc_report='results/qc/lineage_mapping_qc_report.txt',
        weighted_props_qc_report='results/qc/weighted_proportions_qc_report.txt'
    output:
        full_qc_report='results/full_qc_report.txt'
    shell:
        """
        cat {input.pre_qc_report} \
        {input.lineage_mapping_qc_report} \
        {input.weighted_props_qc_report} \
        > {output.full_qc_report}
        """
