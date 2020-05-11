if __name__ == "__main__":

    import sys

    from os.path import abspath, dirname, join

    path = abspath(join(dirname(__file__), '..'))
    sys.path.insert(1, path)

    from jinja2 import Template

    deployment_id, deployment_group = sys.argv[1:]

    domains = {
    'staging': 'committeeoversight.datamade.us',
    'production': 'oversight-index.thelugarcenter.org',
    }

    nginx_template_path = '/home/datamade/committee-oversight-{0}/configs/committee-oversight-{1}.conf.nginx'.format(
    deployment_id, deployment_group)
    nginx_outpath = '/etc/nginx/conf.d/committee-oversight.conf'

    supervisor_template_path = '/home/datamade/committee-oversight-{0}/configs/committee-oversight-{1}.conf.supervisor'.format(
    deployment_id, deployment_group)
    supervisor_outpath = '/etc/supervisor/conf.d/committee-oversight.conf'

    crontask_template_path = '/home/datamade/committee-oversight-{0}/scripts/committee-oversight-crontasks'.format(deployment_id)
    crontask_outpath = '/etc/cron.d/committee-oversight-crontasks'

    with open(nginx_template_path) as f:
        nginx_conf = Template(f.read())
        context = {
          'deployment_id': deployment_id,
          'domain': domains[deployment_group]
        }
        nginx_rendered = nginx_conf.render(context)

    with open(supervisor_template_path) as f:
        supervisor_conf = Template(f.read())
        supervisor_rendered = supervisor_conf.render(
          {'deployment_id': deployment_id})

    with open(nginx_outpath, 'w') as out:
        out.write(nginx_rendered)

    with open(supervisor_outpath, 'w') as out:
        out.write(supervisor_rendered)

    if deployment_group == 'production':
        with open(crontask_template_path) as f:
            crontask_conf = Template(f.read())
            # Jinja strips trailing whitespace. Configuring it not to takes more
            # work than we want to invest in this approach. Manually add back the
            # trailing whitespace here.
            # https://jinja.palletsprojects.com/en/2.11.x/api/#basics
            contask_rendered = crontask_conf.render(
              {'deployment_id': deployment_id}) + '\n'

        with open(crontask_outpath, 'w') as out:
            out.write(contask_rendered)
