from multiprocessing import cpu_count
from pathlib import Path

bind = "0.0.0.0:8000"

# Worker Options
workers = cpu_count() + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Logging Options
loglevel = "debug"
accesslog = str((Path(__file__).parent / "access_log").absolute())
errorlog = str((Path(__file__).parent / "error_log").absolute())
