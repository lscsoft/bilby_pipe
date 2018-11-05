import jinja2
import os
import bilby


def create_summary_page(dag):
    """ Generates the HTML summary page

    The summary page is generated from a Jinja2 template matching the
    executable filename in bilby_pipe/templates.

    Parameters
    ----------
    dag: bilby_pipe.main.Dag
        A dag object containing the `inputs` data and `jobs_labels`


    """
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_dir))

    template = '{}.html'.format('summary_template')

    try:
        template = env.get_template(template)
    except jinja2.TemplateNotFound as e:
        raise ValueError("Unable to generate a summary page: {}".format(e))

    filename = os.path.join(dag.inputs.outdir, 'summary.html')
    with open(filename, 'w') as fh:
        fh.write(template.render(inputs=dag.inputs,
                                 results_pages=dag.results_pages))


def create_run_output(result):

    corner_plot = '{}_corner.png'.format(result.label)
    oneD_table = {}
    oneD_figures = {}
    for key in result.search_parameter_keys:
        summary = result.get_one_dimensional_median_and_error_bar(key)
        oneD_table[key] = ('{} &plusmn ({}, {})'
                           .format(summary.median, summary.minus,
                                   summary.plus))
        oneD_figures[key] = '{}_{}.png'.format(result.label, key)

    result.plot_marginals()
    result.plot_corner()

    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_dir))

    template = '{}.html'.format('run_template')

    try:
        template = env.get_template(template)
    except jinja2.TemplateNotFound as e:
        raise ValueError("Unable to generate a summary page: {}".format(e))

    filename = os.path.join(result.outdir, '{}.html'.format(result.label))
    with open(filename, 'w') as fh:
        fh.write(template.render(
            label=result.label, corner_plot=corner_plot, oneD_table=oneD_table,
            oneD_figures=oneD_figures, title=result.label,
            parameter_keys=result.search_parameter_keys))
