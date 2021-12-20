import os
import yaml
import socket
import time
import logging
import datetime
import dns.resolver
import sys
from os import path

RESOLV_FAILOVER_CONFIG_NAME = "resolv-conf-failover-config.yml"

def get_config():
    return resolv_failover_config()

class resolv_failover_config:
    file_path = ""
    resolv_conf_path = ""
    ping_dns_names = []
    health_check_interval = 0
    retry_interval = 0
    log_level = ""

    def __init__(self, file_name=RESOLV_FAILOVER_CONFIG_NAME):
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            self.file_path = path.join(sys._MEIPASS, file_name)
        else:
            self.file_path = path.join(path.dirname(__file__), file_name)
        self.read_config()

    def read_config(self):
        with open(self.file_path) as file:
            try:
                yaml_data = yaml.safe_load(file)
                self.resolv_conf_path = yaml_data["resolv_conf_path"]
                self.health_check_interval = yaml_data["health_check_interval"]
                self.ping_dns_names = yaml_data["ping_dns_names"]
                self.retry_interval = yaml_data["retry_interval"]
                self.log_level = yaml_data["log_level"]
            except:
                log("error", f"reading config {self.file_path} is failed.")
                exit(1)

        if self.resolv_conf_path == "":
            raise ValueError("resolv_conf_path is not set.")
        if self.health_check_interval == 0:
            raise ValueError("health_check_interval is not set.")
        if len(self.ping_dns_names) == 0:
            raise ValueError("ping_dns_name is not set.")
        # retry_interval == 0 => no retry
        log("info", f"reading config {self.file_path} is success.")

def dnsserver_healthy_check_loop(config):
    log("info", "start health check loop.")
    while(True):
        log("debug", "start turn on health check.")
        for dns_name in config.ping_dns_names:
            log("debug", f"health check with {dns_name}.")
            if be_able_to_resolv_name(dns_name, get_nameserver_addrs(config.resolv_conf_path)):
                log("debug", f"health check is success.")
                continue
            log("warning", f"resolving {dns_name} is failed. retry after {config.retry_interval} second.")
            time.sleep(config.retry_interval)
            if not be_able_to_resolv_name(dns_name, get_nameserver_addrs(config.resolv_conf_path)):
                log("error", f"retrying is failed. rewrite {config.resolv_conf_path}.")
                rewrite_resolv_conf(config.resolv_conf_path)
                break
            log("info", "retrying is success.")
        log("debug", f"sleep {config.health_check_interval} for next health check.")
        time.sleep(config.health_check_interval)

def be_able_to_resolv_name(dns_name, nameserver_ips):
    if len(nameserver_ips) == 0:
        return False
    my_resolver = dns.resolver.Resolver()
    my_resolver.nameservers = [nameserver_ips[0]]
    try:
        if len(my_resolver.query(dns_name)) == 0:
            return False
    except:
        log("warning", f"exception is raised when resolving name.")
        return False
    return True

def get_nameserver_addrs(resolv_conf_path):
    nameservers = []
    with open(resolv_conf_path) as resolv_conf:
        for line in resolv_conf:
            if "nameserver " not in line:
                continue
            ip_addr = line.split(" ")[1].strip(" ").replace("\n", '')
            nameservers.append(ip_addr)
    if len(nameservers) == 0:
        log("warning", "nameserver is nothing.")
        return False
    return nameservers


def rewrite_resolv_conf(resolv_conf_path):
    log("debug", "rewriting is started.")
    nameservers = get_nameserver_addrs(resolv_conf_path)
    new_nameservers = []
    nameserver_max_index = len(nameservers) - 1
    nameserver_index = 0
    new_conf_str = ""
    with open(resolv_conf_path, "r+") as resolv_conf:
        for line in resolv_conf:
            if "nameserver " not in line:
                new_conf_str += f"{line}"
                continue
            if nameserver_index > nameserver_max_index:
                log("warning", "resolv config file may be changed within rewriting. so, nothing to do.")
                return
            # insert_nameserver_index = nameserver_max_index - nameserver_index
            insert_nameserver_index = nameserver_index + 1 - (nameserver_max_index + 1) * int(nameserver_index / nameserver_max_index)
            log("debug", f"nameserver_max_index: {nameserver_max_index}")
            log("debug", f"nameserver_index: {nameserver_index}")
            log("debug", f"insert_nameserver_index: {insert_nameserver_index}")
            new_conf_str += f"nameserver {nameservers[insert_nameserver_index]}\n"
            new_nameservers.append(nameservers[insert_nameserver_index])
            nameserver_index+=1
    with open(f"{resolv_conf_path}.pre", "w+") as new_resolv_conf:
        try:
            new_resolv_conf.write(new_conf_str)
        except:
            log("error", f"creating {resolv_conf_path}.pre is failed.")
            return
        log("debug", f"resolv conf pre-file {resolv_conf_path}.pre is created.")

    nowtime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    try:
        os.rename(resolv_conf_path, f"{resolv_conf_path}.save.{nowtime}") 
        os.rename(f"{resolv_conf_path}.pre", resolv_conf_path)
    except:
        log("error", f"replacing new config to {resolv_conf_path} is failed.")
        return
    log("info", f"rewriting is success. order is old: {nameservers} new: {new_nameservers}")

def logging_configure(config):
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    if config.log_level not in log_levels.keys():
        log("error", f"specified log level {config.log_level} is not invalid.")
        exit(1)
    logger = logging.getLogger()
    logger.setLevel(log_levels[config.log_level])
    log("info", f"log level is {config.log_level}({log_levels[config.log_level]})")

def log(level, msg):
    if level == "debug":
        logging.debug(msg)
    if level == "info":
        logging.info(msg)
    if level == "warning":
        logging.warning(msg)
    if level == "error":
        logging.error(msg)

def main():
    logging.basicConfig(format="%(asctime)s <%(levelname)s> %(message)s", level=logging.INFO)
    config = get_config()
    logging_configure(config)
    dnsserver_healthy_check_loop(config)

if __name__ == '__main__':
    main()
