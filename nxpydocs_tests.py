import os
import logging
import json
import re
import requests
from github import Github
from pyats import aetest
from pyats.log.utils import banner
from tabulate import tabulate
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("USERNAME")
TOKEN = os.getenv("TOKEN")
REPO_NAME = os.getenv("REPO_NAME")
WEBEX_ROOM = os.getenv("WEBEX_ROOM")
WEBEX_TOKEN = os.getenv("WEBEX_TOKEN")

# Get your logger for your script
log = logging.getLogger(__name__)

###################################################################
#                  COMMON SETUP SECTION                           #
###################################################################

class common_setup(aetest.CommonSetup):
    """ Common Setup section """

    ###
    # Get JSON from Github repository
    ###
    @aetest.subsection
    def get_hostname(self):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        hostname_list = []
        for item in repo.get_contents("JSON"):
            hostname = (re.sub('\s(.*)','',item.name))
            hostname_list.append(hostname)
        self.hostname = set(hostname_list)
        return(self.hostname)

    @aetest.subsection
    def get_show_version(hostname):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        for item in repo.get_contents("JSON"):
            raw_json_content = item.decoded_content
            if f"{ hostname } show version" in item.name:
                show_version = raw_json_content
                return(show_version)

    @aetest.subsection
    def get_show_system_resources(hostname):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        for item in repo.get_contents("JSON"):
            raw_json_content = item.decoded_content
            if f"{ hostname } show system resource" in item.name:
                show_system_resources = raw_json_content
                return(show_system_resources)

    @aetest.subsection
    def get_show_interface(hostname):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        for item in repo.get_contents("JSON"):
            raw_json_content = item.decoded_content
            if f"{ hostname } show interface" in item.name:
                show_interface = raw_json_content
                return(show_interface)

    @aetest.subsection
    def get_dir(hostname):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        for item in repo.get_contents("JSON"):
            raw_json_content = item.decoded_content
            if f"{ hostname } dir" in item.name:
                dir = raw_json_content
                return(dir)

###################################################################
#                     TESTCASES SECTION                           #
###################################################################
class Version_Check(aetest.Testcase):
    @aetest.setup
    def setup(self):
        self.list_of_hostnames = common_setup.get_hostname(self)
    # Test for NXOS Version
    @aetest.test
    def nxos_version(self, nxos_version_threshold = "9.3(8)"):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.version_info = common_setup.get_show_version(hostname)
            self.failed_nxos_version = {}
            json_version = json.loads(self.version_info)
            self.version = json_version['nxos_ver_str']
            if self.version:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.version)
                if self.version != nxos_version_threshold:
                    table_row.append('Failed')
                    self.failed_nxos_version = self.version
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_nxos_version_webex()                    
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','NXOS Version',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_nxos_version:
            self.failed_nxos_version_check()
            self.failed('One or more of the NXOS versions does not match the golden version')
        else:
            self.passed('All NXOS Version matches golden version')
 
    @aetest.test
    def failed_nxos_version_check(self, nxos_version_threshold = "9.3(8)"):
        if self.version == nxos_version_threshold:
            self.skipped('All Versions match the golden version')
        else:
            self.failed(f'One or more of the NXOS version is { self.version } (threshold { nxos_version_threshold }')

    def failed_nxos_version_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_version_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, version=self.version, test="nxos")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # Test for kickstart version
    @aetest.test
    def kickstart_version(self, kickstart_version_threshold = "9.3(8)"):
        table_data = []
        for hostname in self.list_of_hostnames:        
            self.version_info = common_setup.get_show_version(hostname)
            self.failed_kickstart_version = {}
            json_version = json.loads(self.version_info)
            self.version = json_version['kickstart_ver_str']
            if self.version:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.version)
                if self.version != kickstart_version_threshold:
                    table_row.append('Failed')
                    self.failed_kickstart_version = self.version
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_kickstart_version_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(self.hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
            
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','Kickstart Version',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_kickstart_version:
            self.failed_kickstart_version_check()
            self.failed('One or more of the NXOS kickstart version does not match the golden version')
        else:
            self.passed('All Kickstart Version matches golden version')
 
    @aetest.test
    def failed_kickstart_version_check(self, kickstart_version_threshold = "9.3(8)"):
        if self.version == kickstart_version_threshold:
            self.skipped('All kickstart versions match the golden kickstart version')
        else:
            self.failed(f'One or more kickstart versions is { self.version } (threshold { kickstart_version_threshold }')

    def failed_kickstart_version_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_version_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, version=self.version, test="kickstart")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

class Resource_Check(aetest.Testcase):
    @aetest.setup
    def setup(self):
        self.list_of_hostnames = common_setup.get_hostname(self)

    # Test for CPU Idle > 15%
    @aetest.test
    def cpu_state_idle(self, cpu_state_idle_threshold = 15):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.system_resources = common_setup.get_show_system_resources(hostname)
            self.failed_cpu_state_idle = {}
            json_system_resources = json.loads(self.system_resources)
            self.cpu_state = float(json_system_resources['cpu_state_idle'])
            if self.cpu_state:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.cpu_state)
                if self.cpu_state <= cpu_state_idle_threshold:
                    table_row.append('Failed')
                    self.failed_cpu_state_idle = self.cpu_state
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_cpu_state_idle_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','CPU State Idle',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_cpu_state_idle:
            self.failed_cpu_state_idle_check()

            self.failed('One or more CPU Idle State Is Less Than or Equal to 15%')
        else:
            self.passed('All CPU Idle States are Greater Than 15%')
 
    @aetest.test
    def failed_cpu_state_idle_check(self, cpu_state_idle_threshold = 15):
        if self.cpu_state >= cpu_state_idle_threshold:
            self.skipped('All CPU Idle States Are Greater Than 15%')
        else:
            self.failed(f'One or more CPU Idle States is at { self.cpu_state } (threshold { cpu_state_idle_threshold }')

    def failed_cpu_state_idle_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_system_resources_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, resource=self.cpu_state, test="cpu_idle_state")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # Test for CPU Idle > 15%
    @aetest.test
    def current_memory_status(self, current_memory_status_threshold = "OK"):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.system_resources = common_setup.get_show_system_resources(hostname)        
            self.failed_current_memory_status = {}
            json_system_resources = json.loads(self.system_resources)
            self.memory_status = json_system_resources['current_memory_status']
            if self.memory_status:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.memory_status)
                if self.memory_status != current_memory_status_threshold:
                    table_row.append('Failed')
                    self.failed_current_memory_status = self.memory_status
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_current_memory_status_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','Current Memory Status',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_current_memory_status:
            self.failed_current_memory_status_check()
            self.failed('The Current Memory Status of one of the devices is Not OK')
        else:
            self.passed('The Current Memory Status of all devices is OK')
 
    @aetest.test
    def failed_current_memory_status_check(self, current_memory_status_threshold = "OK"):
        if self.memory_status == current_memory_status_threshold:
            self.skipped('Current Memory Status of all devices OK')
        else:
            self.failed(f'The Current Memory Status of one of the devices is { self.memory_status } (threshold { current_memory_status_threshold }')

    def failed_current_memory_status_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_system_resources_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, resource=self.memory_status, test="current_memory_status")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # Test for 15 minute load average
    @aetest.test
    def fifteen_minute_average_load(self, minute_average_threshold = 85):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.system_resources = common_setup.get_show_system_resources(hostname)
            self.failed_15_minute_average = {}
            json_system_resources = json.loads(self.system_resources)
            self.minute_average = float(json_system_resources['load_avg_15min'])
            if self.minute_average:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.cpu_state)
                if self.minute_average >= minute_average_threshold:
                    table_row.append('Failed')
                    self.failed_15_minute_average = self.minute_average
                    if WEBEX_ROOM:
                        self.failed_fifteen_minute_average_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','15 Minute Average',
                                       'Passed/Failed'],
                             tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_15_minute_average:
            self.failed_fifteen_minute_average_status_check()
            self.failed('The Current 15 Minutes Average Load of One of the Devices is Greater Than 85%')
        else:
            self.passed('The Current 15 Minute Average Load of All Devices is Under 85%')
 
    @aetest.test
    def failed_fifteen_minute_average_status_check(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
            self.skipped('The Current 15 Minute Average Load of all devices is Under 85%')
        else:
            self.failed(f'The Current 15 Minute Average Load of one of the devices is { self.minute_average } (threshold { minute_average_threshold }')

    def failed_fifteen_minute_average_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_system_resources_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, resource=self.minute_average, test="15_minute_load_average")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # Test for 5 minute load average
    @aetest.test
    def five_minute_average_load(self, minute_average_threshold = 85):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.system_resources = common_setup.get_show_system_resources(hostname)        
            self.failed_5_minute_average = {}
            json_system_resources = json.loads(self.system_resources)
            self.minute_average = float(json_system_resources['load_avg_5min'])
            if self.minute_average:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.cpu_state)
                if self.minute_average >= minute_average_threshold:
                    table_row.append('Failed')
                    self.failed_5_minute_average = self.minute_average
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_five_minute_average_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','5 Minute Average',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_5_minute_average:
            self.failed_five_minute_average_status_check()
            self.failed('The Current 5 Minutes Average Load of One or More Devices Is Greater Than 85%')
        else:
            self.passed('The Current 5 Minute Average Load of All Devices is Under 85%')
 
    @aetest.test
    def failed_five_minute_average_status_check(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
            self.skipped('The Current 5 Minute Average Load of All Devices is Under 85%')
        else:
            self.failed(f'The Current 5 Minute Average Load of one or more Devices is { self.minute_average } (threshold { minute_average_threshold }')

    def failed_five_minute_average_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_system_resources_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, resource=self.minute_average, test="5_minute_load_average")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # Test for 1 minute load average
    @aetest.test
    def one_minute_status_load(self, minute_average_threshold = 85):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.system_resources = common_setup.get_show_system_resources(hostname)        
            self.failed_1_minute_average = {}
            json_system_resources = json.loads(self.system_resources)
            self.minute_average = float(json_system_resources['load_avg_1min'])
            if self.minute_average:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.cpu_state)
                if self.minute_average >= minute_average_threshold:
                    table_row.append('Failed')
                    self.failed_1_minute_average = self.minute_average
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_one_minute_average_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','1 Minute Average',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_1_minute_average:
            self.failed_one_minute_average_status_check()
            self.failed('The Current 1 Minutes Average Load of One or More Devices is Greater Than 85%')
        else:
            self.passed('The Current 1 Minute Average Load for All Devices is Under 85%')
 
    @aetest.test
    def failed_one_minute_average_status_check(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
            self.skipped('The Current 1 Minute Average Load for All Devices is Under 85%')
        else:
            self.failed(f'The Current 1 Minute Average Load of one or more Devices is { self.minute_average } (threshold { minute_average_threshold }')

    def failed_one_minute_average_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_system_resources_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, resource=self.minute_average, test="1_minute_load_average")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # Test for memory percentage
    @aetest.test
    def memory_percentage(self, memory_percentage_threshold = 85):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.system_resources = common_setup.get_show_system_resources(hostname)        
            self.failed_memory_percentage = 0
            json_system_resources = json.loads(self.system_resources)
            self.memory_usage_total = int(json_system_resources['memory_usage_total'])
            self.memory_usage_used = int(json_system_resources['memory_usage_used'])
            self.memory_percentage_value = self.memory_usage_used / self.memory_usage_total * 100
            if self.memory_percentage_value != 0:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.cpu_state)
                if self.memory_percentage_value >= memory_percentage_threshold:
                    table_row.append('Failed')
                    self.failed_memory_percentage = self.memory_percentage_value
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_memory_percentage_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','Memory Percentage',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_memory_percentage:
            self.failed_memory_percentage_check()
            self.failed('The Current Available Memory of One or More Devices is Less Than 85%')
        else:
            self.passed('The Current Available Memory of All Devices is Greater Than 85%')
 
    @aetest.test
    def failed_memory_percentage_check(self, memory_percentage_threshold = 85):
        if self.failed_memory_percentage <= memory_percentage_threshold:
            self.skipped('The Current Available Memory of All Devices is Less Than 85%')
        else:
            self.failed(f'The Current Available Memory of one or more Devices is { self.minute_average }% (threshold { memory_percentage_threshold }')

    def failed_memory_percentage_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_system_resources_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, resource=self.minute_average, test="memory_percentage")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

class Directory_Check(aetest.Testcase):
    @aetest.setup
    def setup(self):
        self.list_of_hostnames = common_setup.get_hostname(self)

    # Test for free diskspace
    @aetest.test
    def free_diskspace(self, free_diskspace_threshold = 85):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.directory_info = common_setup.get_dir(hostname)
            self.failed_free_diskspace = 0
            json_version = json.loads(self.directory_info)
            self.total_diskspace = int(json_version['bytestotal'])
            self.used_diskspace = int(json_version['bytesused'])
            self.diskpace_percentage_value = self.used_diskspace / self.total_diskspace * 100
            if self.diskpace_percentage_value:
                table_row = []
                table_row.append(hostname)
                table_row.append(self.diskpace_percentage_value)
                if self.diskpace_percentage_value >= free_diskspace_threshold:
                    table_row.append('Failed')
                    self.failed_free_diskspace = self.diskpace_percentage_value
                    self.hostname = hostname
                    if WEBEX_ROOM:
                        self.failed_free_diskspace_webex()
                else:
                    table_row.append('Passed')
            else:
                table_row.append(hostname)
                table_row.append('N/A')
                table_row.append('N/A')
            table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device','Diskspace Used Percentage',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_free_diskspace != 0:
            self.failed_free_diskspace_check()
            self.failed('The free diskspace of one or more devices is less than 85%')
        else:
            self.passed('The free diskspace on all devices is greater than 85%')
 
    @aetest.test
    def failed_free_diskspace_check(self, free_diskspace_threshold = 85):
        if self.failed_free_diskspace <= free_diskspace_threshold:
            self.skipped('The free diskspace on all devices is greater than 85%')
        else:
            self.failed(f'The free diskspace percentage on one or more devices is { self.failed_free_diskspace } (threshold { free_diskspace_threshold }')

    def failed_free_diskspace_webex(self):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_dir_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, diskspace=self.failed_free_diskspace, test="diskspace")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # Test for bin file
    @aetest.test
    def directory_has_bin_file(self, bin_file_threshold = "nxos.9.3.8.bin"):
        table_data = []
        for hostname in self.list_of_hostnames:
            self.directory_info = common_setup.get_dir(hostname)        
            self.file_list = []
            json_interfaces = json.loads(self.directory_info)
            for item in json_interfaces['TABLE_dir']['ROW_dir']:
                if 'fname' in item:
                    self.file_list.append(item['fname'])
            for file in self.file_list:
                if file:
                    table_row = []
                    table_row.append(hostname)
                    table_row.append(file)
                    if file == bin_file_threshold:                
                        table_row.append('Passed')
                    else:
                        table_row.append('Failed')
                        self.hostname = hostname
                table_data.append(table_row)
 
        # display the table
        log.info(tabulate(table_data,
                          headers=['Device', 'Bin File',
                                   'Passed/Failed'],
                          tablefmt='orgtbl'))

        # should we pass or fail?
        if bin_file_threshold not in self.file_list:
            self.failed_bin_check()
            self.failed('One of the devices is Missing golden image')
        else:
            self.passed('Golden Image Present on All Devices')
 
    @aetest.test
    def failed_bin_check(self, bin_file_threshold = "nxos.9.3.8.bin"):
        if bin_file_threshold in self.file_list:
            self.skipped('Golden Image Present on All Devices')
        else:
            self.failed(f'The image file { bin_file_threshold } is not present in bootflash on one or more devices')

    def failed_bin_webex(self, bin_file_threshold = "nxos.9.3.8.bin"):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_dir_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, bin_file=bin_file_threshold, test="bin_file")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

class Interface_Errors_Count_Check(aetest.Testcase):
    @aetest.setup
    def setup(self):
        self.list_of_hostnames = common_setup.get_hostname(self)

    # Test for babble
    @aetest.test
    def interface_eth_babbles_counter_summary(self, eth_babbles_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_babbles' in intf:
                    counter = intf['eth_babbles']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > eth_babbles_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_babbles_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Babbles Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_babbles_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have babbles')
        else:
            self.passed('No interfaces have babbles')
 
    @aetest.test
    def interface_babbles_check(self, name = None, babbles_threshold = 0):
        if name is None:
            self.skipped('no interface babbles')
        else:
            self.failed(f'{ self.hostname } Interface { name } has babbles { self.failed_interfaces[name] } (threshold { babbles_threshold }')

    def interface_babbles_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="babbles")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for bad ethernet
    @aetest.test
    def interface_bad_eth_counter_summary(self, bad_eth_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_bad_eth' in intf:
                    counter = intf['eth_bad_eth']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > bad_eth_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname                            
                            if WEBEX_ROOM:
                                self.interface_bad_eth_check_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Bad Ethernet Errors Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_bad_eth_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Bad Ethernet errors')
        else:
            self.passed('No interfaces have Bad Ethernet errors')
 
    @aetest.test
    def interface_bad_eth_check(self, name = None, bad_eth_threshold = 0):
        if name is None:
            self.skipped('no interface bad ethernet errors')
        else:
            self.failed(f'Interface { name } has bad ethernet errors { self.failed_interfaces[name] } (threshold { bad_eth_threshold }')

    def interface_bad_eth_check_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="bad_eth")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for bad protocols
    @aetest.test
    def interface_bad_protocol_counter_summary(self, bad_protocol_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_bad_proto' in intf:
                    counter = intf['eth_bad_proto']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > bad_protocol_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_bad_protocol_check_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Bad Protocol Errors Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []
        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_bad_protocol_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Bad Protocol errors')
        else:
            self.passed('No interfaces have Bad Protocol errors')
 
    @aetest.test
    def interface_bad_protocol_check(self, name = None, bad_protocol_threshold = 0):
        if name is None:
            self.skipped('no interface bad protocol errors')
        else:
            self.failed(f'Interface { name } has bad protocol errors { self.failed_interfaces[name] } (threshold { bad_protocol_threshold }')

    def interface_bad_protocol_check_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="bad_protocol")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for collisions
    @aetest.test
    def interface_collisions_counter_summary(self, collisions_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_coll' in intf:
                    counter = intf['eth_coll']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > collisions_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_collisions_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Collisions Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_collisions_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Collisions')
        else:
            self.passed('No interfaces have Collisions')
 
    @aetest.test
    def interface_collisions_check(self, name = None, collisions_threshold = 0):
        if name is None:
            self.skipped('no interface collisions')
        else:
            self.failed(f'Interface { name } has collisions { self.failed_interfaces[name] } (threshold { collisions_threshold }')

    def interface_collisions_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="collisions")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for CRCs
    @aetest.test
    def interface_crc_counter_summary(self, crc_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_crc' in intf:
                    counter = intf['eth_crc']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > crc_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_crc_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'CRC Errors Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_crc_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have CRC errors')
        else:
            self.passed('No interfaces have CRC errors')
 
    @aetest.test
    def interface_crc_check(self, name = None, crc_threshold = 0):
        if name is None:
            self.skipped('no interface crc errors')
        else:
            self.failed(f'Interface { name } has crc errors { self.failed_interfaces[name] } (threshold { crc_threshold }')

    def interface_crc_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="crc")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for dribble
    @aetest.test
    def interface_dribble_counter_summary(self, dribble_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_dribble' in intf:
                    counter = intf['eth_dribble']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > dribble_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_dribble_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Dribble Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_dribble_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Dribble')
        else:
            self.passed('No interfaces have Dribble')

    @aetest.test
    def interface_dribble_check(self, name = None, dribble_threshold = 0):
        if name is None:
            self.skipped('no interface dribble')
        else:
            self.failed(f'Interface { name } has dribble { self.failed_interfaces[name] } (threshold { dribble_threshold }')

    def interface_dribble_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="dribble")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for full duplex
    @aetest.test
    def interface_full_duplex_summary(self, duplex_fail_threshold = "half"):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_duplex' in intf:
                    duplex_value = intf['eth_duplex']
                    if duplex_value:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(duplex_value)
                        if duplex_value == duplex_fail_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = duplex_value
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_duplex_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Duplex Mode',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_duplex_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Dribble')
        else:
            self.passed('No interfaces have Dribble')
 
    @aetest.test
    def interface_duplex_check(self, name = None):
        if name is None:
            self.skipped('All interfaces duplex is full')
        else:
            self.failed(f'Interface { name } { self.failed_interfaces[name] } is not full duplex')

    def interface_duplex_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="duplex")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for Ignored
    @aetest.test
    def interface_ignored_counter_summary(self, ignored_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_ignored' in intf:
                    counter = intf['eth_ignored']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > ignored_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_ignored_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Ignored Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_ignored_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have ignored packets')
        else:
            self.passed('No interfaces have ingored packets')

    @aetest.test
    def interface_ignored_check(self, name = None, ignored_threshold = 0):
        if name is None:
            self.skipped('no interface ignores')
        else:
            self.failed(f'Interface { name } has ignores { self.failed_interfaces[name] } (threshold { ignored_threshold }')

    def interface_ignored_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="ignored")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for down if drops
    @aetest.test
    def interface_down_if_drops_counter_summary(self, down_if_drops_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_in_ifdown_drops' in intf:
                    counter = intf['eth_in_ifdown_drops']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > down_if_drops_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_down_if_drops_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Down Interface Drops Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_down_if_drops_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have down interface drops')
        else:
            self.passed('No interfaces have down interface drops')

    @aetest.test
    def interface_down_if_drops_check(self, name = None, down_if_drops_threshold = 0):
        if name is None:
            self.skipped('no interface down interface drops')
        else:
            self.failed(f'Interface { name } has down interface drops { self.failed_interfaces[name] } (threshold { down_if_drops_threshold }')

    def interface_down_if_drops_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="down_if_drops")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for input discards
    @aetest.test
    def interface_input_discards_counter_summary(self, input_discards_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_indiscard' in intf:
                    counter = intf['eth_indiscard']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > input_discards_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_input_discards_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Input Discards Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_input_discards_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have input discards')
        else:
            self.passed('No interfaces have input discards')

    @aetest.test
    def interface_input_discards_check(self, name = None, input_discards_threshold = 0):
        if name is None:
            self.skipped('no interface input discards')
        else:
            self.failed(f'Interface { name } has input discards { self.failed_interfaces[name] } (threshold { input_discards_threshold }')

    def interface_input_discards_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="input_discards")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for input errors
    @aetest.test
    def interface_input_errors_counter_summary(self, input_errors_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_inerr' in intf:
                    counter = intf['eth_inerr']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > input_errors_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_input_errors_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Input Errors Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_input_errors_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have input errors')
        else:
            self.passed('No interfaces have input errors')

    @aetest.test
    def interface_input_errors_check(self, name = None, input_errors_threshold = 0):
        if name is None:
            self.skipped('no interface input errors')
        else:
            self.failed(f'Interface { name } has input errors { self.failed_interfaces[name] } (threshold { input_errors_threshold }')

    def interface_input_errors_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="input_errors")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for input pause
    @aetest.test
    def interface_input_pause_counter_summary(self, input_pause_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_inpause' in intf:
                    counter = intf['eth_inpause']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > input_pause_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_input_pause_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Input Pause Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_input_pause_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have input pause')
        else:
            self.passed('No interfaces have input pause')

    @aetest.test
    def interface_input_pause_check(self, name = None, input_pause_threshold = 0):
        if name is None:
            self.skipped('no interface input pause')
        else:
            self.failed(f'Interface { name } has input pause { self.failed_interfaces[name] } (threshold { input_pause_threshold }')

    def interface_input_pause_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="input_pause")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for late collisions
    @aetest.test
    def interface_late_collision_counter_summary(self, late_collision_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_latecoll' in intf:
                    counter = intf['eth_latecoll']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > late_collision_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_late_collision_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Late Collision Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_late_collsion_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have late collisions')
        else:
            self.passed('No interfaces have late collisions')

    @aetest.test
    def interface_late_collsion_check(self, name = None, late_collision_threshold = 0):
        if name is None:
            self.skipped('no interface late collisions')
        else:
            self.failed(f'Interface { name } has late collisions { self.failed_interfaces[name] } (threshold { late_collision_threshold }')

    def interface_late_collision_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="late_collision")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for lost carrier
    @aetest.test
    def interface_lost_carrier_counter_summary(self, lost_carrier_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_lostcarrier' in intf:
                    counter = intf['eth_lostcarrier']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > lost_carrier_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_lost_carrier_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Lost Carrier Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_lost_carrier_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have lost carrier')
        else:
            self.passed('No interfaces have lost carrier')

    @aetest.test
    def interface_lost_carrier_check(self, name = None, lost_carrier_threshold = 0):
        if name is None:
            self.skipped('no interface lost carrier')
        else:
            self.failed(f'Interface { name } has lost carrier { self.failed_interfaces[name] } (threshold { lost_carrier_threshold }')

    def interface_lost_carrier_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="lost_carrier")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for no buffer
    @aetest.test
    def interface_no_buffer_counter_summary(self, no_buffer_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_nobuf' in intf:
                    counter = intf['eth_nobuf']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > no_buffer_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_no_buffer_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'No Buffer Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_no_buffer_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have no buffer')
        else:
            self.passed('No interfaces have no buffer')

    @aetest.test
    def interface_no_buffer_check(self, name = None, no_buffer_threshold = 0):
        if name is None:
            self.skipped('no interface no buffer')
        else:
            self.failed(f'Interface { name } has no buffer { self.failed_interfaces[name] } (threshold { no_buffer_threshold }')

    def interface_no_buffer_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="no_buffer")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for no carrier
    @aetest.test
    def interface_no_carrier_counter_summary(self, no_carrier_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_nocarrier' in intf:
                    counter = intf['eth_nocarrier']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > no_carrier_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_no_carrier_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'No Carrier Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_no_carrier_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have no carrier')
        else:
            self.passed('No interfaces have no carrier')

    @aetest.test
    def interface_no_carrier_check(self, name = None, no_carrier_threshold = 0):
        if name is None:
            self.skipped('no interface no carrier')
        else:
            self.failed(f'Interface { name } has no carrier { self.failed_interfaces[name] } (threshold { no_carrier_threshold }')

    def interface_no_carrier_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="no_carrier")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for output discards
    @aetest.test
    def interface_output_discard_counter_summary(self, output_discard_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_outdiscard' in intf:
                    counter = intf['eth_outdiscard']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > output_discard_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_output_discard_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Output Discard Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_output_discard_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have output discards')
        else:
            self.passed('No interfaces have output discards')

    @aetest.test
    def interface_output_discard_check(self, name = None, output_discard_threshold = 0):
        if name is None:
            self.skipped('no interface output discard')
        else:
            self.failed(f'Interface { name } has output discards { self.failed_interfaces[name] } (threshold { output_discard_threshold }')

    def interface_output_discard_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="output_discard")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for output errors
    @aetest.test
    def interface_output_error_counter_summary(self, output_error_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_outerr' in intf:
                    counter = intf['eth_outerr']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > output_error_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_output_error_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Output Error Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_output_error_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have output errors')
        else:
            self.passed('No interfaces have output errors')

    @aetest.test
    def interface_output_error_check(self, name = None, output_error_threshold = 0):
        if name is None:
            self.skipped('no interface output errors')
        else:
            self.failed(f'Interface { name } has output errors { self.failed_interfaces[name] } (threshold { output_error_threshold }')

    def interface_output_error_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="output_error")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for output pause
    @aetest.test
    def interface_output_pause_counter_summary(self, output_pause_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_outpause' in intf:
                    counter = intf['eth_outpause']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > output_pause_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_output_pause_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Output Pause Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_output_pause_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have output pauses')
        else:
            self.passed('No interfaces have output pauses')

    @aetest.test
    def interface_output_pause_check(self, name = None, output_pause_threshold = 0):
        if name is None:
            self.skipped('no interface output pauses')
        else:
            self.failed(f'Interface { name } has output pauses { self.failed_interfaces[name] } (threshold { output_pause_threshold }')

    def interface_output_pause_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="output_pause")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for output overrun
    @aetest.test
    def interface_output_overrun_counter_summary(self, output_overrun_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_overrun' in intf:
                    counter = intf['eth_overrun']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > output_overrun_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_output_overrun_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Output Overrun Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_output_overrun_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have output overruns')
        else:
            self.passed('No interfaces have output overruns')

    @aetest.test
    def interface_output_overrun_check(self, name = None, output_overrun_threshold = 0):
        if name is None:
            self.skipped('no interface output overruns')
        else:
            self.failed(f'Interface { name } has output overruns { self.failed_interfaces[name] } (threshold { output_overrun_threshold }')

    def interface_output_overrun_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="output_overrun")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for runts
    @aetest.test
    def interface_runts_counter_summary(self, runts_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_runts' in intf:
                    counter = intf['eth_runts']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > runts_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_runts_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Runts Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_runts_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have runts')
        else:
            self.passed('No interfaces have runts')

    @aetest.test
    def interface_runts_check(self, name = None, runt_threshold = 0):
        if name is None:
            self.skipped('no interface runts')
        else:
            self.failed(f'Interface { name } has runts { self.failed_interfaces[name] } (threshold { runt_threshold }')

    def interface_runts_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="runts")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for underrun
    @aetest.test
    def interface_underrun_counter_summary(self, underrun_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'eth_underrun' in intf:
                    counter = intf['eth_underrun']
                    if counter:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(counter)
                        if int(counter) > underrun_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = int(counter)
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_underrun_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'Underrun Counter',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []


        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_underrun_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces have underrun')
        else:
            self.passed('No interfaces have underrun')

    @aetest.test
    def interface_underrun_check(self, name = None, underrun_threshold = 0):
        if name is None:
            self.skipped('no interface underrun')
        else:
            self.failed(f'Interface { name } has underrun { self.failed_interfaces[name] } (threshold { underrun_threshold }')

    def interface_underrun_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="underrun")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for state reason description - ports should be UP or Admin down
    @aetest.test
    def interface_state_summary(self, state_fail_threshold = "Link not connected"):
        table_data = []
        self.failed_interfaces = {}
        for hostname in self.list_of_hostnames:
            self.interface_info = common_setup.get_show_interface(hostname)        
            json_interfaces = json.loads(self.interface_info)
            for intf in json_interfaces['TABLE_interface']['ROW_interface']:
                if 'state_rsn_desc' in intf:
                    state_value = intf['state_rsn_desc']
                    if state_value:
                        table_row = []
                        table_row.append(hostname)
                        table_row.append(intf['interface'])
                        table_row.append(state_value)
                        if state_value == state_fail_threshold:
                            table_row.append('Failed')
                            self.failed_interfaces[intf['interface']] = state_value
                            self.interface_name = intf['interface']
                            error_counter = self.failed_interfaces[intf['interface']]
                            self.hostname = hostname
                            if WEBEX_ROOM:
                                self.interface_state_check_webex(name = error_counter)
                        else:
                            table_row.append('Passed')
                    else:
                        table_row.append(hostname)
                        table_row.append(intf)
                        table_row.append('N/A')
                        table_row.append('N/A')
                    table_data.append(table_row)
 
        # display the table
            log.info(tabulate(table_data,
                              headers=['Device', 'Interface',
                                       'State',
                                       'Passed/Failed'],
                              tablefmt='orgtbl'))
            table_data = []

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_state_check,
                             name = self.failed_interfaces.keys())
            self.failed('Some interfaces are not connected')
        else:
            self.passed('No interfaces are not connected')
 
    @aetest.test
    def interface_state_check(self, name = None):
        if name is None:
            self.skipped('All interfaces are connected or administratively down')
        else:
            self.failed(f'Interface { name } { self.failed_interfaces[name] } is not connected or administratively down')

    def interface_state_check_webex(self, name):
        template_dir = Path(__file__).resolve().parent
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        adaptive_card_template = env.get_template('failed_show_interface_adaptive_card.j2')
        adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, failure=name, interface=self.interface_name, test="state")
        webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
        log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

if __name__ == '__main__':  # pragma: no cover
    aetest.main()