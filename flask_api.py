#!/usr/bin/env python3

import logging
import os
import re

from flask import Flask, make_response, jsonify, abort

from playstore.playstore import Playstore

if "LOG_LEVEL" in os.environ:
    log_level = os.environ["LOG_LEVEL"]
else:
    log_level = logging.INFO

# Logging configuration.
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s> [%(levelname)s][%(name)s][%(funcName)s()] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    level=log_level,
)
logging.getLogger("werkzeug").disabled = True

# Directory where to save the downloaded applications.
downloaded_apk_location = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "Downloads"
)

# https://developer.android.com/guide/topics/manifest/manifest-element#package
package_name_regex = re.compile(
    r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$", flags=re.IGNORECASE
)


def create_app():
    app = Flask(__name__)
    # Create the download directory (if not already existing).
    if not os.path.isdir(downloaded_apk_location):
        os.makedirs(downloaded_apk_location)
    return app


application = create_app()

@application.errorhandler(500)
def application_error(error):
    logger.error(error)
    return make_response(jsonify(str(error)), error.code)


@application.route("/download/<package_name>", methods=["GET"], strict_slashes=False)
def download(package_name):
    if package_name_regex.match(package_name):
        try:
            api = Playstore("", True)
            try:
                app = api.app_details(package_name).docV2
            except AttributeError:
                logger.error(
                    f"Unable to retrieve application with "
                    f"package name '{package_name}'",
                )
                return jsonify({
                    "package": package_name,
                    "status": "not valid"
                }), 400

            details = {
                "package_name": app.docid,
                "title": app.title,
                "creator": app.creator,
                "version_code": app.details.appDetails.versionCode,
                "version": app.details.appDetails.versionString,
            }
            filename = "%s_%s(%s).apk" % (details['package_name'], details['version'], details['version_code'])
            downloaded_apk_file_path = os.path.join(
                downloaded_apk_location,
                filename,
            )

            success = api.download(
                details["package_name"],
                downloaded_apk_file_path,
                False,
                False,
                False
            )

            if not success:
                logger.critical(f"Error when downloading '{details['package_name']}'")
                return jsonify({
                    "package": package_name,
                    "status": "Error when downloading"
                }), 400

            return {
                "package": details['package_name'],
                "filename": filename,
                "version": details['version'],
                "version_code": details['version_code']
            }

        except Exception as e:
            logger.critical(f"Error during the download: {e}")
            abort(500)
    else:
        logger.critical("Please specify a valid package name")
        abort(400, description='Not valid package')

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000)