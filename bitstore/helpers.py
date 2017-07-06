import logging


def generate_s3_path(inpath, format_params):
    if ('{owner}' in inpath and not format_params.get('owner', None)):
        logging.error('Following format variable is not available: owner')
        raise KeyError
    if ('{name}' in inpath and not format_params.get('name', None)):
        logging.error('Following format variable is not available: name')
        raise KeyError

    # For easier formatting (as filedata has "name" key as well)
    inpath = inpath.replace('{name}', '{dataset_name}')
    try:
        upload_url = inpath.format(**format_params)
    except KeyError as e:
        logging.error('Following format variable is not available: %s' % e)
        raise

    return upload_url
