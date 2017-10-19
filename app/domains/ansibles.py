#!coding:utf-8
from config import Config
import os,re,subprocess
from app.common.ApiResponse import ResposeStatus
from random import choice
from app import logger
import threading
from app.models.ipPool import ipPool
from app.common.httpHelp import  httpRequset
from app.models.operationLog import operationLog
from app import create_app
from app.common.ansible_sdk import *
app=create_app()
class baseWorker:
    def __init__(self,playBookName,ips=[],params={},callBack=''):
        self.playBookName=playBookName
        self.callBack=callBack
        self.ips=ips
        self.params=params
class kvmWorker(baseWorker):
    def checkparams(self,data,playbookName):
        error = False
        message =''
        params={
            'createKvmVm': [
                # {
                #     'name': 'env',
                #     'rule':'TEST|DEV|BETA|V5'
                # },
                {
                    'name': 'vmName'
                },{
                    'name': 'vmIP'
                }
            ],
            'stopKvmVm': [
                {
                    'name': 'vmName'
                }
            ],
            'startKvmVm': [
                {
                    'name':'vmName'
                }
            ],
            'restartKvmVm': [
                {
                    'name': 'vmName'
                }
            ],
            'deleteKvmVm': [
                {
                    'name': 'vmName'
                }
            ]
        }
        for param in params[playbookName]:
            if not param['name'] in data.keys():
                error = True
                message = 'param {} not found'.format(param['name'])
                logger().error(data)
                return error,message
            if param.has_key('rule'):
                if param['rule']:
                    pattern = re.compile(param['rule'])
                    if not pattern.match(data[param['name']]):
                        logger().error(data)
                        error = True
                        message = 'param {} value does not match pattern:{}'.format(param['name'],param['rule'])
                        return error,message
        return error,message
    def parseparams(self,params):
        defaults={
            'baseImageDir': '/data/basesong',
            'baseImageName': 'song.qcow2',
            'vmMEM': '2048',
            'vmCPU': '1'
        }
        for key,value in defaults.items():
            if key not in params.keys():
                params[key]=value
        return params
    def createVm(self):
        error,message = self.checkparams(self.params,self.playBookName)
        if error:
            return message,ResposeStatus.Fail
        env = self.params['vmName'].split('-')[1]
        self.ips = choice(Config.KVMHOSTS[env])
        self.params = self.parseparams(self.params)
        extraVar=" ".join(["{}={}".format(k,v)for k,v in self.params.items()])
        cmd = "ansible-playbook -i hosts {}/site.yml --extra-vars '{}'".format(self.playBookName,extraVar)
        t = threading.Thread(target=ansibleExcutor, args=(cmd, self.callBack,self.playBookName,self.params,self.ips))
        t.start()
        return '',ResposeStatus.Success
    def operationVm(self):
        error,message = self.checkparams(self.params,self.playBookName)
        if error:
            return message,ResposeStatus.Fail
        q=ipPool.query.filter(ipPool.name==self.params['vmName']).first()
        if q:
            self.ips = q.hostServer
            extraVar = " ".join(["{}={}".format(k, v) for k, v in self.params.items()])
            cmd = "ansible-playbook -i hosts site.yml --extra-vars '{}'".format(extraVar)
            print cmd
            # p = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # res,_ = p.communicate()
            # print res
            t = threading.Thread(target=ansibleExcutor, args=(cmd, self.callBack,self.playBookName,self.params,self.ips))
            t.start()
            return "work start",ResposeStatus.Success
        else:
            return "vmName not found",ResposeStatus.Fail
class userAddWorker(baseWorker):
    def startWorker(self):
        extraVar = " ".join(["{}={}".format(k, v) for k, v in self.params.items()])
        cmd = "ansible-playbook -i hosts site.yml --extra-vars '{}'".format(extraVar)
        status,data = ansibleExcutor(cmd, self.callBack, self.playBookName, self.params, self.ips)
        if status == 0:
            return data, ResposeStatus.Success
        else:
            return data,ResposeStatus.Fail
def ansibleWoker(playBookName,ips=[],params={},callBack=''):
    if not playBookName in os.listdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'playbooks')):
        return "指定playbook不存在",ResposeStatus.Fail
    if playBookName in ['stopKvmVm','startKvmVm','restartKvmVm','deleteKvmVm','createKvmVm']:
        worker = kvmWorker(playBookName,ips,params,callBack)
        if playBookName == 'createKvmVm':
            return worker.createVm()
        if playBookName in ['stopKvmVm','startKvmVm','restartKvmVm','deleteKvmVm'] :
            return worker.operationVm()
    if playBookName == 'useradd':
        worker = userAddWorker(playBookName,ips,params,callBack)
        return worker.startWorker()
    else:
        pass
        #todo other playBookType



def ansibleExcutor(cmd,callback,*args,**kwargs):
    playBookName,params,ip = args
    if isinstance(ip,list):
        res = [{"hostname": i, "username": "root"} for i in ip]
    else:
        res = [{"hostname": ip, "username": "root"}]
        ip = [ip]
    tqm = ansibleRunner(res, host_list=ip)
    res = tqm.run_playbook(playbookName=playBookName,extra_vars=params)
    if res['failed'] or res['unreachable']:
        status = 1
    else:
        status = 0
    with app.app_context():
        log=operationLog()
        log.status = status
        log.cmd = cmd
        log.result = json.dumps(res)
        log.save()
    if callback:
        if playBookName  in ['createKvmVm','startKvmVm','stopKvmVm','deleteKvmVm','restartKvmVm']:
            if status == 0:
                data={
                    'hostServer': ip,
                    'result': '{} {} {} success'.format(playBookName,params['vmName'],params['vmIP']),
                    'params': params,
                    'playBookName': playBookName
                }
            else:
                data={
                    'hostServer': ip,
                    'result': '{} {} {} failed'.format(playBookName,params['vmName'],params['vmIP']),
                    'params': params,
                    'message': json.dumps(res),
                    'playBookName': playBookName
                }
            r=httpRequset(url=callback,uri='',method='post',jsons=data)
            print r.status_code
        #todo callback
    if status == 0:
        if playBookName == 'useradd':
            result =  '{} {} on {} success'.format(playBookName,params['login_name'],' '.join(ip))
        if playBookName in ['createKvmVm', 'startKvmVm', 'stopKvmVm', 'deleteKvmVm', 'restartKvmVm']:
            result = '{} {} success'.format(playBookName,' '.join(ip))
        data = {
                'server': ip,
                'result': result,
                'params': params,
                'playBookName': playBookName
        }
    if status == 1:
        if playBookName == 'useradd':
            if res['unreachable']:
                result = '{} {} on {} failed'.format(playBookName, params['login_name'], res['unreachable'].keys()[0])
                message = res['unreachable'].values()[0]
            if res['failed']:
                result = '{} {} on {} failed'.format(playBookName, params['login_name'], res['failed'].keys()[0])
                message = res['failed'].values()[0]
        if playBookName in ['createKvmVm', 'startKvmVm', 'stopKvmVm', 'deleteKvmVm', 'restartKvmVm']:
            if res['unreachable']:
                result = '{} {} failed'.format(playBookName, res['unreachable'].keys()[0])
                message = res['unreachable'].values()[0]
            if res['failed']:
                result = '{} {} failed'.format(playBookName, res['failed'].keys()[0])
                message = res['failed'].values()[0]
        data = {
            'server': ip,
            'result': result,
            'params': params,
            'message': message,
            'playBookName': playBookName
        }
    print status,data
    return status,data

def ansibleAdHoc(moduleName,params,ips):
    res=[{"hostname":ip,"username":"root"}for ip in ips]
    tqm = ansibleRunner(res,host_list=ips)
    result = tqm.run(host_list=ips,module_name=moduleName,module_args=params)
    return result,ResposeStatus.Success