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

USERNAME=""
TOKEN=""
REPO_NAME=""
WEBEX_ROOM=""
WEBEX_TOKEN=""

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
    def get_show_version(self):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        for item in repo.get_contents("JSON"):
            raw_json_content = item.decoded_content
            if "show version" in item.name:
                show_version = raw_json_content
        return(show_version)

    @aetest.subsection
    def get_show_system_resources(self):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        for item in repo.get_contents("JSON"):
            raw_json_content = item.decoded_content
            if "show system resource" in item.name:
                show_system_resources = raw_json_content
        return(show_system_resources)

    @aetest.subsection
    def get_show_interface(self):
        g = Github(USERNAME, TOKEN)
        repo = g.get_user().get_repo(REPO_NAME)
        for item in repo.get_contents("JSON"):
            raw_json_content = item.decoded_content
            if "show interface" in item.name:
                show_interface = raw_json_content
        return(show_interface)

    @aetest.subsection
    def prepare_testcases(self):
        aetest.loop.mark(Interface_Errors_Count_Check, self.hostname)

###################################################################
#                     TESTCASES SECTION                           #
###################################################################
class Version_Check(aetest.Testcase):
    @aetest.setup
    def setup(self):
        self.version_info = common_setup.get_show_version(self)
        self.hostname = common_setup.get_hostname(self)

    # Test for NXOS Version
    @aetest.test
    def nxos_version(self, nxos_version_threshold = "9.3(8)"):
        table_data = []
        self.failed_nxos_version = {}
        json_version = json.loads(self.version_info)
        self.version = json_version['nxos_ver_str']
        if self.version:
            table_row = []
            table_row.append(self.hostname)
            table_row.append(self.version)
            if self.version != nxos_version_threshold:
                table_row.append('Failed')
                self.failed_nxos_version = self.version
            else:
                table_row.append('Passed')
        else:
            table_row.append(self.hostname)
            table_row.append('N/A')
            table_row.append('N/A')
        table_data.append(table_row)
 
        # display the table
        log.info(tabulate(table_data,
                          headers=['Device','NXOS Version',
                                   'Passed/Failed'],
                          tablefmt='orgtbl'))

        # should we pass or fail?
        if self.failed_nxos_version:
            self.failed_nxos_version_check()
            if WEBEX_ROOM:
                self.failed_nxos_version_webex()
            self.failed('The NXOS version does not match the golden version')
        else:
            self.passed('NXOS Version matches golden version')
 
    @aetest.test
    def failed_nxos_version_check(self, nxos_version_threshold = "9.3(8)"):
        if self.version == nxos_version_threshold:
            self.skipped('Version matches golden version')
        else:
            self.failed(f'The NXOS version is { self.version } (threshold { nxos_version_threshold }')

    @aetest.test
    def failed_nxos_version_webex(self, nxos_version_threshold = "9.3(8)"):
        if self.version == nxos_version_threshold:
           self.skipped('NXOS version matches golden version')
        else:
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
        self.failed_kickstart_version = {}
        json_version = json.loads(self.version_info)
        self.version = json_version['kickstart_ver_str']
        if self.version:
            table_row = []
            table_row.append(self.hostname)
            table_row.append(self.version)
            if self.version != kickstart_version_threshold:
                table_row.append('Failed')
                self.failed_kickstart_version = self.version
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

        # should we pass or fail?
        if self.failed_kickstart_version:
            self.failed_kickstart_version_check()
            if WEBEX_ROOM:
                self.failed_kickstart_version_webex()
            self.failed('The kickstart version does not match the golden version')
        else:
            self.passed('Kickstart Version matches golden version')
 
    @aetest.test
    def failed_kickstart_version_check(self, kickstart_version_threshold = "9.3(8)"):
        if self.version == kickstart_version_threshold:
            self.skipped('Version matches golden version')
        else:
            self.failed(f'The kickstart version is { self.version } (threshold { kickstart_version_threshold }')

    @aetest.test
    def failed_kickstart_version_webex(self, kickstart_version_threshold = "9.3(8)"):
        if self.version == kickstart_version_threshold:
           self.skipped('version matches golden version')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_version_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, version=self.version, test="kickstart")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

class Resource_Check(aetest.Testcase):
    @aetest.setup
    def setup(self):
        self.system_resources = common_setup.get_show_system_resources(self)
        self.hostname = common_setup.get_hostname(self)

    # Test for CPU Idle > 15%
    @aetest.test
    def cpu_state_idle(self, cpu_state_idle_threshold = 15):
        table_data = []
        self.failed_cpu_state_idle = {}
        json_system_resources = json.loads(self.system_resources)
        self.cpu_state = float(json_system_resources['cpu_state_idle'])
        if self.cpu_state:
            table_row = []
            table_row.append(self.hostname)
            table_row.append(self.cpu_state)
            if self.cpu_state <= cpu_state_idle_threshold:
                table_row.append('Failed')
                self.failed_cpu_state_idle = self.cpu_state
            else:
                table_row.append('Passed')
        else:
            table_row.append(self.hostname)
            table_row.append('N/A')
            table_row.append('N/A')
        table_data.append(table_row)
 
        # display the table
        log.info(tabulate(table_data,
                          headers=['Device','CPU State Idle',
                                   'Passed/Failed'],
                          tablefmt='orgtbl'))

        # should we pass or fail?
        if self.failed_cpu_state_idle:
            self.failed_cpu_state_idle_check()
            if WEBEX_ROOM:
                self.failed_cpu_state_idle_webex()
            self.failed('The CPU Idle State Is Less Than or Equal to 15%')
        else:
            self.passed('The CPU Idle State Is Greater Than 15%')
 
    @aetest.test
    def failed_cpu_state_idle_check(self, cpu_state_idle_threshold = 15):
        if self.cpu_state >= cpu_state_idle_threshold:
            self.skipped('CPU Idle State Is Greater Than 15%')
        else:
            self.failed(f'The CPU Idle State is { self.cpu_state } (threshold { cpu_state_idle_threshold }')

    @aetest.test
    def failed_cpu_state_idle_webex(self, cpu_state_idle_threshold = 15):
        if self.cpu_state >= cpu_state_idle_threshold:
           self.skipped('CPU Idle State Is Greater Than 15%')
        else:
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
        self.failed_current_memory_status = {}
        json_system_resources = json.loads(self.system_resources)
        self.memory_status = json_system_resources['current_memory_status']
        if self.memory_status:
            table_row = []
            table_row.append(self.hostname)
            table_row.append(self.memory_status)
            if self.memory_status != current_memory_status_threshold:
                table_row.append('Failed')
                self.failed_current_memory_status = self.memory_status
            else:
                table_row.append('Passed')
        else:
            table_row.append(self.hostname)
            table_row.append('N/A')
            table_row.append('N/A')
        table_data.append(table_row)
 
        # display the table
        log.info(tabulate(table_data,
                          headers=['Device','Current Memory Status',
                                   'Passed/Failed'],
                          tablefmt='orgtbl'))

        # should we pass or fail?
        if self.failed_current_memory_status:
            self.failed_current_memory_status_check()
            if WEBEX_ROOM:
                self.failed_current_memory_status_webex()
            self.failed('The Current Memory Status is Not OK')
        else:
            self.passed('The Current Memory Status is OK')
 
    @aetest.test
    def failed_current_memory_status_check(self, current_memory_status_threshold = "OK"):
        if self.memory_status == current_memory_status_threshold:
            self.skipped('Current Memory Status is OK')
        else:
            self.failed(f'The Current Memory Status is { self.memory_status } (threshold { current_memory_status_threshold }')

    @aetest.test
    def failed_current_memory_status_webex(self, current_memory_status_threshold = "OK"):
        if self.memory_status == current_memory_status_threshold:
           self.skipped('The Current Memory Status Is OK')
        else:
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
        self.failed_15_minute_average = {}
        json_system_resources = json.loads(self.system_resources)
        self.minute_average = float(json_system_resources['load_avg_15min'])
        if self.minute_average:
            table_row = []
            table_row.append(self.hostname)
            table_row.append(self.cpu_state)
            if self.minute_average >= minute_average_threshold:
                table_row.append('Failed')
                self.failed_minute_average = self.minute_average
            else:
                table_row.append('Passed')
        else:
            table_row.append(self.hostname)
            table_row.append('N/A')
            table_row.append('N/A')
        table_data.append(table_row)
 
        # display the table
        log.info(tabulate(table_data,
                          headers=['Device','15 Minute Average',
                                   'Passed/Failed'],
                          tablefmt='orgtbl'))

        # should we pass or fail?
        if self.failed_minute_average:
            self.failed_fifteen_minute_average_status_check()
            if WEBEX_ROOM:
                self.failed_fifteen_minute_average_webex()
            self.failed('The Current 15 Minutes Average Load Is Greater Than 85%')
        else:
            self.passed('The Current 15 Minute Average Load is Under 85%')
 
    @aetest.test
    def failed_fifteen_minute_average_status_check(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
            self.skipped('The Current 15 Minute Average Load is Under 85%')
        else:
            self.failed(f'The Current 15 Minute Average Load { self.minute_average } (threshold { minute_average_threshold }')

    @aetest.test
    def failed_fifteen_minute_average_webex(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
           self.skipped('The Current 15 Minute Average Load is Under 85%')
        else:
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
        self.failed_5_minute_average = {}
        json_system_resources = json.loads(self.system_resources)
        self.minute_average = float(json_system_resources['load_avg_5min'])
        if self.minute_average:
            table_row = []
            table_row.append(self.hostname)
            table_row.append(self.cpu_state)
            if self.minute_average >= minute_average_threshold:
                table_row.append('Failed')
                self.failed_5_minute_average = self.minute_average
            else:
                table_row.append('Passed')
        else:
            table_row.append(self.hostname)
            table_row.append('N/A')
            table_row.append('N/A')
        table_data.append(table_row)
 
        # display the table
        log.info(tabulate(table_data,
                          headers=['Device','5 Minute Average',
                                   'Passed/Failed'],
                          tablefmt='orgtbl'))

        # should we pass or fail?
        if self.failed_5_minute_average:
            self.failed_five_minute_average_status_check()
            if WEBEX_ROOM:
                self.failed_five_minute_average_webex()
            self.failed('The Current 5 Minutes Average Load Is Greater Than 85%')
        else:
            self.passed('The Current 5 Minute Average Load is Under 85%')
 
    @aetest.test
    def failed_five_minute_average_status_check(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
            self.skipped('The Current 5 Minute Average Load is Under 85%')
        else:
            self.failed(f'The Current 5 Minute Average Load { self.minute_average } (threshold { minute_average_threshold }')

    @aetest.test
    def failed_five_minute_average_webex(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
           self.skipped('The Current 5 Minute Average Load is Under 85%')
        else:
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
        self.failed_1_minute_average = {}
        json_system_resources = json.loads(self.system_resources)
        self.minute_average = float(json_system_resources['load_avg_1min'])
        if self.minute_average:
            table_row = []
            table_row.append(self.hostname)
            table_row.append(self.cpu_state)
            if self.minute_average >= minute_average_threshold:
                table_row.append('Failed')
                self.failed_1_minute_average = self.minute_average
            else:
                table_row.append('Passed')
        else:
            table_row.append(self.hostname)
            table_row.append('N/A')
            table_row.append('N/A')
        table_data.append(table_row)
 
        # display the table
        log.info(tabulate(table_data,
                          headers=['Device','1 Minute Average',
                                   'Passed/Failed'],
                          tablefmt='orgtbl'))

        # should we pass or fail?
        if self.failed_1_minute_average:
            self.failed_one_minute_average_status_check()
            if WEBEX_ROOM:
                self.failed_one_minute_average_webex()
            self.failed('The Current 1 Minutes Average Load Is Greater Than 85%')
        else:
            self.passed('The Current 1 Minute Average Load is Under 85%')
 
    @aetest.test
    def failed_one_minute_average_status_check(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
            self.skipped('The Current 1 Minute Average Load is Under 85%')
        else:
            self.failed(f'The Current 1 Minute Average Load { self.minute_average } (threshold { minute_average_threshold }')

    @aetest.test
    def failed_one_minute_average_webex(self, minute_average_threshold = 85):
        if self.minute_average <= minute_average_threshold:
           self.skipped('The Current 1 Minute Average Load is Under 85%')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_system_resources_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, resource=self.minute_average, test="1_minute_load_average")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

class Interface_Errors_Count_Check(aetest.Testcase):
    @aetest.setup
    def setup(self):
        self.interface_info = common_setup.get_show_interface(self)
        self.hostname = common_setup.get_hostname(self)

    # Test for babble
    @aetest.test
    def interface_eth_babbles_counter_summary(self, eth_babbles_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_babbles' in intf:
                counter = intf['eth_babbles']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > eth_babbles_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_babbles_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_babbles_webex,name = self.failed_interfaces.keys())
            self.failed('Some interfaces have babbles')
        else:
            self.passed('No interfaces have babbles')
 
    @aetest.test
    def interface_babbles_check(self, name = None, babbles_threshold = 0):
        if name is None:
            self.skipped('no interface babbles')
        else:
            self.failed(f'Interface { name } has babbles { self.failed_interfaces[name] } (threshold { babbles_threshold }')

    @aetest.test
    def interface_babbles_webex(self, name = None):
        if name is None:
           self.skipped('no interface babbles')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="babbles")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for bad ethernet
    @aetest.test
    def interface_bad_eth_counter_summary(self, bad_eth_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_bad_eth' in intf:
                counter = intf['eth_bad_eth']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > bad_eth_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_bad_eth_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_bad_eth_check_webex,name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Bad Ethernet errors')
        else:
            self.passed('No interfaces have Bad Ethernet errors')
 
    @aetest.test
    def interface_bad_eth_check(self, name = None, bad_eth_threshold = 0):
        if name is None:
            self.skipped('no interface bad ethernet errors')
        else:
            self.failed(f'Interface { name } has bad ethernet errors { self.failed_interfaces[name] } (threshold { bad_eth_threshold }')

    @aetest.test
    def interface_bad_eth_check_webex(self, name = None):
        if name is None:
           self.skipped('no interface bad ethernet')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="bad_eth")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for bad protocols
    @aetest.test
    def interface_bad_protocol_counter_summary(self, bad_protocol_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_bad_proto' in intf:
                counter = intf['eth_bad_proto']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > bad_protocol_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_bad_protocol_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_bad_protocol_check_webex,name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Bad Protocol errors')
        else:
            self.passed('No interfaces have Bad Protocol errors')
 
    @aetest.test
    def interface_bad_protocol_check(self, name = None, bad_protocol_threshold = 0):
        if name is None:
            self.skipped('no interface bad protocol errors')
        else:
            self.failed(f'Interface { name } has bad protocol errors { self.failed_interfaces[name] } (threshold { bad_protocol_threshold }')

    @aetest.test
    def interface_bad_protocol_check_webex(self, name = None):
        if name is None:
           self.skipped('no interface bad protocol')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="bad_protocol")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for collisions
    @aetest.test
    def interface_collisions_counter_summary(self, collisions_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_coll' in intf:
                counter = intf['eth_coll']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > collisions_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_collisions_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_collisions_webex,name = self.failed_interfaces.keys())
            self.failed('Some interfaces have Collisions')
        else:
            self.passed('No interfaces have Collisions')
 
    @aetest.test
    def interface_collisions_check(self, name = None, collisions_threshold = 0):
        if name is None:
            self.skipped('no interface collisions')
        else:
            self.failed(f'Interface { name } has collisions { self.failed_interfaces[name] } (threshold { collisions_threshold }')

    @aetest.test
    def interface_collisions_webex(self, name = None):
        if name is None:
           self.skipped('no interface collisions')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="collisions")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for CRCs
    @aetest.test
    def interface_crc_counter_summary(self, crc_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_crc' in intf:
                counter = intf['eth_crc']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > crc_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_crc_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_crc_webex,name = self.failed_interfaces.keys())
            self.failed('Some interfaces have CRC errors')
        else:
            self.passed('No interfaces have CRC errors')
 
    @aetest.test
    def interface_crc_check(self, name = None, crc_threshold = 0):
        if name is None:
            self.skipped('no interface crc errors')
        else:
            self.failed(f'Interface { name } has crc errors { self.failed_interfaces[name] } (threshold { crc_threshold }')

    @aetest.test
    def interface_crc_webex(self, name = None):
        if name is None:
           self.skipped('no interface crc')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="crc")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for dribble
    @aetest.test
    def interface_dribble_counter_summary(self, dribble_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_dribble' in intf:
                counter = intf['eth_dribble']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > dribble_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_dribble_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_dribble_webex,name = self.failed_interfaces.keys())                             
            self.failed('Some interfaces have Dribble')
        else:
            self.passed('No interfaces have Dribble')

    @aetest.test
    def interface_dribble_check(self, name = None, dribble_threshold = 0):
        if name is None:
            self.skipped('no interface dribble')
        else:
            self.failed(f'Interface { name } has dribble { self.failed_interfaces[name] } (threshold { dribble_threshold }')

    @aetest.test
    def interface_dribble_webex(self, name = None):
        if name is None:
           self.skipped('no interface dribble')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="dribble")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for full duplex
    @aetest.test
    def interface_full_duplex_summary(self, duplex_fail_threshold = "half"):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_duplex' in intf:
                duplex_value = intf['eth_duplex']
                if duplex_value:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(duplex_value)
                    if duplex_value == duplex_fail_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = duplex_value
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_duplex_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_duplex_webex,name = self.failed_interfaces.keys())                             
            self.failed('Some interfaces have Dribble')
        else:
            self.passed('No interfaces have Dribble')
 
    @aetest.test
    def interface_duplex_check(self, name = None):
        if name is None:
            self.skipped('All interfaces duplex is full')
        else:
            self.failed(f'Interface { name } { self.failed_interfaces[name] } is not full duplex')

    @aetest.test
    def interface_duplex_webex(self, name = None):
        if name is None:
           self.skipped('Interface Full Duplex')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="duplex")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for Ignored
    @aetest.test
    def interface_ignored_counter_summary(self, ignored_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_ignored' in intf:
                counter = intf['eth_ignored']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > ignored_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_ignored_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_ignored_webex,name = self.failed_interfaces.keys())                             
            self.failed('Some interfaces have ignored packets')
        else:
            self.passed('No interfaces have ingored packets')

    @aetest.test
    def interface_ignored_check(self, name = None, ignored_threshold = 0):
        if name is None:
            self.skipped('no interface ignores')
        else:
            self.failed(f'Interface { name } has ignores { self.failed_interfaces[name] } (threshold { ignored_threshold }')

    @aetest.test
    def interface_ignored_webex(self, name = None):
        if name is None:
           self.skipped('no interface crc')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="ignored")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for down if drops
    @aetest.test
    def interface_down_if_drops_counter_summary(self, down_if_drops_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_in_ifdown_drops' in intf:
                counter = intf['eth_in_ifdown_drops']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > down_if_drops_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_down_if_drops_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_down_if_drops_webex,name = self.failed_interfaces.keys())                             
            self.failed('Some interfaces have down interface drops')
        else:
            self.passed('No interfaces have down interface drops')

    @aetest.test
    def interface_down_if_drops_check(self, name = None, down_if_drops_threshold = 0):
        if name is None:
            self.skipped('no interface down interface drops')
        else:
            self.failed(f'Interface { name } has down interface drops { self.failed_interfaces[name] } (threshold { down_if_drops_threshold }')

    @aetest.test
    def interface_down_if_drops_webex(self, name = None):
        if name is None:
           self.skipped('no down interface drops')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="down_if_drops")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for input discards
    @aetest.test
    def interface_input_discards_counter_summary(self, input_discards_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_indiscard' in intf:
                counter = intf['eth_indiscard']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > input_discards_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_input_discards_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_input_discards_webex,name = self.failed_interfaces.keys())                             
            self.failed('Some interfaces have input discards')
        else:
            self.passed('No interfaces have input discards')

    @aetest.test
    def interface_input_discards_check(self, name = None, input_discards_threshold = 0):
        if name is None:
            self.skipped('no interface input discards')
        else:
            self.failed(f'Interface { name } has input discards { self.failed_interfaces[name] } (threshold { input_discards_threshold }')

    @aetest.test
    def interface_input_discards_webex(self, name = None):
        if name is None:
           self.skipped('no interface input discards')
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, hostname=self.hostname, interface=name, failure=self.failed_interfaces[name], test="input_discards")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)

    # test for input errors
    @aetest.test
    def interface_input_errors_counter_summary(self, input_errors_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_inerr' in intf:
                counter = intf['eth_inerr']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > input_errors_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for input pause
    @aetest.test
    def interface_input_pause_counter_summary(self, input_pause_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_inpause' in intf:
                counter = intf['eth_inpause']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > input_pause_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for late collisions
    @aetest.test
    def interface_late_collision_counter_summary(self, late_collision_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_latecoll' in intf:
                counter = intf['eth_latecoll']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > late_collision_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for lost carrier
    @aetest.test
    def interface_lost_carrier_counter_summary(self, lost_carrier_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_lostcarrier' in intf:
                counter = intf['eth_lostcarrier']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > lost_carrier_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for no buffer
    @aetest.test
    def interface_no_buffer_counter_summary(self, no_buffer_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_nobuf' in intf:
                counter = intf['eth_nobuf']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > no_buffer_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for no carrier
    @aetest.test
    def interface_no_carrier_counter_summary(self, no_carrier_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_nocarrier' in intf:
                counter = intf['eth_nocarrier']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > no_carrier_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for output discards
    @aetest.test
    def interface_output_discard_counter_summary(self, output_discard_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_outdiscard' in intf:
                counter = intf['eth_outdiscard']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > output_discard_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for output errors
    @aetest.test
    def interface_output_error_counter_summary(self, output_error_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_outerr' in intf:
                counter = intf['eth_outerr']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > output_error_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for output pause
    @aetest.test
    def interface_output_pause_counter_summary(self, output_pause_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_outpause' in intf:
                counter = intf['eth_outpause']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > output_pause_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for output overrun
    @aetest.test
    def interface_output_overrun_counter_summary(self, output_overrun_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_overrun' in intf:
                counter = intf['eth_overrun']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > output_overrun_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for runts
    @aetest.test
    def interface_runts_counter_summary(self, runts_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_runts' in intf:
                counter = intf['eth_runts']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > runts_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for underrun
    @aetest.test
    def interface_underrun_counter_summary(self, underrun_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_underrun' in intf:
                counter = intf['eth_underrun']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > underrun_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for underrun
    @aetest.test
    def interface_underrun_counter_summary(self, underrun_threshold = 0):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'eth_underrun' in intf:
                counter = intf['eth_underrun']
                if counter:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(counter)
                    if int(counter) > underrun_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = int(counter)
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

    # test for state reason description - ports should be UP or Admin down
    @aetest.test
    def interface_state_summary(self, state_fail_threshold = "Link not connected"):
        table_data = []
        self.failed_interfaces = {}
        json_interfaces = json.loads(self.interface_info)
        for intf in json_interfaces['TABLE_interface']['ROW_interface']:
            if 'state_rsn_desc' in intf:
                state_value = intf['state_rsn_desc']
                if state_value:
                    table_row = []
                    table_row.append(self.hostname)
                    table_row.append(intf['interface'])
                    table_row.append(state_value)
                    if state_value == state_fail_threshold:
                        table_row.append('Failed')
                        self.failed_interfaces[intf['interface']] = state_value
                    else:
                        table_row.append('Passed')
                else:
                    table_row.append(self.hostname)
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

        # should we pass or fail?
        if self.failed_interfaces:
            aetest.loop.mark(self.interface_state_check,
                             name = self.failed_interfaces.keys())
            if WEBEX_ROOM:
                aetest.loop.mark(self.interface_state_check_webex,name = self.failed_interfaces.keys())
            self.failed('Some interfaces are not connected')
        else:
            self.passed('No interfaces are not connected')
 
    @aetest.test
    def interface_state_check(self, name = None):
        if name is None:
            self.skipped('All interfaces are connected or administratively down')
        else:
            self.failed(f'Interface { name } { self.failed_interfaces[name] } is not connected or administratively down')

    @aetest.test
    def interface_state_check_webex(self, name = None):
        if name is None:
           self.skipped('All interfaces are connected or administratively down') 
        else:
            template_dir = Path(__file__).resolve().parent
            env = Environment(loader=FileSystemLoader(str(template_dir)))
            adaptive_card_template = env.get_template('failed_test_show_interface_adaptive_card.j2')
            adataptive_card_output = adaptive_card_template.render(roomid = WEBEX_ROOM, interface=name, hostname=self.hostname, failure=self.failed_interfaces[name], test="state")
            webex_adaptive_card_response = requests.post('https://webexapis.com/v1/messages', data=adataptive_card_output, headers={"Content-Type": "application/json", "Authorization": f"Bearer { WEBEX_TOKEN }" })
            log.info('The POST to WebEx had a response code of ' + str(webex_adaptive_card_response.status_code) + 'due to' + webex_adaptive_card_response.reason)
if __name__ == '__main__':  # pragma: no cover
    aetest.main()