from gologin import GoLogin
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from config.tokens import gologin_tokens

############################################################################
# Start GoLogin-profile browser and setup remote control
############################################################################

'''
Gologin provides browser profile instance that utilize proxies and unique 
fingerprints in order to hide the underlying browser instance untrackable.
'''

def _provide_gl_browser_profile():

    # Generate a random port within the privat port range
    random_client_port = random.randint(49152, 65535)

    token = gologin_tokens['token']
    profile_id_list = gologin_tokens['profile_id_list']
    random_profile_id = random.choice(profile_id_list)

    gl = GoLogin({
        "token": token,
        "profile_id": random_profile_id,
        "port": random_client_port 
        })

    return gl 


def start_remote_debug_gologin_browser():

    # start gologin-profile-browser as a remote debugging instance
    gl = _provide_gl_browser_profile()
    debugger_address = gl.start()

    # setup remote control with chrome driver
    options = Options()
    options.add_experimental_option("debuggerAddress", debugger_address)
    exe_path = r'''webdriver/chromedriver.exe'''
    service = Service(executable_path=exe_path)

    return webdriver.Chrome(service= service,  options=options), gl