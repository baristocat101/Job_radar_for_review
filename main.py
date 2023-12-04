from datetime import datetime
import logging
from scrape_jobposts import scrape_and_store_new_jobposts
from manage_jobposts import JobStorageManager, JobPostOrganizer
from rate_jobposts import rate_all_jobpost, check_for_cool_jobs
from send_mail import send_mail_with_notification
from log_helpers import setup_log_file


def main():
	
	setup_log_file()
	logging.info(f'Job radar started: {datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}')

	############################################################################
	# Scrape and store new, relevant job posts
	############################################################################

	scrape_and_store_new_jobposts()

	############################################################################
	# Archiving inactive jobposts and reorganize remaining jobposts
	############################################################################

	
	job_storage_manager = JobStorageManager(spreadsheet_name="Job_radar_aktiv")
	job_storage_manager.find_inactive_jobposts()
	job_storage_manager.archive_inactive_jobposts()

	JobPostOrganizer(spreadsheet_name="Job_radar_aktiv").reorganize_jobposts()
   
	############################################################################
	# Analyze and rate stored job posts
	############################################################################

	rate_all_jobpost()

	############################################################################
	# Notify by email if cool jobs appears
	############################################################################

	cool_job_list = check_for_cool_jobs(cool_score=50)
	if cool_job_list:
		send_mail_with_notification(cool_job_list)
	
	logging.info("Job radar end")





if __name__=="__main__":
	main()
	
