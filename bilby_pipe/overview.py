#!/usr/bin/env python
"""
Module to create a lightweight overview page for a run
"""
from os.path import abspath, relpath

from jinja2 import Template

from .utils import logger


def create_overview(
    inputs, generation_node_list, parallel_node_list, merged_node_list, plot_node_list
):
    """ Create an overview.html page to see the progress of jobs

    Parameters
    ----------
    inputs: bilby_pipe.inputs.Input
        The main set of inputs
    generation_node_list: list
        List of generation node jobs
    parallel_node_list: list
        List of parallel (analysis) node jobs
    merged_node_list: list
        List of merge node jobs
    plot_node_list: list
        List of plot node jobs

    """

    index_file_dir = inputs.webdir
    index_file = "{}/overview.html".format(index_file_dir)
    template = Template(string_template)

    if inputs.injection_waveform_approximant is None:
        inputs.injection_waveform_approximant = inputs.waveform_approximant
    if inputs.injection_file:
        injection_file = abspath(inputs.injection_file)
    else:
        injection_file = None

    if inputs.trigger_time is not None:
        priors = inputs.priors
    else:
        # If a trigger time doesn't exist, the geocent time prior isn't defined
        priors = inputs._get_priors(add_geocent_time=False)

    if inputs.prior_file is not None:
        prior_file = (abspath(inputs.prior_file),)
    else:
        prior_file = "Specified in INI"

    filled_template = template.render(
        inputs=inputs,
        priors=priors,
        config_file=abspath(inputs.ini),
        config_dict=vars(inputs.known_args),
        prior_file=prior_file,
        injection_file=injection_file,
        data_directory=relpath(inputs.data_directory, index_file_dir),
        result_directory=relpath(inputs.result_directory, index_file_dir),
        result_directory_abs=abspath(inputs.result_directory),
        generation_node_list=generation_node_list,
        parallel_node_list=parallel_node_list,
        merged_node_list=merged_node_list,
        plot_node_list=plot_node_list,
        webdir=relpath(inputs.webdir, index_file_dir),
        generation_log_directory=relpath(
            inputs.data_generation_log_directory, index_file_dir
        ),
        analysis_log_directory=relpath(
            inputs.data_analysis_log_directory, index_file_dir
        ),
        summary_log_directory=relpath(inputs.summary_log_directory, index_file_dir),
    )
    with open(index_file, "w+") as f:
        print(filled_template, file=f)
    logger.info("Overview page available at {}".format(index_file))


string_template = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
</head>

<style>

body {
    padding-bottom: 50px;
}

table {
  font-family: arial, sans-serif;
  border-collapse: collapse;
  width: 100%;
}
td, th {
  border: 1px solid #dddddd;
  text-align: left;
  padding: 8px;
}

tr:nth-child(even) {
    background-color: #dddddd;
}

.accordion {
    background-color: #eee;
    color: #444;
    cursor: pointer;
    padding: 2px;
    width: 100%;
    text-align: left;
    border: none;
    outline: none;
    transition: 0.4s;
}

.active, .accordion:hover {
    background-color: #ccc;
}

.panel {
    padding: 0 8px;
    background-color: white;
    display: none;
}

.alignleft {
        float: left;
}
.alignright {
        float: right;
}
</style>

<div class="container">
<h1> Overview page for label: {{ inputs.label }} </h1>
</div>

<div class="container">
<h2> Setup </h2>

<button class="accordion"> <b>Configuration file:</b> {{ config_file }} </button>
<div class="panel">
<table style="width:100%">
{% for key, val in config_dict.items() %}
<tr>
    <th scope="row"> {{ key }} </th>
   <td> {{ val }} </td>
</tr>
{% endfor %}
</table>
</div>

<button class="accordion"> <b>Prior file:</b> {{ prior_file }} </button>
<div class="panel">
<table style="width:100%">
{% for key, val in priors.items() %}
<tr>
    <th scope="row"> {{ key }} </th>
   <td> {{ val }} </td>
</tr>
{% endfor %}
</table>
</div>

{% if inputs.injection %}
<button class="accordion"> <b>Injection-waveform:</b> {{ inputs.injection_waveform_approximant }},
<b>File:</b> {{ injection_file }} </button>
<div class="panel">
<table style="width:100%">
{{ inputs.injection_df.to_html() }}
</table>
{% endif %}

</div>
</div>

{% for generation_node in generation_node_list %}
<div class="container">
<h2> Data: {{ generation_node.label }} </h2>

<button class="accordion"> <b>Log file</b>:
{{ generation_log_directory }}/{{ generation_node.label }}.err </button>
<div class="panel">
<object data="{{ generation_log_directory }}/{{ generation_node.label }}.err" width=100% height="200">
N/A
</object>
</div>

{% if inputs.create_plots %}
<button class="accordion"> <b>Data plots</b> </button>
<div class="panel">
<table style="width:100%">
<tr>
{% for det in generation_node.inputs.detectors %}
   <th> {{ det }} </th>
{% endfor %}
</tr>
<tr>
{% for det in generation_node.inputs.detectors %}
   <td><img src="{{ data_directory }}/{{ det }}_{{ generation_node.label }}_frequency_domain_data.png" width=100%></td>
{% endfor %}
</tr>
</table>
</div>
{% endif %}
</div>
{% endfor %}

{% for parallel_node in parallel_node_list %}
<div class="container">
<h2> Parallel Analysis: {{ parallel_node.label }} </h2>

{% if inputs.create_plots %}
<button class="accordion"> <b>Trace plots</b> </button>
<div class="panel">
   <td><img src="{{ result_directory }}/{{ parallel_node.label }}_checkpoint_trace.png" width=100%></td>
</div>
{% endif %}

<button class="accordion"> <b>Log file</b>:
{{ analysis_log_directory }}/{{ parallel_node.label }}.err </button>
<div class="panel">
<object data="{{ analysis_log_directory }}/{{ parallel_node.label }}.err" width=100% height="200">
N/A
</object>
</div>

<button class="accordion"> <b>Output file</b>:
{{ analysis_log_directory }}/{{ parallel_node.label }}.out </button>
<div class="panel">
<object data="{{ analysis_log_directory }}/{{ parallel_node.label }}.out" width=100% height="200">
N/A
</object>
</div>

</div>
{% endfor %}

<div class="container">
<h2> Other log files: </h2>

{% for merged_node in merged_node_list %}
<button class="accordion"> <b>Log file</b>:
{{ analysis_log_directory }}/{{ merged_node.label }}.err </button>
<div class="panel">
<object data="{{ analysis_log_directory }}/{{ merged_node.label }}.err" width=100% height="200">
N/A
</object>
</div>
{% endfor %}

{% for plot_node in plot_node_list %}
<button class="accordion"> <b>Log file</b>:
{{ analysis_log_directory }}/{{ plot_node.label }}.err </button>
<div class="panel">
<object data="{{ analysis_log_directory }}/{{ plot_node.label }}.err" width=100% height="200">
N/A
</object>
</div>
{% endfor %}

</div>

<div class="container">
<h2> Bilby results:
<a href="{{ result_directory }}"> {{ result_directory_abs }} </a>
 </h2>
 </div>

{% if inputs.create_summary %}
<div class="container">
<h2> PESummary:
<a href="{{ webdir }}/home.html"> webdir </a>
 </h2>
<button class="accordion"> <b>Log file</b>:
{{ summary_log_directory }}/{{ inputs.label }}_pesummary.err </button>
<div class="panel">
<object data="{{ summary_log_directory }}/{{ inputs.label }}_pesummary.out" width=100% height="200">
N/A
</object>
</div>
</div>

{% endif %}

<script>
var acc = document.getElementsByClassName("accordion");
var i;

for (i = 0; i < acc.length; i++) {
    acc[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var panel = this.nextElementSibling;
        if (panel.style.display === "block") {
            panel.style.display = "none";
        } else {
            panel.style.display = "block";
        }
    });
}
</script>
"""
