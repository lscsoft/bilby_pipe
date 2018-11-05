import jinja2
import os


def create_summary_page(dag):
    """ Generates the HTML summary page

    The summary page is generated from a Jinja2 template matching the
    executable filename in bilby_pipe/templates.

    Parameters
    ----------
    dag: bilby_pipe.main.Dag
        A dag object containing the `inputs` data and `jobs_outputs`


    """
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates_dir))

    template = '{}.html'.format('basic_template')

    try:
        template = env.get_template(template)
    except jinja2.TemplateNotFound as e:
        raise ValueError("Unable to generate a summary page: {}".format(e))

    filename = os.path.join(dag.inputs.outdir, 'summary.html')
    with open(filename, 'w') as fh:
        fh.write(template.render(jobs=dag.jobs_outputs, inputs=dag.inputs))
