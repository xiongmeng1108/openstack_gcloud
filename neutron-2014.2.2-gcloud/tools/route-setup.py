#!/usr/bin/python
import subprocess
import re
import os
interface_info_list=[]

exchange_mask = lambda mask: sum(bin(int(i)).count('1') \
                                 for i in mask.split('.'))


def get_gateway(interface_name):
    subp=subprocess.Popen("route -n", shell=True,stdout=subprocess.PIPE)
    line=subp.stdout.readline()
    gateway=None
    while line:
        line_list=line.split()
        if line_list[0]=="0.0.0.0" and line_list[7]==interface_name:
            gateway=line_list[1]
            break
        line=subp.stdout.readline()
    return  gateway




def get_network(ip_list, netmask_list, prefix):
    network=str()
    for k in range(4):
        network+=str(int(netmask_list[k])&int(ip_list[k]))
        if k!=3:
            network+="."
    network+=prefix
    return network

def exec_command(command):
    os.system(command)

subp=subprocess.Popen("ifconfig", shell=True,stdout=subprocess.PIPE)
line=subp.stdout.readline()
while line:
    interface=re.findall("eth[0-9]{1,3}", line)
    if interface:
        interface_info={"name": interface[0]}
        interface_info['gateway']=get_gateway(interface[0])
        ip_info=subp.stdout.readline()
        list=ip_info.split()
        interface_info['ip'] = list[1]
        prefix=str(exchange_mask(list[3]))
        network=get_network(list[1].split("."),list[3].split("."),"/"+prefix)
        interface_info['network']=network
        interface_info_list.append(interface_info)
    line=subp.stdout.readline()
print interface_info_list

for  interface_info in interface_info_list:
    #flush  #ip rule del  from 40.40.40.146  table eth0
    exec_command("ip route flush table %s" %interface_info["name"])
    exec_command("ip rule del  from %s table %s" %(interface_info['ip'],interface_info["name"]))
    # add ip  route add default  via  40.40.40.1  dev eth0  table  eth0
    if interface_info['gateway']:
        exec_command("ip  route add default  via %s dev %s table %s"
                     %(interface_info['gateway'],interface_info["name"],interface_info["name"]))

    #ip  route add  40.40.40.0/24 dev eth0 src 40.40.40.146 table eth0
    exec_command("ip route add %s dev %s src %s table %s"
                 %(interface_info['network'],interface_info["name"],interface_info['ip'],interface_info["name"]))

    # ip rule add from 40.40.40.146  table eth0
    exec_command("ip rule add from %s table %s" %(interface_info['ip'],interface_info["name"]))







