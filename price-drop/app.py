import logging
from flask import Flask

from src.routes import api
from src.scheduler import start_scheduler
from src.logs import log_to_file

app = Flask(__name__, template_folder='templates')
app.register_blueprint(api)

log = logging.getLogger('werkzeug')


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return '/health' not in record.getMessage()


log.addFilter(HealthCheckFilter())

start_scheduler()


if __name__ == '__main__':
    log_to_file("================================ Flask Service Status: Started ================================")
    app.run(host='0.0.0.0', port=5000, debug=False)
