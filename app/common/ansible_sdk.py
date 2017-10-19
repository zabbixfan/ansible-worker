#!/usr/bin/env python3
# coding=utf-8
import json,sys
import os
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.inventory.group import Group
from ansible.inventory.host import Host
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars import VariableManager
from collections import namedtuple
from ansible.executor.playbook_executor import PlaybookExecutor
from config import Config
from ansible.utils.color import colorize, hostcolor

class ResultsCollector(CallbackBase):
    """
    Reference: https://github.com /ansible/ansible/blob/v2.0.0.2-1/lib/ansible/plugins/callback/default.py
    """
    def __init__(self, *args, **kwargs):
        super(ResultsCollector, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}
        self.host_skipped = {}

    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()] = result
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if delegated_vars:
            self._display.display("fatal: [%s -> %s]: UNREACHABLE! => %s" % (result._host.get_name(), delegated_vars['ansible_host'], self._dump_results(result._result)), color='red')
        else:
            self._display.display("fatal: [%s]: UNREACHABLE! => %s" % (result._host.get_name(), self._dump_results(result._result)), color='red')

    def v2_runner_on_ok(self, result, *args, **kwargs):
        if result._host.get_name()not in self.host_ok.keys():
            self.host_ok[result._host.get_name()]=[]
        self.host_ok[result._host.get_name()].append(result)
        self._clean_results(result._result, result._task.action)
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if result._task.action == 'include':
            return
        elif result._result.get('changed', False):
            if delegated_vars:
                msg = "changed: [%s -> %s]" % (result._host.get_name(), delegated_vars['ansible_host'])
            else:
                msg = "changed: [%s]" % result._host.get_name()
            color = 'yellow'
        else:
            if delegated_vars:
                msg = "ok: [%s -> %s]" % (result._host.get_name(), delegated_vars['ansible_host'])
            else:
                msg = "ok: [%s]" % result._host.get_name()
            color = 'green'

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:

            if (self._display.verbosity > 0 or '_ansible_verbose_always' in result._result) and not '_ansible_verbose_override' in result._result:
                msg += " => %s" % (self._dump_results(result._result),)
            self._display.display(msg, color=color)

        self._handle_warnings(result._result)

    def v2_runner_on_failed(self, result, *args, **kwargs):
        self.host_failed[result._host.get_name()] = result
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if 'exception' in result._result:
            if self._display.verbosity < 3:
                # extract just the actual error message from the exception text
                error = result._result['exception'].strip().split('\n')[-1]
                msg = "An exception occurred during task execution. To see the full traceback, use -vvv. The error was: %s" % error
            else:
                msg = "An exception occurred during task execution. The full traceback is:\n" + result._result['exception']

            self._display.display(msg, color='red')

            # finally, remove the exception from the result so it's not shown every time
            del result._result['exception']

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            if delegated_vars:
                self._display.display("fatal: [%s -> %s]: FAILED! => %s" % (result._host.get_name(), delegated_vars['ansible_host'], self._dump_results(result._result)), color='red')
            else:
                self._display.display("fatal: [%s]: FAILED! => %s" % (result._host.get_name(), self._dump_results(result._result)), color='red')

        if result._task.ignore_errors:
            self._display.display("...ignoring", color='cyan')

    def v2_runner_on_skipped(self,result):
        self.host_skipped[result._host.get_name()] = result
        pass

    def v2_runner_on_no_hosts(self, task):
        print('skipping: no hosts matched')

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._display.banner("TASK [%s]" % task.get_name().strip())
        if self._display.verbosity > 2:
            path = task.get_path()
            if path:
                self._display.display("task path: %s" % path, color='dark gray')
    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        if not name:
            msg = "PLAY"
        else:
            msg = "PLAY [%s]" % name

        print(msg)
    def v2_playbook_on_stats(self, stats):
        self._display.banner("PLAY RECAP")

        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)

            self._display.display(u"%s : %s %s %s %s" % (
                hostcolor(h, t),
                colorize(u'ok', t['ok'], 'green'),
                colorize(u'changed', t['changed'], 'yellow'),
                colorize(u'unreachable', t['unreachable'], 'red'),
                colorize(u'failed', t['failures'], 'red')),
                screen_only=True
            )

            self._display.display(u"%s : %s %s %s %s" % (
                hostcolor(h, t, False),
                colorize(u'ok', t['ok'], None),
                colorize(u'changed', t['changed'], None),
                colorize(u'unreachable', t['unreachable'], None),
                colorize(u'failed', t['failures'], None)),
                log_only=True
            )

        self._display.display("", screen_only=True)

class MyInventory(Inventory):

    def __init__(self, resource, loader, variable_manager, host_list=['']):
        """
        resource的数据格式是一个列表字典，比如
            {
                "group1": {
                    "hosts": [{"hostname": "10.10.10.10", "port": "22", "username": "test", "password": "mypass"}, ...],
                    "vars": {"var1": value1, "var2": value2, ...}
                }
            }
        如果你只传入1个列表，这默认该列表内的所有主机属于my_group组,比如
            [{"hostname": "10.10.10.10", "port": "22", "username": "test", "password": "mypass"}, ...]
        """
        super(MyInventory, self).__init__(loader=loader, variable_manager=variable_manager, host_list=host_list)
        self.resource = resource
        self.gen_inventory()

    def my_add_group(self, hosts, groupname, groupvars=None):
        """
        add hosts to a group
        """
        my_group = Group(name=groupname)

        # if group variables exists, add them to group
        if groupvars:
            for key, value in groupvars.items():
                my_group.set_variable(key, value)

        # add hosts to group
        for host in hosts:
            # set connection variables
            hostname = host.get("hostname")
            hostip = host.get('ip', hostname)
            hostport = host.get("port")
            username = host.get("username")
            password = host.get("password")
            ssh_key = host.get("ssh_key")
            my_host = Host(name=hostname, port=hostport)
            my_host.set_variable('ansible_ssh_host', hostip)
            my_host.set_variable('ansible_ssh_port', hostport)
            my_host.set_variable('ansible_ssh_user', username)
            my_host.set_variable('ansible_ssh_pass', password)
            my_host.set_variable('ansible_ssh_private_key_file', ssh_key)

            # set other variables
            for key, value in host.items():
                if key not in ["hostname", "port", "username", "password"]:
                    my_host.set_variable(key, value)
            # add to group
            my_group.add_host(my_host)

        self.add_group(my_group)

    def gen_inventory(self):
        """
        add hosts to inventory.
        """
        if isinstance(self.resource, list):
            self.my_add_group(self.resource, 'default_group')

        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.iteritems():
                self.my_add_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))

class Options(object):
    '''
        用于替换ansible的命令行参数
    '''
    def __init__(self, verbosity=None, inventory=None, listhosts=None, subset=None, module_paths=None, extra_vars=None,
                 forks=None, ask_vault_pass=None, vault_password_files=None, new_vault_password_file=None,
                 output_file=None, tags=None, skip_tags=None, one_line=None, tree=None, ask_sudo_pass=None, ask_su_pass=None,
                 sudo=None, sudo_user=None, become=False, become_method='sudo', become_user='root', become_ask_pass=None,
                 ask_pass=None, private_key_file=None, remote_user=None, connection=None, timeout=None, ssh_common_args=None,
                 sftp_extra_args=None, scp_extra_args=None, ssh_extra_args=None, poll_interval=None, seconds=None, check=None,
                 syntax=None, diff=None, force_handlers=None, flush_cache=None, listtasks=None, listtags=None, module_path=None):
        self.verbosity = verbosity
        self.inventory = inventory
        self.listhosts = listhosts
        self.subset = subset
        self.module_paths = module_paths
        self.extra_vars = extra_vars
        self.forks = forks
        self.ask_vault_pass = ask_vault_pass
        self.vault_password_files = vault_password_files
        self.new_vault_password_file = new_vault_password_file
        self.output_file = output_file
        self.tags = tags
        self.skip_tags = skip_tags
        self.one_line = one_line
        self.tree = tree
        self.ask_sudo_pass = ask_sudo_pass
        self.ask_su_pass = ask_su_pass
        self.sudo = sudo
        self.sudo_user = sudo_user
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.become_ask_pass = become_ask_pass
        self.ask_pass = ask_pass
        self.private_key_file = private_key_file
        self.remote_user = remote_user
        self.connection = connection
        self.timeout = timeout
        self.ssh_common_args = ssh_common_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.ssh_extra_args = ssh_extra_args
        self.poll_interval = poll_interval
        self.seconds = seconds
        self.check = check
        self.syntax = syntax
        self.diff = diff
        self.force_handlers = force_handlers
        self.flush_cache = flush_cache
        self.listtasks = listtasks
        self.listtags = listtags
        self.module_path = module_path

class ansibleRunner(object):
    """
    This is a General object for parallel execute modules.
    """

    def __init__(self, resource,host_list=[],*args, **kwargs):
        self.resource = resource
        self.inventory = None
        self.variable_manager = None
        self.loader = None
        self.options = None
        self.passwords = None
        self.callback = None
        self.host_list=host_list
        self.__initializeData()

    def __initializeData(self):
        """
        初始化ansible
        """
        Options = namedtuple('Options',
                             ['listtags', 'listtasks', 'listhosts', 'syntax', 'connection', 'module_path', 'forks',
                              'remote_user', 'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
                              'scp_extra_args', 'become', 'become_method', 'become_user', 'verbosity', 'check','timeout'])

        # initialize needed objects
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.options = Options(listtags=False, listtasks=False, listhosts=False, syntax=False, connection='ssh',
                          module_path=None, forks=100, remote_user='root', private_key_file=None, ssh_common_args=None,
                          ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, become=True,
                          become_method='sudo', become_user='root', verbosity=0, check=False,timeout=2)

        self.passwords = dict(sshpass=None, becomepass=None)
        self.inventory = MyInventory(self.resource, self.loader, self.variable_manager,self.host_list)
        self.variable_manager.set_inventory(self.inventory)

    def run(self, host_list, module_name, module_args):
        """
        run module from andible ad-hoc.
        module_name: ansible module_name
        module_args: ansible module args
        """
        # create play with tasks
        play_source = dict(
            name="Ansible Play",
            hosts=host_list,
            gather_facts='no',
            tasks=[dict(action=dict(module=module_name, args=module_args))]
        )
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

        # actually run it
        tqm = None
        self.results_callback = ResultsCollector()

        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
            )
            tqm._stdout_callback = self.results_callback
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
        # tqm = None
        return self.get_result()

    def run_playbook(self,playbookName,extra_vars={}):
        """
        run ansible palybook
        """

        #     self.options=self.options._replace(tags=[tags])
        filename = os.path.join(Config.BASE_DIR,playbookName,'site.yml')  # playbook的路径
        try:
            if not os.path.exists(filename):
                print('%s not exist ' % filename)
                sys.exit()
            filenames=[filename]
            self.variable_manager.extra_vars = extra_vars
            # actually run it

            executor = PlaybookExecutor(
                playbooks=filenames, inventory=self.inventory, variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options, passwords=self.passwords,
            )
            self.results_callback = ResultsCollector()
            executor._tqm._stdout_callback = self.results_callback
            executor.run()
        except Exception as e:
            print("run_playbook:%s" % e)
        return self.get_result()

    def get_result(self):
        self.result_all = {'success': {}, 'failed': {}, 'unreachable': {}}
        # print result_all
        # print dir(self.results_callback)
        for host, results in self.results_callback.host_ok.items():
            if host not in self.result_all['success'].keys():
                self.result_all['success'][host]=[]
            for result in results:
                if result._result.has_key('cmd'):
                    self.result_all['success'][host].append({'taskName':result._task.name,'taskResult':{'cmd':result._result['cmd'],'stdout':result._result['stdout'],'changed':result._result['changed']}})
                else:
                    delKey= ['_ansible_parsed','_ansible_no_log','invocation','_ansible_verbose_always']
                    for key in delKey:
                        if result._result.has_key(key):
                            result._result.pop(key)
                    self.result_all['success'][host].append({'taskName':result._task.name,'taskResult':result._result})

        for host, result in self.results_callback.host_failed.items():
            if 'msg' in result._result.keys():
                self.result_all['failed'][host] = {'taskName':result._task.name,'taskResult':result._result['msg']}
            else:
                self.result_all['failed'][host] = {'taskName':result._task.name,'taskResult':result._result['stderr']}

        for host, result in self.results_callback.host_unreachable.items():
            self.result_all['unreachable'][host] = {'taskName': result._task.name, 'taskResult': result._result['msg']}
        if
        return self.result_all

if __name__ == '__main__':
    res = [{"hostname": "192.168.4.119","username":"root"},{"hostname": "192.168.100.43","username":"root"}]
    tqm = ansibleRunner(res,host_list=['192.168.100.43'])
    #print tqm.run_playbook(playbookName='stopKvmVm',extra_vars={'vmName':'BrokerService-TEST-4.48','vmIP':'192.168.4.183'})
    #print tqm.run(host_list=['192.168.4.119'],module_name='virt',module_args={'name':'DataCenter-TEST-4.49','command':'status'})
    print tqm.run(host_list=['192.168.100.43'],module_name='shell',module_args='whoami')
