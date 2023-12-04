import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

def setup_log_file():
	# find logging directory
	script_directory = os.path.dirname(os.path.abspath(__file__))
	project_directory = os.path.dirname(script_directory)
	log_directory = os.path.join(project_directory, 'logs')
	os.makedirs(log_directory, exist_ok=True)

	# setup logging handler
	current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	log_file_name = os.path.join(log_directory, f"log_{current_datetime}.txt")
	handler = RotatingFileHandler(log_file_name, maxBytes=1000000, backupCount=5)

	# Get the root logger and add the handler
	logger = logging.getLogger()
	logger.addHandler(handler)
	logger.setLevel(logging.INFO)
	

def log_big_separator(logger, message):
    logger.info("\n----------------------")
    logger.info(message)
    logger.info("----------------------\n")

def log_small_separator(logger, message):
    logger.info("\n----------------------")
    logger.info(message+"\n")
    
