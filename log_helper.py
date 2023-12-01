import os
import time
import pandas as pd
from datetime import datetime
from typing import Dict, List, Union, Tuple
import logging
import gspread
from selenium.webdriver.remote.webdriver import WebDriver
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from helper_classes import BrowserManager, ElementFinder
from config.datastructure import DATACOLOUMNS, DOMAIN_MARKERS
from log_helpers import log_big_separator, log_small_separator

logger = logging.getLogger(__name__)


class GoogleSheetManager:
    '''A class for managing Google Sheets interactions via the Google Sheet API.'''

    def __init__(self, spreadsheet_name: str):
        # get the file path of the credentials_file and start a gspread client
        script_directory = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(script_directory, 'config', 'SA_credentials.json')
        self.client = gspread.service_account(filename=credentials_path)

        self.sheet = self.client.open(spreadsheet_name)

    def get_worksheet_as_dataframe(self, worksheet: gspread.worksheet.Worksheet) -> pd.DataFrame:
        df = get_as_dataframe(worksheet)
        num_cols = len(DATACOLOUMNS)
        df_cleaned_rows = df.dropna(how='all')
        df_cleaned_columns = df_cleaned_rows.iloc[:, :num_cols]
        return df_cleaned_columns

    def update_google_worksheet(self, ws: gspread.worksheet.Worksheet, df: pd.DataFrame):
        ws.clear()
        set_with_dataframe(ws, df)




class JobStorageManager:
    '''A class for managing new and existing job posts and their Google Sheets 
    interactions.'''

    def __init__(self, spreadsheet_name: str):
        self.google_sheet_manager = GoogleSheetManager(spreadsheet_name)
        self.browser_manager = BrowserManager()
    

    def find_inactive_jobposts(self):
        log_big_separator(logger, "FIND INACTIVE JOBPOSTS")
        start_time = time.time()

        def _ensure_authorization_wall_not_encountered(driver: WebDriver, href: str):
            try:
                ElementFinder(driver).find_by_class('authwall-join-form__title')
                driver.get(href)
                _ensure_authorization_wall_not_encountered(driver, href)
            except Exception:
                return


        def _is_jobpost_inactive(driver: WebDriver) -> bool:
            is_jobpost_inactive = 0
            try:
                ele_text = ElementFinder(driver).find_by_xpath(
                    '''//*[@id="main-content"]/section[1]/div/section[2]/div/div[1]/div/h4/figure/figcaption'''
                ).text
                if ele_text in ["No longer accepting applications", 
                                "Modtager ikke længere ansøgninger"]:
                    is_jobpost_inactive = 1
            except Exception:
                pass
            return is_jobpost_inactive

        # verifies that href is still active - if not, the job is marked as inactive
        # also marked inactive if the application deadline have expired 
        for ws_idx, ws in enumerate(self.google_sheet_manager.sheet.worksheets()[1:]):
            continue_loop = True
            while continue_loop:
                time.sleep(1)

                if ws_idx == 0:
                    self.browser_manager.start_browser_session()
                else:
                    # restart browser session between each worksheet for better stability
                    self.browser_manager.restart_browser_session()
            
                df = self.google_sheet_manager.get_worksheet_as_dataframe(ws)
                if len(df) == 0:        # break if no jobpost are present
                    logger.info("Domain completed")
                    break
                for row_idx, row in df.iterrows():
                    try:
                        self.browser_manager.driver.get(row['href'])
                        _ensure_authorization_wall_not_encountered(
                                                self.browser_manager.driver, 
                                                row['href']
                                                )
                        if _is_jobpost_inactive(self.browser_manager.driver):
                            df['is_active'].iloc[row_idx] = 0
                            logger.info("Job inactive")
                    except Exception:
                        # test whether browser session is open
                        try:
                            # if open the jobpost is marked as inactive 
                            self.browser_manager.driver.get("www.openai.com")
                            df['is_active'].iloc[row_idx] = 0
                            logger.info("Job inactive")
                        except:
                            continue_loop = False
                            logger.error("Exception occurred, restarting browser session")
                            break 
                    if (row_idx+1)==len(df):
                        continue_loop = False
                        logger.info("Domain completed")
                        break
            self.google_sheet_manager.update_google_worksheet(ws,df)
        self.browser_manager.stop_browser_session()
        completion_time = start_time - time.time()
        log_small_separator(logger, 
                        f"Inactive check done - completion time {completion_time}")
        return 


    def archive_inactive_jobposts(self):
        log_big_separator(logger, "ARCHIVING INACTIVE JOBPOSTS")
        start_time = time.time()

        sheet_active = self.google_sheet_manager.sheet

        # initialize new job post handler for archived job posts
        job_handler_archive = JobStorageManager(spreadsheet_name = 'Job_radar_inaktiv')

        # archive new, inactive jobposts
        for ws_idx, ws_ina in enumerate(
            job_handler_archive.google_sheet_manager.sheet.worksheets()[1:]):

            ws_a = sheet_active.worksheets()[ws_idx+1]
            df_active = self.google_sheet_manager.get_worksheet_as_dataframe(ws_a)

            # filter out row with IDs not present in new dataset and IDs of already archived files 
            df_archive = \
                job_handler_archive.google_sheet_manager.get_worksheet_as_dataframe(
                                                                            ws_ina
                                                                            )
            archived_id_list = df_archive['id'].tolist()
            df_inactive = df_active[(df_active['is_active'] == 0) | 
                                     df_active['id'].isin(archived_id_list)]

            # update the archive
            df_archive_updated = job_handler_archive.update_existing_dataframe(
                                                                    df_archive, 
                                                                    df_inactive
                                                                    )
            job_handler_archive.google_sheet_manager.update_google_worksheet(
                                                                ws_ina, 
                                                                df_archive_updated
                                                                )

            # delete archived rows from the active worksheet
            updated_archived_id_list = df_archive_updated['id'].tolist()
            df_active = df_active[~df_active['id'].isin(updated_archived_id_list)]
            self.google_sheet_manager.update_google_worksheet(ws_a, df_active)
        completion_time = start_time - time.time()
        log_small_separator(logger, 
                        f"Archiving done - completion time {completion_time}")



    def update_existing_dataframe(self, df_old: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
        
        df_new['id'] = df_new['id'].astype('Int64')
        df_old['id'] = df_old['id'].astype('Int64')

        # Combine the dateframes using 'id' as index
        df_new.set_index('id', inplace=True)
        df_old.set_index('id', inplace=True)
        df_updated = df_old.combine_first(df_new)

        return df_updated.reset_index()



    def store_new_jobposts(self, df_new: pd.DataFrame, ws_idx: int):
        log_small_separator(logger, f"Storing new jobposts - domain: {ws_idx}")

        worksheet = self.google_sheet_manager.sheet.worksheets()[ws_idx]

        # loading existing jobposts and merge with new jobposts
        df_existing = self.google_sheet_manager.get_worksheet_as_dataframe(worksheet)
        if df_existing.shape[0] > 0:
            df_updated = self.update_existing_dataframe(df_existing, df_new)
        else:
            df_updated = df_new

        self.google_sheet_manager.update_google_worksheet(worksheet, df_updated)
        return







class JobPostOrganizer:
    '''A class for organizing and reorganizing job posts within a Google Sheet.'''
    def __init__(self, spreadsheet_name: str):
        self.google_sheet_manager = GoogleSheetManager(spreadsheet_name)

    def determine_df_destination_indices(self, 
                                         df_source: pd.DataFrame, 
                                         df_source_idx: int) -> pd.DataFrame:
        
        # find out if any job post belong to another dataframe
        df_destination = [
            0 if (any(keyword in title for keyword in DOMAIN_MARKERS[0][0])) else
            1 if any(keyword in title for keyword in DOMAIN_MARKERS[1][0]) else
            2 if (any(keyword in title for keyword in DOMAIN_MARKERS[2][0]) and 
                    any(keyword not in title for keyword in DOMAIN_MARKERS[2][1])) else
            3 if any(keyword in title for keyword in DOMAIN_MARKERS[3][0]) else
            4 if (any(keyword in title for keyword in DOMAIN_MARKERS[4][0]) and 
                    any(keyword not in title for keyword in DOMAIN_MARKERS[4][1])) else
            5 if any(keyword in title for keyword in DOMAIN_MARKERS[5][0]) else
            df_source_idx
            for title in df_source['jobpost_title']
        ]
        return df_destination 


    def move_jobposts(self, df_all_domains_list: List[pd.DataFrame]) -> List[pd.DataFrame]:
        for df_source_idx, df_source in enumerate(df_all_domains_list):

            # find out if any jobpost belong to another dataframe
            df_dest_idx_list = self.determine_df_destination_indices(df_source,df_source_idx)

            # move any wrong placed jobposts and remove from source df
            for row_idx, row in df_source.iterrows():
                df_dest = df_all_domains_list[df_dest_idx_list[row_idx]]
                if df_source_idx != df_dest_idx_list[row_idx] and row['id'] not in df_dest['id'].tolist():
                    logger.info("\nJobpost moved\n")
                    row['jobpost_title'] += " - [moved]"
                    df_all_domains_list[df_dest_idx_list[row_idx]] = \
                        pd.concat([df_dest, pd.DataFrame([row])], ignore_index=True)
                    df_all_domains_list[df_source_idx] = df_source.drop(row_idx).reset_index(drop=True)
        return df_all_domains_list


    def remove_duplicates(self, df_all_domains_list: List[pd.DataFrame]) -> List[pd.DataFrame]:
        all_ids_list = [id_val for df in df_all_domains_list for id_val in df['id']]

        df_all_domains_list_updated = []
        for df_domain in df_all_domains_list:
            for row_idx, row in df_domain.iterrows():
                if (all_ids_list.count(row['id']) > 1) and (" - [moved]" not in row['jobpost_title']):
                    logger.info("\nDuplicate removed\n")
                    df_domain = df_domain.drop(row_idx)
            df_all_domains_list_updated.append(df_domain)
        return df_all_domains_list_updated



    def reorganize_jobposts(self):
        '''
        Moves jobposts between the domaines (dataframes) according to rules defined 
        in a set of domain markers which indicate which domain each job post belong
        to. 
        '''
        log_big_separator(logger, "REORGANIZING JOBPOSTS")
        start_time = time.time()

        df_all_domains_list = [self.google_sheet_manager.get_worksheet_as_dataframe(ws) 
                               for ws 
                               in self.google_sheet_manager.sheet.worksheets()[1:]]

        df_all_domains_list_updated = self.move_jobposts(df_all_domains_list)
        df_all_domains_list_updated = self.remove_duplicates(df_all_domains_list)

        for domain_idx, df_domain in enumerate(df_all_domains_list_updated):
            ws = self.google_sheet_manager.sheet.worksheets()[domain_idx+1]
            self.google_sheet_manager.update_google_worksheet(ws,df_domain)

        completion_time = start_time - time.time()
        log_small_separator(logger, 
                        f"Reorganizing done - completion time {completion_time}")
        return
    