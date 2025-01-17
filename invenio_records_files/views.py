# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio-Records-Files REST integration."""

from __future__ import absolute_import, print_function

from flask import Blueprint, abort, g, request
from invenio_files_rest.views import bucket_view, object_view
from six import iteritems
from six.moves.urllib.parse import urljoin

from invenio_records_files.models import RecordsBuckets


def create_blueprint_from_app(app):
    """Create Invenio-Records-Files blueprint from a Flask application.

    :params app: A Flask application.
    :returns: Configured blueprint.
    """
    records_files_blueprint = Blueprint(
        'invenio_records_files',
        __name__,
        url_prefix='')

    for config_name, endpoints_to_register in \
            iteritems(app.config['RECORDS_FILES_REST_ENDPOINTS']):
        for endpoint_to_register in endpoints_to_register:
            record_item_path = \
                app.config[config_name][endpoint_to_register]['item_route']
            files_resource_endpoint_suffix = \
                endpoints_to_register[endpoint_to_register]
            files_resource_endpoint_suffix = \
                urljoin('/', files_resource_endpoint_suffix)
            records_files_blueprint.add_url_rule(
                '{record_item_path}{files_resource_endpoint_suffix}'
                .format(**locals()),
                view_func=bucket_view,
            )
            records_files_blueprint.add_url_rule(
                '{record_item_path}{files_resource_endpoint_suffix}/<path:key>'
                .format(**locals()),
                view_func=object_view,
            )

    @records_files_blueprint.url_value_preprocessor
    def resolve_pid_to_bucket_id(endpoint, values):
        """Flask URL preprocessor to resolve pid to Bucket ID.

        In the ``records_files_blueprint`` we are gluing together Records-REST
        and Files-REST APIs. Records-REST knows about PIDs but Files-REST does
        not, this function will pre-process the URL so the PID is removed from
        the URL and resolved to bucket ID which is injected into Files-REST
        view calls:
        /api/<record_type>/<pid_value>/files/<key> -> /files/<bucket>/<key>.
        """
        # We are removing the value since we need the request values to include
        # only the ones contained in the view signature.
        g.pid = values.pop('pid_value')
        pid, record = g.pid.data
        try:
            # Check if the Record class has the property of files.
            files = record.files
        except AttributeError:
            abort(404)
        if files is not None:
            values['bucket_id'] = str(record.resolve_files_to_bucket_id(files))
        else:
            abort(404)

    @records_files_blueprint.url_defaults
    def restore_pid_to_url(endpoint, values):
        """Put ``pid_value`` back to the URL after matching Files-REST views.

        Since we are computing the URL more than one times, we need the
        original values of the request to be unchanged so that it can be
        reproduced.
        """
        values['pid_value'] = g.pid

    return records_files_blueprint
