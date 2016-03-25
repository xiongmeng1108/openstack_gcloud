__author__ = 'luoyb'
import socket
from binascii import hexlify
from binascii import  unhexlify
from neutron.agent.linux import utils
import  re
from neutron.openstack.common import log as logging
import json
import os


LOG = logging.getLogger(__name__)


class TC_Operation(object):
    def __init__(self):
          self.root_helper="sudo  neutron-rootwrap /etc/neutron/rootwrap.conf"

    def _add_ingress_qdisc(self,nsname=None,devname=None):
        LOG.debug(_('_add_ingress_qdisc in call,nsname %s,devname %s'%(nsname,devname)))
        """
        :param nsname: qrouter-f9accec4-0fc1-4ab9-989e-6eff21402aaf
        :param devname: qg-2ef7de9d-7b
        :return:None
        """
        cmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","qdisc","add","dev",devname,"ingress"])
        utils.execute(cmd,self.root_helper)
    def _add_ingress_filter(self,nsname=None,devname=None,ingress_size=None):
        """
        :param nsname:
        :param devname:
        :param ingress_size:375000Kbit
        :return:
        """
        LOG.debug(_('_add_ingress_filter in call'))
        cmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","filter","add","dev",devname,"protocol",
                    "all","parent","ffff:","u32","match","ip", "dst", "0.0.0.0/0" ,
                   "police", "rate",  ingress_size,"burst","512kbit", "mtu", "162kbit","drop", "flowid",":1"])
        utils.execute(cmd,self.root_helper)

    def delete_ingress_qdisc(self,nsname=None,devname=None):
        """

        :param nsname:
        :param devname:
        :return:
        """
        LOG.debug(_('delete_ingress_qdisc in call'))
        is_exist_ingress_qdisc=self.check_qdisc(nsname,devname,"ingress ffff:")
        if is_exist_ingress_qdisc != -1:
          cmd=[]
          if nsname is not None:
              nscmd=["ip","netns","exec",nsname]
              cmd.extend(nscmd)
          cmd.extend(["tc","qdisc","del","dev",devname,"ingress"])
          utils.execute(cmd,self.root_helper)

    def add_ingress_limit(self,nsname=None,devname=None,ingress_size='375000Kbit'):
        """

        :param nsname:
        :param devname:
        :param ingress_size:375000Kbit
        :return:
        """
        LOG.debug(_('add_ingress_limit in call'))
        #check ingress qdisc is exist
        is_exist_ingress_qdisc=self.check_qdisc(nsname,devname,"ingress ffff:")
        if is_exist_ingress_qdisc != -1:
            #check exist ingress is the same ingress_size
            exist_ingress_size=self._get_ingress(nsname,devname)
            if cmp(ingress_size,exist_ingress_size):#not the same
                  self.delete_ingress_qdisc(nsname,devname)
            else:
                return
        #add ingress qdisc
        self._add_ingress_qdisc(nsname,devname)
        #add ingress filter
        self._add_ingress_filter(nsname,devname,ingress_size)

    def _get_ingress(self,nsname,devname):
        """
        get in gress band
        :param nsname:
        :param devname:
        :return: 375000Kbit or None
        """
        LOG.debug(_('_get_ingress in call'))
        cmd=[]
        nscmd=[]
        filter_str=None
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","filter","show","dev",devname,"parent","ffff:"])
        filter_str=utils.execute(cmd,self.root_helper)
        if filter_str:
            pattern =re.compile("rate (\d*)Kbit")
            res=re.search(pattern,filter_str)
            if res:
                 return  res.group()[4:]

        return  None

    def del_qdisc_root(self,nsname=None,devname=None):
        """
        add out gress root qdisc
        :param nsname:
        :param devname:
        :return:
        """
        LOG.debug(_('del_qdisc_root in call'))
        cmd=[]
        nscmd=[]
        if nsname is not None:
            is_exist=self.check_qdisc(nsname,devname,"htb 1:")
            if is_exist ==-1:
                return 0
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","qdisc","del","dev",devname,"root"])
        rc=utils.execute(cmd,self.root_helper)
        return rc
    def add_root_and_class(self,nsname=None,devname=None,default_limit="1kbit"):
        """
        add outgress root ,default limit band , add root qdisc and root class,first class 1000 mbit,root class 1:1
        :param nsname:
        :param devname:
        :param default_limit: 1kbit
        :return:
        """
        LOG.debug(_('add_root_and_class in call,nsname %s ,devname %s,default_limit %s' %(nsname,devname,default_limit)))
        is_exist=self.check_qdisc(nsname,devname,"htb 1:")
        if is_exist !=-1:
            is_exist=self.check_qdisc(nsname,devname,"default 9")
            if is_exist==-1:#qdisc has not default limit
                self.del_qdisc_root(nsname,devname)
        #print is_exist
        cmd=[]
        nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        if is_exist == -1:
           cmd.extend(["tc","qdisc","add","dev",devname,"root","handle","1:","htb","default",9])
           #print(cmd)
           rc=utils.execute(cmd,self.root_helper)
           self.add_or_update_class(nsname,devname,"1:1","1:9",default_limit,default_limit)
           self.add_leaf(nsname,devname,"1:9")
           #print("result:"+rc)
        #add  root class
           self.add_or_update_class(nsname,devname,"1:","1:1","10240mbit","10240mbit")
        #add default class id


    def add_or_update_class(self,nsname=None,devname=None,parent_classid=None,curent_classid=None,rate=None,ceil=None ):
        """
        add or update class  qos  bandwidth
        :param nsname:
        :param devname:
        :param parent_classid: "1:1"
        :param curent_classid: "1:10"
        :param rate: 10000Kbit
        :param ceil:10000Kbit
        :return:0 :class sfq not exist
        """

        LOG.debug(_('add_or_update_class in call,nsname %s,devname %s,curent_class %s,rate %s' %(nsname,devname,curent_classid,rate)))
        cmd=[]
        nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        is_exist=self.check_class(nsname,devname,"class htb "+curent_classid)
        #print "add_class"
        #print is_exist
        if is_exist==-1 :#class not exist
           cmd.extend(["tc","class","add","dev",devname,"parent",parent_classid,"classid",curent_classid,"htb","rate",rate,"ceil",ceil])
           utils.execute(cmd,self.root_helper)
           return 0
        else:#class is exist ,update class rate
           cmd.extend(["tc","class","replace","dev",devname,"parent",parent_classid,"classid",curent_classid,"htb","rate",rate,"ceil",ceil])
           utils.execute(cmd,self.root_helper)
        return 1

    def add_leaf(self,nsname=None,devname=None,curent_classid=None ):
        """
          add qdisc info ,add_leaf
        :param nsname:
        :param devname:
        :param curent_classid: "1:10"
        :return:
        """

        cmd=[]
        nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
        cmd.extend(nscmd)
        cmd.extend(["tc","qdisc","add","dev",devname,"parent",curent_classid,"sfq","perturb","10"])
        utils.execute(cmd,self.root_helper)

    def add_flow(self,nsname=None,devname=None,parentid=None,src_ip=None,classid=None):
        #ip netns exec qrouter-b90a765b-d4ee-4ca9-aee8-79387537a3a7
        #tc filter add  dev qg-fca39d8c-1a protocol ip parent 1: u32 match ip src  20.251.36.102 flowid 1:10
        """

        :param nsname:
        :param devname:
        :param parentid: "1:"
        :param src_ip: "192.168.10.100"
        :param classid: "1:10"
        :return:
        """
        LOG.debug(_('add_flow in call,nsname %s,devname %s,parentid %s ,src_ip %s,class_id %s'%(nsname,devname,parentid,src_ip,classid)))
        cmd=[]
        nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        check_rc= self.check_flow(nsname,devname,classid,src_ip)
        if check_rc is False:
             #print "add new flow"
             cmd.extend(["tc","filter","add","dev",devname,"protocol","ip","parent",parentid,"u32","match","ip","src",src_ip,"flowid",classid])
             utils.execute(cmd,self.root_helper)
        # elif check_rc == -2:
        #      #print "delete old flow"
        #      self.del_flow(nsname,devname,classid)
        #      cmd.extend(["tc","filter","add","dev",devname,"protocol","ip","parent",parentid,"u32","match","ip","src",src_ip,"flowid",classid])
        #      utils.execute(cmd,self.root_helper)
        #      #print "add new flow"

    def _get_flow_grep_src(self,src_ip):
        """

        :param src_ip: "192.168.10.100"
        :return:
        """
        hexstr=hexlify(socket.inet_aton(src_ip))+"/ffffffff"

        #print hexstr
        return hexstr

    def check_qdisc(self,nsname=None,devname=None,grep_src=None):
        """

        :param nsname:
        :param devname:
        :param grep_src:
        :return: -1  not exist  ,other exist
        """
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","qdisc","show","dev",devname])
        output=utils.execute(cmd,self.root_helper)
        if output:
                return output.find(grep_src)
        return -1

    def check_class(self,nsname=None,devname=None,grep_src=None):
        """

        :param nsname:
        :param devname:
        :param grep_src:
        :return: -1 not exist,other exist
        """
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","class","show","dev",devname])
        output=utils.execute(cmd,self.root_helper)
        if output:
                return output.find(grep_src)
        return -1

    def _find_all_classid_filters(self,output,class_id):
        """

        :param output:
        :param class_id:"1:10"
        :return: eg [('49151', '801', '800', '801', '0'), ('49152', '801', '800', '801', '0')]
        """
        pattern =re.compile("parent 1: protocol ip pref (\d*) u32 fh ([a-f0-9_]*)::([a-f0-9_]*) order 2048 key ht ([a-f0-9_]*) bkt ([a-f0-9_]*) flowid "+class_id)
        return pattern.findall(output)


    def del_flows(self,nsname,devname,class_id):
        """
        delete all flows of class_id
        :param nsname:
        :param devname:
        :param class_id:"1:10"
        :return:
        """
        LOG.debug(_('del_flows in call, nsname %s,devname %s,class_id %s' %(nsname,devname,class_id)))
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","filter","show","dev",devname])
        output=utils.execute(cmd,self.root_helper)
        filters_groups=self._find_all_classid_filters(output,class_id)
        if filters_groups and len(filters_groups)>0:
            for item in filters_groups:
                cmd=[]
                cmd.extend(nscmd)
                filter_perf=item[0]
                cmd.extend(["tc","filter","del","dev",devname,
                             "parent","1:", "protocol", "ip","pref", filter_perf,"u32"])
                utils.execute(cmd,self.root_helper)


    def _re_match_src_ip_filter(self,output,class_id,src_ip):
        """

        :param output:
        :param src_ip:"192.168.10.100"
        :return: eg[()]
                 ******
        """
        pattern_str="parent 1: protocol ip pref (\d*) u32 fh ([a-f0-9_]*)::([a-f0-9_]*) order 2048 key ht ([a-f0-9_]*) bkt ([a-f0-9_]*) flowid "+class_id+" \n" \
                    +"  match "+str(hexlify(socket.inet_aton(src_ip)))
        pattern =re.compile(pattern_str)
        res=re.search(pattern,output)
        if res:
            return  res.group()
        else:
            return None

    def check_flow(self,nsname=None,devname=None,classid=None,src_ip=None):
        """

        :param nsname:
        :param devname:
        :param classid:"1:10"
        :param src_ip:"196.168.10.100"
        :return:
        """
        LOG.debug(_('check_flow in call,class_id %s src_ip %s'%(classid,src_ip)))
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","filter","show","dev",devname])
        output=utils.execute(cmd,self.root_helper)
        res=self._re_match_src_ip_filter(output,class_id=classid,src_ip=src_ip)
        if res:
            return True
        else:
            return False


    def del_flow(self,nsname = None,devname=None, classid=None,src_ip=None):
        """

        :param nsname:
        :param devname:
        :param classid: "1:10"
        :param src_ip: "192.168.10.100"
        :return:
        """
        LOG.debug(_('del_flow classid %s,src_ip %s'%(classid,src_ip)))
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","filter","show","dev",devname])
        output=utils.execute(cmd,self.root_helper)
        res=self._re_match_src_ip_filter(output,class_id=classid,src_ip=src_ip)
        if res:
            filter_perf_info=res[:res.index(" fh")]
            rule_set=filter_perf_info.split(" ")
            del_cmd=nscmd
            del_cmd.extend(["tc","filter","del","dev",devname])
            del_cmd.extend(rule_set)
            #print rule_set
            output=utils.execute(del_cmd,self.root_helper)

    def del_class(self,nsname,devname,classid):
        """

        :param nsname:
        :param devname:
        :param classid: "1:10"
        :return:
        """
        LOG.debug(_('del_class class_id %s'%(classid)))
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        if self.check_class(nsname,devname,"class htb "+classid)==-1:
            return
        cmd.extend(["tc","class","del","dev",devname,"classid",classid])
        output=utils.execute(cmd,self.root_helper)

    def del_flow_and_class(self,nsname = None,devname=None, classid=None):
        """

        :param nsname:
        :param devname:
        :param classid: "1:10"
        :return:
        """
        LOG.debug(_('del_flow_and_class in call ,nsname %s,devname %s,class_id %s'%(nsname,devname,classid)))
        self.del_flows(nsname,devname,classid)
        self.del_class(nsname,devname,classid)

    def add_class_and_flow(self,nsname = None,devname=None, classid=None,max_rate=None,src_ip=None):
        """

        :param nsname:
        :param devname:
        :param classid:"1:10"
        :param max_rate: "375000Kbit"
        :param src_ip:"192.168.10.100"
        :return:
        """
        LOG.debug(_('add_class_and_flow in call,classid %s,max_rate %s,src_ip %s'%(classid,max_rate,src_ip)))
        #self.add_root_and_class(nsname,devname)
        rc=self.add_or_update_class(nsname,devname,"1:1",classid,max_rate,max_rate)
        if rc==0:
            self.add_leaf(nsname,devname,classid)
        self.add_flow(nsname,devname,"1:",src_ip,classid)

    def _get_all_class_rate(self,nsname,devname):
        """
        :param output:
        :return: {10:2000,11:10000}
        """
        class_rate_dicts={}
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","class","show","dev",devname])
        output=utils.execute(cmd,self.root_helper)
        pattern =re.compile("class htb 1:(\d*) root prio 0 rate (\d*)Kbit")
        res_list= pattern.findall(output)
        if res_list:
            for item in res_list:
             class_rate_dicts.update({int(item[0]):int(item[1])})
        return class_rate_dicts
    def get_class_and_flow(self,nsname,devname,min_classid,max_classid):
        """

        :param nsname:
        :param devname:
        :param min_classid:eg 10
        :param max_classid:eg 30
        :return:{classid1:{"classid":classid1,"max_rate":1000,"src_ips":["ip_address1",""ip_address2]},} 1000 means kbit
        """
        LOG.debug(_('get_class_and_flow in call'))
        cmd=nscmd=[]
        if nsname is not None:
            nscmd=["ip","netns","exec",nsname]
            cmd.extend(nscmd)
        cmd.extend(["tc","filter","show","dev",devname])
        output=utils.execute(cmd,self.root_helper)

        qoss_dict={} #{"classid1":{"classid":"classid1","src_ips":["ip_address1",""ip_address2]},}
        pattern =re.compile("ip pref (\d*) u32 fh ([a-f0-9_]*)::([a-f0-9_]*) order 2048 key ht ([a-f0-9_]*) bkt ([a-f0-9_]*) flowid 1:(\d*) \n"
         +"  match ([a-f0-9_]*)/ffffffff at 12")
        res_list= pattern.findall(output)
        if res_list:
            for item in res_list:
                class_id=int(item[5])
                src_ip=socket.inet_ntoa(unhexlify(item[6]))
                class_dict=qoss_dict.get(class_id)
                if not class_dict:
                     class_dict={"class_id":class_id,"src_ips":[src_ip]}
                     qoss_dict.update({class_id:class_dict})#"classid1":{"classid":"classid1","src_ips":["ip_address1",""ip_address2]}
                else:
                    #update src_ips of class_dict
                    src_ips_list=class_dict.get("src_ips")
                    src_ips_list.append(src_ip)
                    #qoss.append(qos)
        #get classs rate
        class_rate_dicts=self._get_all_class_rate(nsname,devname)
        for key in qoss_dict:
            class_dict=qoss_dict[key]
            class_dict.update({"max_rate":class_rate_dicts.get(key,1)})
        return qoss_dict
        ##print output
        #match_line=None
        #grep_flow_src="flowid 1:"
        # class_dict={} # {"classid":"classid1","src_ips":["ip_address1",""ip_address2]}
        # qos={}
        # class_line=ip_line=line_index=0
        # for line in output.split('\n'):

             # class_index= line.find(grep_flow_src)
             # if class_index!= -1 and  line.find("protocol ip") !=-1 and line.find("u32 ") !=-1 :
             #    #get class_id
             #    classid_str=line[class_index+len(grep_flow_src):]
             #    ##print classid_str
             #    sub_class_id=int(classid_str)
             #    #print sub_class_id
             #    if sub_class_id>=min_classid and sub_class_id<=max_classid:
             #        qos["class_id"]=sub_class_id
             #        class_line=line_index
             #        ##print qos
             # elif line_index-class_line==1:
             #    #print "line"+line
             #    ip_index=line.find("match ")
             #    ip_end_index=line.find("/ffffffff")
             #    if ip_index!=-1 and ip_end_index>ip_index:
             #        hen16_ip=line[ip_index+len("match "):ip_end_index]
             #        src_ip= socket.inet_ntoa(unhexlify(hen16_ip))
             #        class_dict=None
             #        ##print src_ip
             #        class_dict=qoss_dict.get(qos["class_id"])
             #        if not class_dict:
             #            class_dict={"class_id":qos["class_id"],"src_ips":[src_ip]}
             #            qoss_dict.update({qos["class_id"]:class_dict})#"classid1":{"classid":"classid1","src_ips":["ip_address1",""ip_address2]}
             #        else:
             #            #update src_ips of class_dict
             #            src_ips_list=class_dict.get("src_ips")
             #            src_ips_list.add(src_ip)
             #        #qoss.append(qos)
             #    qos={}
             # line_index=line_index+1



class QosLimit(TC_Operation):



    def __init__(self):
        super(QosLimit, self).__init__()
        try:
             self.tc_file_root_path=cfg.CONF.state_path+"/tc"
        except Exception:
            self.tc_file_root_path="/var/lib/neutron/tc"
        if not os.path.exists( self.tc_file_root_path):
            os.makedirs(self.tc_file_root_path)

    def set_tc_file_root_path(self,tc_file_root_path):
        self.tc_file_root_path=tc_file_root_path
    def compare_qos_bind_rate(self,cache_qos_bind,new_qos_bind):
        """
        compare qos bind rate
        :param cache_qos_bind: {"max_rate":"100","ip_srcs":["192.168.10.1","192.168.20.1"]}
        :param new_qos_bind:{"max_rate":"100","src_ips":["192.168.10.1","192.168.20.1"]}
        :return:True or False
        """

        if cache_qos_bind["max_rate"]==new_qos_bind["max_rate"]:
            return True
        else:
            return False
    def compare_and_udpate_qos_bind_src_ips(self,nsname,devname,cache_qos_bind,new_qos_bind):
        """
        compare qos ip src and update filters
        :param cache_qos_bind:{"max_rate":"100","src_ips":["192.168.10.1","192.168.20.1"]}
        :param new_qos_bind:{"max_rate":"100","src_ips":["192.168.10.1","192.168.20.1"]}
        :return:
        """
        LOG.debug(_('compare_and_udpate_qos_bind_src_ips in call'))
        cache_src_ips = cache_qos_bind["src_ips"]
        new_src_ips = new_qos_bind["src_ips"]
        class_id="1:"+str(cache_qos_bind["class_id"])
        #if ip srcs has new ip src,add to tc filter
        for src_ip in new_src_ips:
            if src_ip in cache_src_ips:
                continue
                #print src_ip+" is exist"
            else:
                #print src_ip+" is not exist"
                #add_class_and_flow(self,nsname = None,devname=None, classid=None,max_rate=None,src_ip=None)
                self.add_class_and_flow(nsname,devname,classid=class_id,max_rate=str(new_qos_bind["max_rate"])+"Kbit",src_ip=src_ip)
                LOG.debug(_("add src_ip %s to class_id %d" %(src_ip,cache_qos_bind["class_id"])))
                #print "add " +src_ip +" to tc"
        # if ip src in cache ,but it is not in new ip srcs,now remove it from tc filters
        for src_ip in cache_src_ips:
            if src_ip not in new_src_ips:
                #print src_ip+" is not exist"
                #print "remove " +src_ip +" to tc"
                self.del_flow(nsname,devname,classid=class_id,src_ip=src_ip)
        #update cache ip src to new ip srcs
        cache_src_ips=new_src_ips

    def get_qos_classid(self,class_id_list,min_classid=10,max_classid=30):
        """
        from tc class range to select unused class_id
        :param class_id_list: [10,20]
        :return: class_id ,eg 11
        """
        exist_qos_class_ids=class_id_list
        classids_range=range(min_classid,max_classid+1)
        for classid in classids_range:
            if classid not in exist_qos_class_ids:
                    return classid
    def _get_tc_file_path(self,router_id):
        return self.tc_file_root_path+"/"+router_id+"_qos_bind_class.json"

    def generate_file_from_json(self,cache_qos_binds,router_id):
        LOG.debug(_('generate_file_from_json in call,router_id %s'%(router_id)))
        qos_bind_class={}
        for key in cache_qos_binds:
            qos_bind_class.update({key:cache_qos_binds[key]["class_id"]})
        if len(qos_bind_class):
           json.dump(qos_bind_class,open(self._get_tc_file_path(router_id),'w'))
        else:
            self.delete_router_tc_json_files(router_id)

    def read_json_from_file(self,router_id):
        """

        :param router_id:
        :return: {"rule_id2": 11, "rule_id5": 10}
        """
        qos_bind_class={}
        path=self._get_tc_file_path(router_id)
        if os.path.exists(path):
            qos_bind_class=json.load(open(path,'r'))
        return qos_bind_class

    def delete_router_tc_json_files(self,router_id):
        LOG.debug(_('delete_router_tc_json_files in call,router_id %s'%(router_id)))
        tc_file_path=self._get_tc_file_path(router_id)
        if os.path.exists(tc_file_path):
            os.remove(tc_file_path)

    def init_router_qos_cache(self,router_id,nsname,devname,min_classid,max_classid,default_limit):
        """
        init router qos cache from tc and tc metadata,and add or update default limit
        :param cache_qos_binds: {}
        :param min_classi_d: 10
        :param max_class_id: 30
        :return:cache_qos_binds  {"rule_id3":{"max_rate":90,"class_id":10,"ip_srcs":["192.168.10.1","192.168.20.1"]}
        """
        LOG.debug(_('init_router_qos_cache in call,router_id %s'%(router_id)))
        #add  qdisc root and default_limit
        self.add_root_and_class(nsname,devname,default_limit)
        cache_qos_binds={}

        #{classid1:{"classid":classid1,"max_rate":1000,"src_ips":["ip_address1",""ip_address2]},}
        tc_qos_flows=self.get_class_and_flow(nsname,devname,min_classid,max_classid)

        binds_classids=self.read_json_from_file(router_id)#{"rule_id2": 11, "rule_id5": 10}
        #conducter cache_qos_binds
        if binds_classids:
            for key in binds_classids:
                class_id= binds_classids[key]
                if tc_qos_flows.get(class_id):
                    cache_qos_binds.update({key:tc_qos_flows[class_id]})
                    tc_qos_flows.pop(class_id)
        for class_id in tc_qos_flows:
            #delete flows
           self.del_flow_and_class(nsname,devname,classid="1:"+str(class_id))

        self.generate_file_from_json(cache_qos_binds,router_id)


        return cache_qos_binds



    def update_qos_binds(self,router_id,nsname,devname,new_qos_binds,cache_qos_binds,min_classid=10,max_classid=30):
        """
         update cache qos binds according to new qos binds
        :param nsname:
        :param devname:
        :param new_qos_binds: {"rule_id5":{"max_rate":100,"ip_srcs":["192.168.10.1","192.168.20.1"]},
        :param cache_qos_binds:{"rule_id3":{"max_rate":90,"class_id":10,"ip_srcs":["192.168.10.1","192.168.20.1"]}
        :return:
        """
        LOG.debug(_('update_qos_binds in call,router_id %s'%(router_id)))
        #record new  qos bind id
        new_keys = []
        #according new qos binds to get new keys and update rate and filters of  the same old key in cache qos binds
        for item in new_qos_binds:
            key = item
            old_value= cache_qos_binds.get(key)
            if old_value is None:
               new_keys.append(key)
               continue
            new_value = new_qos_binds[key]
            #compare old_value and new_value
            if not self.compare_qos_bind_rate(cache_qos_bind=old_value,new_qos_bind=new_value):
                class_id="1:"+str(old_value["class_id"])
                rate_str=str(new_value["max_rate"])+"Kbit"
                self.add_or_update_class(nsname,devname,parent_classid="1:",curent_classid=class_id,rate=rate_str,ceil=rate_str)
                old_value["max_rate"]=new_value["max_rate"]
            self.compare_and_udpate_qos_bind_src_ips(nsname,devname,cache_qos_bind=old_value,new_qos_bind=new_value)
        #for old cache_qos_binds
        #record exist class_id in cache qos binds
        class_id_list=[]
        #record remve qos rule_id id to remove_key_list
        remove_key_list=[]

        #compare cache qos binds  with  new qos binds to get record exist class_id and remove_key_list
        for item in cache_qos_binds:
            key = item
            new_value = new_qos_binds.get(key)
            if new_value is None:
               #print "remove tc class and filters\n"
               class_id_str="1:"+str(cache_qos_binds[key]["class_id"])
               self.del_flow_and_class(nsname,devname,class_id_str)
               remove_key_list.append(key)
               continue
            else:
                class_id_list.append(cache_qos_binds[key]["class_id"])
        #remove not exist in new qos binds from cache qos binds
        for key in remove_key_list:
            #print "remove "+key +" qos bind in cache bind qos\n"
            cache_qos_binds.pop(key)

        #according new  qos bind ids to add new qos binds to tc and cache qos
        for key in new_keys:
            qos_value=new_qos_binds[key]
            #get class_id
            class_id=self.get_qos_classid(class_id_list,min_classid,max_classid)
            class_id_str="1:"+str(class_id)
            #self.add_class_and_flow(nsname,devname,class_id=class_id_str,max_rate=str(qos_value["max_rate"])+"Kbit",src_ip=qos_value[])
            #add class  and filters
            rate_str=str(qos_value["max_rate"])+"Kbit"
            self.add_or_update_class(nsname,devname,"1:",class_id_str,rate=rate_str,ceil=rate_str)
            for src_ip in qos_value["src_ips"]:
                self.add_flow(nsname,devname,parentid="1:",src_ip=src_ip,classid=class_id_str)
            qos_value["class_id"]=class_id
            #append class_id to class_id_list
            class_id_list.append(class_id)
            cache_qos_binds.update({key:qos_value})

        #print "generate new json files "
        self.generate_file_from_json(cache_qos_binds=cache_qos_binds,router_id=router_id)
        #qos_bind_class_dict=self.read_json_from_file(router_id="router_id")

        #print "qos_bind_class_dict %r" %(qos_bind_class_dict)
        #print new_qos_binds
        #print cache_qos_binds


if __name__ == '__main__':
    #tc_operation=TC_Operation()
    nsname="qrouter-22304d8a-0ce4-4269-a391-3c28f1cae0a8"
    router_id="22304d8a-0ce4-4269-a391-3c28f1cae0a8"
    devname="qg-b45629e4-79"
    new_qos_binds = {}
    cache_qos_binds={}
    #{"rule_id3":{"max_rate":90,"class_id":10,"src_ips":["192.168.10.1","192.168.20.1"]},"rule_id2":{"max_rate":200,"class_id":11,"src_ips":["192.168.10.2","192.168.40.1"]}}
    tc_file_root_path="/var/lib/neutron/tc/"
    qos_limit= QosLimit()
    qos_limit.set_tc_file_root_path(tc_file_root_path)
    import pydevd
    pydevd.settrace('20.251.32.192', port=8888, stdoutToServer=True, stderrToServer=True)

    cache_qos_binds=qos_limit.init_router_qos_cache(router_id,nsname,devname,10,100,"1Kbit")
    qos_limit.update_qos_binds(router_id,nsname,devname,new_qos_binds,cache_qos_binds)

   # qos_limit.del_qdisc_root(nsname,devname)
    #qos_limit.delete_router_tc_json_files(router_id)

    #tc_operation.add_ingress_limit(nsname,devname,ingress_size="380000Kbit")
    #print tc_operation._get_ingress(nsname,devname)


   # tc_operation.add_class_and_flow(nsname,devname,"1:10","100mbit","10.0.0.1")
    #tc_operation.add_class_and_flow(nsname,devname,"1:10","100mbit","10.0.0.2")
    #tc_operation.del_flow(nsname,devname,"1:10","10.0.0.1")


    #tc_operation.del_flow_and_class(nsname,devname,'1:10')
    #tc_operation.add_or_update_class(nsname,devname,"1:1","1:11","20mbit","20mbit")
    #print tc_operation.get_class_and_flow(nsname,devname,10,100)

   # tc_operation.check_qdisc(nsname,devname,"htb 1:")
 #   tc_operation.del_qdisc_root(nsname,devname)
    #tc_operation.add_root_and_class(nsname,devname)
   #
   # tc_operation.add_flow(nsname,devname,"1:","20.251.36.102","1:10")
   # #print tc_operation.check_flow(nsname,devname,"1:10","20.251.36.102")
   ##def del_flow(self,nsname = None,devname=None, classid=None):
    #qoss=tc_operation.get_class_and_flow(nsname,devname,10,20)
    #for qos in qoss:
     #   print ("%r"%(qos))
    #tc_operation.del_flow_and_class(nsname,devname,"1:10")
    #tc_operation.add_class_and_flow(nsname,devname,"1:10","100mbit","20.251.36.104")
