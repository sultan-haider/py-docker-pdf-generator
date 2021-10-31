#! /usr/bin/env python
"""
    WSGI APP to convert wkhtmltopdf As a webservice

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import json
import tempfile
import subprocess
from urllib.request import urlopen
from werkzeug.wrappers import Request, Response
from executor import execute
import boto3
import logging


def get_s3_client(a_key, s_key, reg):
    return boto3.client('s3', aws_access_key_id=a_key,
                        aws_secret_access_key=s_key,
                        region_name=reg)


def generic_upload_file(fil_name, bucket, output_filename, a_key, s_key, reg, content_type='application/pdf'):
    # If S3 object_name was not specified, use file_name
    # Upload the file
    s3_client = get_s3_client(a_key, s_key, reg)
    try:
        response = s3_client.upload_file(fil_name, bucket, output_filename, ExtraArgs={'ContentType': content_type})
        return output_filename

    except Exception as e:
        raise Exception(str(e))


@Request.application
def application(request):
    """
    To use this application, the user must send a POST request with
    base64 or form encoded encoded HTML content and the wkhtmltopdf Options in
    request data, with keys 'base64_html' and 'options'.
    The application will return a response with the PDF file.
    """
    print(request)
    if request.method == 'GET':
        return Response({}, 200, content_type="application/json")

    if request.method != 'POST':
        return
    request_is_json = request.content_type.endswith('json')

    with tempfile.NamedTemporaryFile(suffix='.html') as source_file:
        options = {}
        if request_is_json:
            # If a JSON payload is there, all data is in the payload
            payload = json.loads(request.data)
            if payload['api_key'] != 'KIA26KFGWE9G1MSQETTZG':
                return
            html_file = urlopen(payload['file'])
            source_file.write(html_file.read())
            options = payload.get('options', {})
        elif request.files:
            # First check if any files were uploaded
            source_file.write(request.files['file'].read())
            # Load any options that may have been provided in options
            options = json.loads(request.form.get('options', '{}'))

        source_file.flush()

        # Evaluate argument to run with subprocess
        args = ['/usr/bin/xvfb-run', 'wkhtmltopdf']

        # Add Global Options
        if options:
            for option, value in options.items():
                args.append('--%s' % option)
                if option == 'header-html':
                    subprocess.call(["wget", value, "-O", "/tmp/header.html"])
                    value = "/tmp/header.html"

                if option == 'footer-html':
                    subprocess.call(["wget", value, "-O", "/tmp/footer.html"])
                    value = "/tmp/footer.html"

                if value:
                    args.append('"%s"' % value)

        # Add source file name and output file name
        file_name = source_file.name
        args += [file_name, file_name + ".pdf"]
        # Execute the command using executor
        execute(' '.join(args))
        print(source_file.name)
        uploaded_pdf = generic_upload_file(file_name + '.pdf', payload['bucket'], payload['output_filename'],
                                           payload['a_key'],
                                           payload['s_key'], payload['reg'])
        # return Response({"pdf_url": uploaded_pdf}, content_type='application/json')
        return Response(json.dumps({"pdf_url": uploaded_pdf}), 200, content_type="application/json")


if __name__ == '__main__':
    from werkzeug.serving import run_simple

    run_simple(
        '127.0.0.1', 15000, application, use_debugger=True, use_reloader=True
    )
