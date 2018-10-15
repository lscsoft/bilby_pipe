from jinja2 import Environment, FileSystemLoader
import os


def create_summary_page(inputs, dag):
    """ Generates the HTML summary page given the jobs list """
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('summary.html')

    filename = os.path.join(inputs.outdir, 'summary.html')
    with open(filename, 'w') as fh:
        fh.write(template.render(jobs=dag.jobs_outputs, inputs=inputs))
